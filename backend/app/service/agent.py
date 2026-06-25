from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, AsyncGenerator
from pathlib import Path
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import AppConfig
from app.db.database import assign_message_id_to_debug_events, create_message
from app.db.workflow_db import (
    create_workflow_execution,
    create_workflow_step,
    update_workflow_execution_status,
    update_workflow_step,
)
from app.service.debug_bus import DebugEventBus, DebugEventMsg, _sse_event
from app.service.tools import execute_tool, get_tool_schemas
from app.service.datasource_resolver import set_current_tenant_id

logger = logging.getLogger(__name__)
script_dir = Path(__file__).parent
markdown_text = (script_dir / "ReAct_loop.md").read_text(encoding="utf-8")
# Enhanced System Prompt embedding the explicit Meta-Model and strict constraints
REACT_SYSTEM_PROMPT = markdown_text

# Build tool descriptions section once at module load
_tool_schemas = get_tool_schemas()
_tool_descriptions = "\n".join(
    f"- **`{t['function']['name']}`**: {t['function']['description']}"
    for t in _tool_schemas
)
TOOLS_PROMPT_SECTION = (
    "\n\n## Available Tools\n"
    "Use these tools to interact with the database and system:\n\n"
    f"{_tool_descriptions}\n"
)

def _parse_problem_breakdown(text: str) -> dict[str, Any] | None:
    """Extract the Problem Breakdown JSON from the LLM's step-0 response."""
    # Try ```json ... ``` code block first
    match = re.search(r"```json\s*([\s\S]*?)```", text)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass
    # Fallback: try to find a raw JSON object
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            return json.loads(match.group(0).strip())
        except json.JSONDecodeError:
            pass
    return None

def _now() -> datetime:
    return datetime.now(timezone.utc)

def _extract_balanced_json(text: str, start: int) -> tuple[str, int] | None:
    """Extract a balanced JSON object/array starting at position `start`.

    Handles both objects {...} and arrays [...]. Skips optional
    leading/trailing backticks that may wrap the JSON.
    """
    if start >= len(text):
        return None
    # Skip optional opening backtick
    if text[start] == "`":
        start += 1
        if start >= len(text):
            return None
    ch = text[start]
    if ch not in ("{", "["):
        return None
    opening = ch
    closing = "}" if opening == "{" else "]"
    depth = 0
    in_string = False
    escape = False
    end = start
    for i in range(start, len(text)):
        ch = text[i]
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == opening:
            depth += 1
        elif ch == closing:
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if depth != 0:
        return None
    return text[start:end], end


def parse_react_actions(text: str) -> tuple[list[tuple[str, dict[str, Any]]], str | None]:
    """Parse one or more Tool Name / Tool Input pairs and optional Final Answer.

    Supports both plain and backtick-wrapped formats:
      Tool Name: `ontology_query_tool` Tool Input:`{"keyword": ["物料"]}`
      Tool Name: sql_executor Tool Input: {"sql": "SELECT 1"}

    Returns (list of (tool_name, args), final_answer_or_None).
    """
    logger.debug("parse_react_actions raw text (%d chars): %s", len(text), text[:500])

    # Attempt to locate final answer first
    final_answer = None
    if "Final Answer:" in text:
        parts = text.split("Final Answer:", 1)
        final_answer = parts[1].strip()

    actions: list[tuple[str, dict[str, Any]]] = []

    # Pattern: Tool Name: [backtick]name[backtick] ... Tool Input: [backtick]JSON[backtick]
    # The space between Tool Name and Tool Input is optional (could be newline or space)
    action_pattern = re.compile(
        r"Tool Name:\s*(?:`([^`]+)`|(\w+))\s+Tool Input:\s*",
        re.MULTILINE,
    )

    _INVALID_TOOL_NAMES = frozenset({"none", "null", "undefined", "nan", ""})

    for match in action_pattern.finditer(text):
        tool_name = match.group(1) or match.group(2)
        tool_name = tool_name.strip()
        logger.debug("Found Tool Name: %s at pos %d", tool_name, match.start())

        # Filter out obviously invalid tool names
        if not tool_name or tool_name.lower() in _INVALID_TOOL_NAMES:
            logger.debug("Skipping invalid tool name: %s", tool_name)
            continue

        json_start = match.end()
        # Skip whitespace (including optional backtick before JSON)
        while json_start < len(text) and text[json_start] in " \t\n\r`":
            json_start += 1

        if json_start >= len(text):
            logger.debug("No content after Tool Input: for tool %s", tool_name)
            continue
        if text[json_start] not in ("{", "["):
            logger.debug("Tool Input does not start with { or [ for tool %s, found: %s",
                         tool_name, repr(text[json_start:json_start + 50]))
            continue

        result = _extract_balanced_json(text, json_start)
        if result is None:
            logger.debug("Failed to extract balanced JSON for tool %s at pos %d", tool_name, json_start)
            continue
        json_str, end_pos = result
        logger.debug("Extracted JSON (%d chars) for tool %s: %s", len(json_str), tool_name, json_str[:200])

        try:
            args = json.loads(json_str.strip())
            actions.append((tool_name.strip(), args))
            logger.debug("Parsed action: %s -> %s", tool_name, {k: str(v)[:50] for k, v in args.items()})
        except json.JSONDecodeError as e:
            logger.warning("Failed to parse tool input JSON: %s — raw: %s", e, json_str[:200])
            actions.append((tool_name.strip(), {}))

    logger.debug("parse_react_actions result: %d actions, final_answer=%s", len(actions), "yes" if final_answer else "no")
    return actions, final_answer


