from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncGenerator

import yaml
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import AppConfig
from app.db.database import create_message
from app.db.workflow_db import (
    create_workflow_execution,
    create_workflow_step,
    update_workflow_execution_status,
    update_workflow_step,
)
from app.service.debug_bus import DebugEventBus, DebugEventMsg, _sse_event
from app.service.tools import execute_tool
from app.service.datasource_resolver import set_current_tenant_id

logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _load_workflows(yaml_dir: str) -> list[dict]:
    """Load all YAML workflow definitions from a directory."""
    workflows: list[dict] = []
    dir_path = Path(yaml_dir)
    if not dir_path.exists():
        logger.warning(f"Workflow YAML directory not found: {yaml_dir}")
        return workflows

    for yaml_file in sorted(dir_path.glob("*.yaml")):
        try:
            with open(yaml_file, "r", encoding="utf-8") as f:
                wf = yaml.safe_load(f)
                if wf:
                    wf["_file"] = str(yaml_file)
                    workflows.append(wf)
        except Exception as e:
            logger.error(f"Failed to load workflow {yaml_file}: {e}")

    return workflows


def _match_workflow(user_message: str, workflows: list[dict]) -> dict | None:
    """Match a user message to a workflow based on trigger_keywords.

    Returns the first matching workflow, or None.
    """
    message_lower = user_message.lower()
    for wf in workflows:
        keywords = wf.get("trigger_keywords", [])
        for kw in keywords:
            if kw.lower() in message_lower:
                return wf
    return None


def _resolve_template(template: str, context: dict) -> str:
    """Resolve {{ ... }} placeholders in a template string.

    Context contains:
      - context: user's chat context (selected_files, selected_tables)
      - user_message: the user's message
      - steps: dict of step_name -> step_output dict (accumulated during execution)
    """

    def _replace(match: re.Match) -> str:
        expr = match.group(1).strip()
        try:
            # Evaluate the expression against the context
            value = eval(expr, {"__builtins__": {}}, context)
            if isinstance(value, (dict, list)):
                return json.dumps(value, ensure_ascii=False)
            return str(value)
        except Exception as e:
            logger.warning(f"Template resolution failed for '{{{{{expr}}}}}': {e}")
            return f"{{{{{expr}}}}}"

    return re.sub(r"\{\{(.+?)\}\}", _replace, template)


async def _execute_llm_step(
    step: dict,
    context: dict,
    client: AsyncOpenAI,
    config: AppConfig,
) -> str:
    """Execute an LLM call step. Returns the LLM response text."""
    system = _resolve_template(step.get("system", ""), context)
    prompt = _resolve_template(step.get("prompt", ""), context)

    messages = [{"role": "system", "content": system}]
    if prompt:
        messages.append({"role": "user", "content": prompt})

    try:
        response = await client.chat.completions.create(
            model=config.llm.model,
            messages=messages,  # type: ignore[arg-type]
            max_tokens=config.llm.max_tokens,
            temperature=config.llm.temperature,
        )
        return response.choices[0].message.content or ""
    except Exception as e:
        raise RuntimeError(f"LLM call failed: {e}")


async def _execute_tool_step(
    step: dict,
    context: dict,
) -> dict[str, Any]:
    """Execute a tool_call step. Returns the tool result dict."""
    tool_name = _resolve_template(step.get("tool", ""), context)
    params_raw = step.get("params", {})
    params: dict[str, Any] = {}
    for k, v in params_raw.items():
        params[k] = _resolve_template(str(v), context)

    return await execute_tool(tool_name, params)