def parse_react_action(text: str) -> tuple[str | None, dict[str, Any] | None, str | None]:
    """Convenience wrapper: return the first action or final answer."""
    actions, final_answer = parse_react_actions(text)
    if final_answer is not None:
        return None, None, final_answer
    if actions:
        return actions[0][0], actions[0][1], None
    return None, None, None

def update_meta_model_state(current_state: dict[str, Any], text: str) -> dict[str, Any]:
    """Parses the LLM's delta updates block and merges it into our state tracking object."""
    updates_match = re.search(r"-\s*\*\*Meta-Model Updates\*\*:\s*(.+)", text, re.DOTALL)
    if updates_match:
        # Stop at next section header or end
        update_text = updates_match.group(1).strip()
        next_header = re.search(r"\n-\s+\*\*|\n(?:Thought|Action|Final Answer):", update_text)
        if next_header:
            update_text = update_text[:next_header.start()].strip()

        if not update_text:
            return current_state

        # Track with deduplication and size limits
        max_entries = 20
        text_lower = update_text.lower()
        if "schema" in text_lower and update_text not in current_state["schema"]:
            current_state["schema"].append(update_text)
            if len(current_state["schema"]) > max_entries:
                current_state["schema"] = current_state["schema"][-max_entries:]
        if ("glossary" in text_lower or "term" in text_lower) and update_text not in current_state["domain_glossary"]:
            current_state["domain_glossary"].append(update_text)
            if len(current_state["domain_glossary"]) > max_entries:
                current_state["domain_glossary"] = current_state["domain_glossary"][-max_entries:]
        if update_text not in current_state["deltas_history"]:
            current_state["deltas_history"].append(update_text)
            if len(current_state["deltas_history"]) > max_entries:
                current_state["deltas_history"] = current_state["deltas_history"][-max_entries:]
    return current_state


async def _call_llm_with_retry(client: AsyncOpenAI, model: str, messages: list, max_tokens: int, temperature: float, max_retries: int = 3) -> Any:
    """Call the LLM with exponential backoff retry on transient failures."""
    last_error = None
    for attempt in range(max_retries):
        try:
            return await client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                wait = 2 ** attempt
                logger.warning("LLM call failed (attempt %d/%d), retrying in %ds: %s", attempt + 1, max_retries, wait, e)
                await asyncio.sleep(wait)
            else:
                logger.error("LLM call failed after %d attempts: %s", max_retries, e)
    raise last_error  # type: ignore[misc]


_TRUNCATION_NOTE = "\n[Note: output truncated to 8000 chars for efficiency]"

# (Keep other TRUNCATION references updated too)
_OBS_TRUNCATION_NOTE = "\n\n[Note: observations truncated to 8000 chars]"

async def run_agent_loop(
    user_message: str,
    messages: list[dict[str, str]],
    conversation_id: int,
    session: AsyncSession,
    config: AppConfig,
    bus: DebugEventBus,
    user_id: int | None = None,
    tenant_id: int | None = None,
) -> AsyncGenerator[str, None]:
    """Dynamic ReAct agent loop: LLM reads state meta-model, outputs changes and actions.

    Yields SSE events: step_start, step_end, step_error, chunk, end, error.
    """
    if tenant_id is not None:
        set_current_tenant_id(tenant_id)

    start_time = datetime.now(timezone.utc)
    # Enforce highly deterministic execution behavior to mitigate hallucination risks
    client = AsyncOpenAI(base_url=config.llm.api_base, api_key=config.llm.api_key)

    # Create workflow execution record
    execution_id = await create_workflow_execution(
        session, conversation_id, mode="dynamic"
    )

    # Initialize externalized dictionary tracking meta-model states securely
    meta_model_state: dict[str, Any] = {
        "original_question": user_message,
        "structured_question": {},
        "domain_glossary": [],
        "schema": [],
        "business_process": "[Pending Gather]",
        "metrics_logic": "[Pending Gather]",
        "output_style": "[Pending Analysis]",
        "deltas_history": [],
    }

    # Initialize underlying execution window base array
    agent_messages: list[dict[str, Any]] = []
    for msg in messages:
        if msg["role"] == "system":
            continue
        agent_messages.append({"role": msg["role"], "content": msg["content"]})

    max_iterations = config.workflow.max_iterations
    consecutive_parse_failures = 0

    # Token accumulation counters
    accumulated_prompt_tokens = 0
    accumulated_completion_tokens = 0
    accumulated_total_tokens = 0

    for iteration in range(max_iterations):
        iter_start = datetime.now(timezone.utc)
        logger.debug(
            "[agent_loop] iter=%d/%d conv_id=%s",
            iteration, max_iterations, conversation_id,
        )
        # ── Step 0: Problem Breakdown ──
        if iteration == 0:
            contextual_system_prompt = (
                f"{REACT_SYSTEM_PROMPT}{TOOLS_PROMPT_SECTION}\n\n"
                f"=== INITIALIZATION PHASE ===\n"
                f"You are in initialization. Complete Step 0 (Problem Breakdown) ONLY.\n"
                f"Do NOT call tools and do NOT produce a Final Answer yet.\n"
                f"Original Question: {user_message}\n"
                f"==========================================="
            )
            current_round_messages = [{"role": "system", "content": contextual_system_prompt}] + agent_messages
        else:
            # Dynamically inject persistent state context into dynamic tracking header
            structured_json = json.dumps(meta_model_state['structured_question'], ensure_ascii=False)
            contextual_system_prompt = (
                f"{REACT_SYSTEM_PROMPT}{TOOLS_PROMPT_SECTION}\n\n"
                f"=== CURRENT PERSISTENT META-MODEL STATE ===\n"
                f"1. [Original Question]: {meta_model_state['original_question']}\n"
                f"   [Structured Question]: {structured_json}\n"
                f"2. [Domain Term Glossary]: {meta_model_state['domain_glossary']}\n"
                f"3. [Static Data Structure / Schema]: {meta_model_state['schema']}\n"
                f"4. [Related Business Process]: {meta_model_state['business_process']}\n"
                f"5. [Core Metrics & Computing Logic]: {meta_model_state['metrics_logic']}\n"
                f"6. [Report Format / Output Style]: {meta_model_state['output_style']}\n"
                f"7. [Join Paths]: [Pending Discovery]\n"
                f"8. [Query Results / Dataset]: [Pending]\n"
                f"==========================================="
            )
            current_round_messages = [{"role": "system", "content": contextual_system_prompt}] + agent_messages

        llm_call_start = datetime.now(timezone.utc)
        try:
            response = await _call_llm_with_retry(
                client,
                config.llm.model,
                current_round_messages,  # type: ignore[arg-type]
                config.llm.max_tokens,
                0.1,
            )
        except Exception as e:
            logger.error(f"Agent LLM error at ReAct iteration {iteration}: {e}")
            yield _sse_event({"type": "error", "error": str(e)})
            await update_workflow_execution_status(
                session, execution_id, "failed", finished_at=_now()
            )
            await session.commit()
            return

        choice = response.choices[0]
        llm_text = choice.message.content or ""
        llm_call_duration = int((datetime.now(timezone.utc) - llm_call_start).total_seconds() * 1000)
        usage = response.usage

        # Accumulate tokens across all iterations
        if usage:
            accumulated_prompt_tokens += usage.prompt_tokens or 0
            accumulated_completion_tokens += usage.completion_tokens or 0
            accumulated_total_tokens += usage.total_tokens or 0

        # Record LLM response for every thinking step iteration
        await bus.emit(DebugEventMsg(
            category="llm_call",
            data={
                "mode": "agent_thinking",
                "iteration": iteration,
                "model": config.llm.model,
                "temperature": 0.1,
                "max_tokens": config.llm.max_tokens,
                "llm_text_truncated": llm_text[:500] + "..." if len(llm_text) > 500 else llm_text,
                "finish_reason": choice.finish_reason,
                "usage": {
                    "prompt_tokens": usage.prompt_tokens if usage else None,
                    "completion_tokens": usage.completion_tokens if usage else None,
                    "total_tokens": usage.total_tokens if usage else None,
                },
                "accumulated_usage": {
                    "prompt_tokens": accumulated_prompt_tokens,
                    "completion_tokens": accumulated_completion_tokens,
                    "total_tokens": accumulated_total_tokens,
                },
                "duration_ms": llm_call_duration,
            },
            timestamp=_now(),
        ))

        # ── Step 0: Problem Breakdown handling ──
        if iteration == 0:
            agent_messages.append({"role": "assistant", "content": llm_text})
            breakdown = _parse_problem_breakdown(llm_text)
            if breakdown:
                meta_model_state["structured_question"] = breakdown
                # Extract output format / report style hints into meta model
                if breakdown.get("output_format"):
                    meta_model_state["output_style"] = breakdown["output_format"]
                    if breakdown.get("report_style"):
                        meta_model_state["output_style"] += f": {breakdown['report_style']}"

                await bus.emit(DebugEventMsg(
                    category="system",
                    data={
                        "mode": "dynamic_react",
                        "iteration": 0,
                        "step": "problem_breakdown",
                        "message": "Step 0 completed: problem decomposed into structured JSON",
                        "structured_question": breakdown,
                    },
                ))
                # Provide the structured question as context for the next iteration
                agent_messages.append({
                    "role": "user",
                    "content": (
                        f"Step 0 complete. Use this Problem Breakdown to guide tool calls:\n"
                        f"```json\n{json.dumps(breakdown, ensure_ascii=False, indent=2)}\n```\n\n"
                        f"Now proceed with Step 1: query ontology for each entity/query_subject, "
                        f"then follow Steps 2-7 in the protocol."
                    ),
                })
                await session.commit()
                iter_ms = int((datetime.now(timezone.utc) - iter_start).total_seconds() * 1000)
                logger.debug(
                    "[agent_loop] iter=%d step0-breakdown conv_id=%s iter_ms=%d",
                    iteration, conversation_id, iter_ms,
                )
                continue
            else:
                # Fallback: if JSON parsing fails, still proceed but warn
                logger.warning("Step 0 Problem Breakdown JSON not found in LLM response, proceeding with raw text")
                agent_messages.append({
                    "role": "user",
                    "content": (
                        f"Your last response did not contain a valid Problem Breakdown JSON. "
                        f"Please re-read the Step 0 protocol and output a JSON. "
                        f"Otherwise, proceed with heuristic analysis based on the user's question."
                    ),
                })
                await session.commit()
                continue

        # Append raw trace message to memory array (iterations 1+)
        agent_messages.append({"role": "assistant", "content": llm_text})
        
        # 1. Update the local tracking dictionary using the Delta logic
        meta_model_state = update_meta_model_state(meta_model_state, llm_text)
        
        # 2. Extract all actions and optional Final Answer
        tool_actions, final_answer = parse_react_actions(llm_text)

        # Record parse result for debugging
        await bus.emit(DebugEventMsg(
            category="system",
            data={
                "mode": "dynamic_react",
                "iteration": iteration,
                "step": "parse_result",
                "tool_actions_found": len(tool_actions),
                "tool_names": [name for name, _ in tool_actions],
                "has_final_answer": final_answer is not None,
            },
        ))

        # ── Final Answer branch (priority over tool actions) ──
        if final_answer:
            yield _sse_event({"type": "chunk", "content": final_answer})

            assistant_msg_id = await create_message(
                session, conversation_id, "assistant", final_answer
            )

            assigned = await assign_message_id_to_debug_events(
                session, conversation_id, assistant_msg_id
            )
            logger.debug(
                "[agent_loop] assigned message_id=%s to %s debug events conv_id=%s",
                assistant_msg_id, assigned, conversation_id,
            )

            await update_workflow_execution_status(
                session, execution_id, "completed",
                finished_at=_now(),
                final_answer=final_answer,
            )
            await session.commit()

            yield _sse_event({"type": "end", "message_id": assistant_msg_id})
            iter_ms = int((datetime.now(timezone.utc) - iter_start).total_seconds() * 1000)
            total_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
            logger.info(
                "[agent_loop] FINAL_ANSWER conv_id=%s iter=%d iter_ms=%d total_ms=%d "
                "tokens_accum={prompt=%d completion=%d total=%d} answer_len=%d",
                conversation_id, iteration, iter_ms, total_ms,
                accumulated_prompt_tokens, accumulated_completion_tokens,
                accumulated_total_tokens, len(final_answer),
            )
            return

        # ── Multi-tool execution branch ──
        elif tool_actions:
            consecutive_parse_failures = 0
            observations: list[str] = []

            for idx, (tool_name, tool_args) in enumerate(tool_actions):
                step_id = await create_workflow_step(
                    session,
                    execution_id,
                    step_index=iteration,
                    step_type="tool_call",
                    step_name=tool_name,
                    input=json.dumps(tool_args, ensure_ascii=False),
                )

                yield _sse_event({
                    "type": "step_start",
                    "step_id": step_id,
                    "step_name": tool_name,
                    "step_type": "tool_call",
                })

                tool_start = datetime.now(timezone.utc)
                result = await execute_tool(tool_name, tool_args)
                tool_duration = int((datetime.now(timezone.utc) - tool_start).total_seconds() * 1000)

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
                    observations.append(f"Observation {idx + 1} ({tool_name}):\nError: {result['error']}. Shift strategies if needed.")
                else:
                    output_str = json.dumps(result, ensure_ascii=False)
                    if len(output_str) > 8000:
                        logger.debug(
                            "[agent_loop] tool output truncated for %s: %d -> 8000 chars",
                            tool_name, len(result) if isinstance(result, dict) else len(output_str),
                        )
                        output_str = output_str[:8000] + _TRUNCATION_NOTE
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
                    observations.append(f"Observation {idx + 1} ({tool_name}):\n{output_str}")

                await bus.emit(DebugEventMsg(
                    category="tool_call",
                    data={
                        "tool_name": tool_name,
                        "arguments": tool_args,
                        "result": result if "error" not in result else None,
                        "error": result.get("error"),
                        "duration_ms": tool_duration,
                        "batch_index": idx,
                        "iteration": iteration,
                    },
                    step_id=step_id,
                ))

            # Feed all observations back in a single user message
            combined_observation = "Observation:\n" + "\n\n---\n\n".join(observations)
            if len(combined_observation) > 8000:
                logger.debug(
                    "[agent_loop] combined observation truncated: %d -> 8000 chars conv_id=%s",
                    len(combined_observation), conversation_id,
                )
                combined_observation = combined_observation[:8000] + _OBS_TRUNCATION_NOTE
            agent_messages.append({
                "role": "user",
                "content": combined_observation
            })
            await session.commit()
            iter_ms = int((datetime.now(timezone.utc) - iter_start).total_seconds() * 1000)
            logger.debug(
                "[agent_loop] iter=%d done conv_id=%s tools=%d iter_ms=%d",
                iteration, conversation_id, len(tool_actions), iter_ms,
            )

        else:
            consecutive_parse_failures += 1
            logger.warning(f"ReAct pattern structural parse anomaly at iteration {iteration} (consecutive: {consecutive_parse_failures})")
            if consecutive_parse_failures >= 3:
                yield _sse_event({
                    "type": "error",
                    "error": "Agent failed to produce valid output format after 3 consecutive attempts",
                })
                await update_workflow_execution_status(
                    session, execution_id, "failed", finished_at=_now()
                )
                await session.commit()
                return
            # Safe recovery mechanism: append instruction asking to form valid execution blocks
            agent_messages.append({
                "role": "user", 
                "content": "System Rule Check: Your last response did not output a valid 'Action:' block or a final 'Final Answer:'. Resolve your step immediately using the required structural formatting rules."
            })

    # Catch iteration exhaustion
    yield _sse_event({
        "type": "error",
        "error": "Agent reached maximum iterations without producing a final answer",
    })
    await update_workflow_execution_status(
        session, execution_id, "failed", finished_at=_now()
    )
    await session.commit()