async def run_yaml_workflow(
    user_message: str,
    messages: list[dict[str, str]],
    conversation_id: int,
    session: AsyncSession,
    config: AppConfig,
    bus: DebugEventBus,
    user_id: int | None = None,
    tenant_id: int | None = None,
) -> AsyncGenerator[str, None]:
    """Run a predefined YAML workflow.

    Loads workflows from yaml_dir, matches user_message against trigger_keywords,
    executes steps in order, and yields SSE events.
    Debug events are emitted via the bus and interleaved by the SSE consumer.
    """
    if tenant_id is not None:
        set_current_tenant_id(tenant_id)

    start_time = datetime.now(timezone.utc)

    workflows = _load_workflows(config.workflow.yaml_dir)
    if not workflows:
        yield _sse_event({"type": "error", "error": "No workflow definitions found"})
        return

    matched = _match_workflow(user_message, workflows)
    if matched is None:
        yield _sse_event({"type": "error", "error": "No workflow matched your question"})
        return

    workflow_name = matched.get("name", matched.get("_file", "unknown"))
    steps = matched.get("steps", [])

    # Build template context
    context: dict[str, Any] = {
        "user_message": user_message,
        "context": {
            "selected_files": [],
            "selected_tables": [],
        },
        "steps": {},
    }

    # Create workflow execution
    execution_id = await create_workflow_execution(
        session, conversation_id,
        mode="yaml",
        workflow_name=workflow_name,
    )

    client = AsyncOpenAI(base_url=config.llm.api_base, api_key=config.llm.api_key)

    for idx, step_def in enumerate(steps):
        step_type = step_def.get("type", "tool_call")
        step_name = step_def.get("name", f"step_{idx}")

        # Create step record
        step_id = await create_workflow_step(
            session, execution_id, idx,
            step_type=step_type,
            step_name=step_name,
            input=json.dumps(step_def, ensure_ascii=False),
        )

        yield _sse_event({
            "type": "step_start",
            "step_id": step_id,
            "step_name": step_name,
            "step_type": step_type,
        })

        try:
            if step_type == "tool_call":
                step_start_time = datetime.now(timezone.utc)
                result = await _execute_tool_step(step_def, context)
                step_end_time = datetime.now(timezone.utc)
                if "error" in result:
                    await update_workflow_step(
                        session, step_id, "failed",
                        error=result["error"],
                        finished_at=_now(),
                    )
                    yield _sse_event({
                        "type": "step_error",
                        "step_id": step_id,
                        "error": result["error"],
                    })
                    # Emit tool_call debug event via bus
                    await bus.emit(DebugEventMsg(
                        category="tool_call",
                        data={
                            "tool_name": step_def.get("tool", ""),
                            "arguments": step_def.get("params", {}),
                            "error": result["error"],
                            "duration_ms": int((step_end_time - step_start_time).total_seconds() * 1000),
                        },
                        step_id=step_id,
                    ))
                    # Continue to next steps even if one fails
                    context["steps"][step_name] = {"error": result["error"]}
                else:
                    output_str = json.dumps(result, ensure_ascii=False)
                    await update_workflow_step(
                        session, step_id, "completed",
                        output=output_str,
                        finished_at=_now(),
                    )
                    yield _sse_event({
                        "type": "step_end",
                        "step_id": step_id,
                        "output": output_str,
                    })
                    # Emit tool_call debug event via bus
                    await bus.emit(DebugEventMsg(
                        category="tool_call",
                        data={
                            "tool_name": step_def.get("tool", ""),
                            "arguments": step_def.get("params", {}),
                            "result": result,
                            "duration_ms": int((step_end_time - step_start_time).total_seconds() * 1000),
                        },
                        step_id=step_id,
                    ))
                    context["steps"][step_name] = result

            elif step_type == "llm_call":
                step_start_time = datetime.now(timezone.utc)
                llm_result = await _execute_llm_step(step_def, context, client, config)
                step_end_time = datetime.now(timezone.utc)
                await update_workflow_step(
                    session, step_id, "completed",
                    output=llm_result,
                    finished_at=_now(),
                )
                yield _sse_event({
                    "type": "step_end",
                    "step_id": step_id,
                    "output": llm_result,
                })
                # Emit llm_call debug event via bus (Principle 1: input + output)
                system_prompt = _resolve_template(step_def.get("system", ""), context)
                user_prompt = _resolve_template(step_def.get("prompt", ""), context)
                await bus.emit(DebugEventMsg(
                    category="llm_call",
                    data={
                        "purpose": "workflow_step",
                        "model": config.llm.model,
                        "temperature": config.llm.temperature,
                        "max_tokens": config.llm.max_tokens,
                        "workflow_name": workflow_name,
                        "step_name": step_name,
                        "system_prompt": system_prompt,
                        "user_prompt": user_prompt,
                        "output": llm_result,
                        "output_length_chars": len(llm_result),
                        "duration_ms": int((step_end_time - step_start_time).total_seconds() * 1000),
                    },
                    step_id=step_id,
                ))
                context["steps"][step_name] = {"content": llm_result}

            else:
                await update_workflow_step(
                    session, step_id, "failed",
                    error=f"Unknown step type: {step_type}",
                    finished_at=_now(),
                )
                yield _sse_event({
                    "type": "step_error",
                    "step_id": step_id,
                    "error": f"Unknown step type: {step_type}",
                })

        except Exception as e:
            logger.error(f"Workflow step '{step_name}' failed: {e}")
            await update_workflow_step(
                session, step_id, "failed",
                error=str(e),
                finished_at=_now(),
            )
            yield _sse_event({
                "type": "step_error",
                "step_id": step_id,
                "error": str(e),
            })
            context["steps"][step_name] = {"error": str(e)}

        await session.commit()

    # Build final answer from workflow results
    final_template = matched.get("final_answer", "")
    if final_template:
        final_content = _resolve_template(final_template, context)
    else:
        # Default: describe what happened
        completed = sum(1 for s in context.get("steps", {}).values() if "error" not in s)
        total = len(steps)
        final_content = f"Workflow '{workflow_name}' completed: {completed}/{total} steps succeeded."

    # Stream final content
    yield _sse_event({"type": "chunk", "content": final_content})

    # Save assistant message
    assistant_msg_id = await create_message(
        session, conversation_id, "assistant", final_content
    )

    end_time = datetime.now(timezone.utc)

    # Emit system debug event for workflow completion via bus
    completed = sum(1 for s in context.get("steps", {}).values() if "error" not in s)
    total = len(steps)
    await bus.emit(DebugEventMsg(
        category="system",
        data={
            "mode": "yaml",
            "workflow_name": workflow_name,
            "steps_completed": completed,
            "steps_total": total,
            "duration_ms": int((end_time - start_time).total_seconds() * 1000),
        },
        message_id=assistant_msg_id,
        timestamp=end_time,
    ))

    await update_workflow_execution_status(
        session, execution_id, "completed",
        finished_at=_now(),
        final_answer=final_content,
    )
    await session.commit()

    yield _sse_event({"type": "end", "message_id": assistant_msg_id})
