from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any, AsyncGenerator

from fastapi.responses import StreamingResponse
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_config
from app.db.database import (
    assign_message_id_to_debug_events,
    create_message,
    get_conversation,
    list_messages_by_conversation,
    update_conversation_title,
)
from app.models import ChatRequest
from app.service.datasource import get_columns
from app.service.debug_bus import DebugEventBus, DebugEventMsg, _sse_event
from app.service.skills import skill_registry
from app.service.storage import read_file

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are DataAgent, an intelligent data exploration assistant. \
You help users understand and analyze data from object storage files and database tables. \
When the user provides context about files or tables, use that information to give informed answers. \
Be concise and helpful.

## Available Skills
You have access to specialized skills that provide step-by-step guidance for common tasks. \
When a skill matching the user's question is loaded (shown below in [Loaded Skill] context), \
follow its instruction as your primary workflow. Skills cover SQL querying, data exploration, \
and business ontology search. Use the standard problem breakdown protocol (Steps 0-7) \
only when no skill covers the user's question."""

CLASSIFY_PROMPT_SYSTEM = """You are a high-precision Data Query Intent Classifier. \
# Constraints \

- DO NOT EXPLAIN. \

- DO NOT THINK OUT LOUD. \

- OUTPUT ONLY ONE WORD: "yes" OR "no". \
"""

CLASSIFY_PROMPT = """
# Task \

Determine if a user message requires fetching or analyzing structured data from a database. \

# "yes" Criteria (Data-Related) \
1. Requests specific values, records, or "Reports" for specific entities (e.g., Material IDs, Batch Codes). \
2. Uses terms like: 追溯 (traceability), 统计 (statistics), 查询 (query), 报表 (report), 多少 (how many/much). \
3. Mentions specific identifiers (e.g., "物料123", "ID: 456"). \
4. Requires SQL, tables, or data visualization to answer. \

# "no" Criteria (General/Conversational) \
1. General knowledge (e.g., "什么是质量追溯?"). \
2. Greetings or casual chat. \
3. Requests for advice or general explanations. \

# Examples \
User: "查询去年的销售总额" -> yes \

User: "帮我解释下什么是SQL" -> no \

User: "物料203038884的质量追溯报告" -> yes \

User: "怎么联系物料部门？" -> no \

User Message: {user_input}"""


def _get_llm_client(config: Any) -> AsyncOpenAI:
    """Create an AsyncOpenAI client from config."""
    return AsyncOpenAI(base_url=config.llm.api_base, api_key=config.llm.api_key)


async def _classify_workflow_mode(
    message: str,
    config: Any,
    bus: DebugEventBus,
) -> str | None:
    """Use LLM to classify whether a message is data-related or common."""
    try:
        client = _get_llm_client(config)
        start_time = datetime.now(timezone.utc)
        response = await client.chat.completions.create(
            model=config.llm.model,
            messages=[{"role": "system", "content": CLASSIFY_PROMPT_SYSTEM},
                {"role": "user", "content": CLASSIFY_PROMPT.format(user_input=message)}],
            max_tokens=2048,
            temperature=0,
        )
        end_time = datetime.now(timezone.utc)
        answer = response.choices[0].message.content.strip().lower().rstrip(".") if response.choices else ""
        classification = "dynamic" if answer.startswith("yes") else None

        await bus.emit(DebugEventMsg(
            category="llm_call",
            data={
                "model": config.llm.model,
                "temperature": 0,
                "max_tokens": 2048,
                "system_prompt": CLASSIFY_PROMPT_SYSTEM,
                "user_prompt": CLASSIFY_PROMPT.format(user_input=message),
                "classification": classification,
                "raw_answer": answer,
                "finish_reason": response.choices[0].finish_reason if response.choices else None,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else None,
                    "completion_tokens": response.usage.completion_tokens if response.usage else None,
                    "total_tokens": response.usage.total_tokens if response.usage else None,
                },
                "duration_ms": int((end_time - start_time).total_seconds() * 1000),
            },
            timestamp=end_time,
        ))

        return classification
    except Exception as e:
        logger.warning(f"Workflow mode classification failed, defaulting to config: {e}")
        return None


async def _build_context_text(context: ChatRequest | None) -> str:
    """Build context string from selected files and tables."""
    if context is None or context.context is None:
        return ""

    parts: list[str] = []

    # File contents
    if context.context.selected_files:
        file_parts: list[str] = []
        for path in context.context.selected_files:
            try:
                content = read_file(path)
                file_parts.append(f"--- File: {path} ---\n{content}")
            except Exception as e:
                file_parts.append(f"--- File: {path} ---\n[Error reading file: {e}]")
        parts.append("### Selected Files\n" + "\n\n".join(file_parts))

    # Table schemas
    if context.context.selected_tables:
        table_parts: list[str] = []
        for table_ref in context.context.selected_tables:
            # Format: "datasource_name.table_name"
            if "." in table_ref:
                ds_name, tbl_name = table_ref.split(".", 1)
                try:
                    cols = await get_columns(ds_name, tbl_name)
                    col_lines = [f"  - {c.name} ({c.type})" + (f": {c.comment}" if c.comment else "") for c in cols]
                    table_parts.append(f"### Table: {table_ref}\nColumns:\n" + "\n".join(col_lines))
                except Exception as e:
                    table_parts.append(f"### Table: {table_ref}\n[Error reading schema: {e}]")
            else:
                table_parts.append(f"### Table: {table_ref}\n[Invalid format, expected datasource.table]")
        parts.append("### Selected Tables\n" + "\n\n".join(table_parts))

    return "\n\n".join(parts)


def _build_user_prompt(message: str, context_text: str) -> str:
    if context_text:
        return f"[Context]\n{context_text}\n\n[User Question]\n{message}"
    return message


MAX_TURNS = 10

# ── Skill matching ──────────────────────────────────────────

def _find_matching_skills(message: str, max_skills: int = 3) -> list[dict[str, Any]]:
    """Match user message against registered skills by keyword overlap.

    Returns up to `max_skills` best-matching skills sorted by match score,
    each containing the full skill data including instruction.
    """
    message_lower = message.lower()
    msg_words = set(re.findall(r'\w+', message_lower))
    if not msg_words:
        return []

    matched: list[dict[str, Any]] = []
    for skill in skill_registry.list_skills():
        search_text = f"{skill.name} {skill.display_name} {skill.description}".lower()
        skill_words = set(re.findall(r'\w+', search_text))
        overlap = msg_words & skill_words
        if len(overlap) >= 2:
            matched.append({
                "name": skill.name,
                "group": skill.group,
                "display_name": skill.display_name,
                "description": skill.description,
                "instruction": skill.instruction,
                "match_keywords": sorted(overlap),
                "score": len(overlap),
            })

    matched.sort(key=lambda x: x["score"], reverse=True)
    return matched[:max_skills]


def _build_skill_context(skills: list[dict[str, Any]]) -> str:
    """Format loaded skills into context text for injection."""
    if not skills:
        return ""
    parts: list[str] = ["## Loaded Skills"]
    for s in skills:
        parts.append(
            f"### Skill: {s['display_name']} ({s['name']})\n"
            f"**Group**: {s['group']}\n"
            f"**Description**: {s['description']}\n"
            f"**Instruction**: {s['instruction']}"
        )
    return "\n\n".join(parts)


MEMORY_SYSTEM_PROMPT = """You are a conversation memory summarizer. \
Given an earlier conversation fragment and the user's current question, \
create a concise memory that captures key context for continuing the conversation. \
Be factual and concise. Output only the memory text, no explanations."""

MEMORY_USER_PROMPT = """Summarize the following earlier conversation into a concise memory. \
Include key: entities mentioned (IDs, names), data tables referenced, SQL queries, \
numbers/statistics discussed, and important decisions or conclusions.

Earlier conversation:
{history}

Current user question: {question}

Memory (2-5 sentences max):"""


async def _generate_memory(
    older_messages: list[dict[str, Any]],
    current_question: str,
    config: Any,
    bus: DebugEventBus,
) -> str:
    """Generate a concise memory from older conversation messages via LLM."""
    t_start = datetime.now(timezone.utc)
    msg_count = len(older_messages)

    # Format history for the summarizer (truncate long messages)
    history_lines: list[str] = []
    for msg in older_messages:
        role_label = "user" if msg["role"] == "user" else "assistant"
        content = str(msg["content"])[:500] + ("..." if len(str(msg["content"])) > 500 else "")
        history_lines.append(f"[{role_label}]: {content}")

    history_text = "\n".join(history_lines)

    try:
        client = _get_llm_client(config)
        response = await client.chat.completions.create(
            model=config.llm.model,
            messages=[
                {"role": "system", "content": MEMORY_SYSTEM_PROMPT},
                {"role": "user", "content": MEMORY_USER_PROMPT.format(
                    history=history_text,
                    question=current_question,
                )},
            ],
            max_tokens=512,
            temperature=0.3,
        )
        memory = response.choices[0].message.content.strip() if response.choices else ""
        elapsed_ms = int((datetime.now(timezone.utc) - t_start).total_seconds() * 1000)

        # Emit llm_call debug event per Principle 1 (LLM input + output)
        await bus.emit(DebugEventMsg(
            category="llm_call",
            data={
                "purpose": "memory_generation",
                "model": config.llm.model,
                "temperature": 0.3,
                "max_tokens": 512,
                "system_prompt": MEMORY_SYSTEM_PROMPT,
                "user_prompt": MEMORY_USER_PROMPT.format(
                    history=history_text,
                    question=current_question,
                ),
                "output": memory,
                "output_length_chars": len(memory),
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else None,
                    "completion_tokens": response.usage.completion_tokens if response.usage else None,
                    "total_tokens": response.usage.total_tokens if response.usage else None,
                },
                "duration_ms": elapsed_ms,
            },
            timestamp=datetime.now(timezone.utc),
        ))

        return memory
    except Exception as e:
        elapsed_ms = int((datetime.now(timezone.utc) - t_start).total_seconds() * 1000)
        logger.warning(f"Memory generation failed: {e}")
        await bus.emit(DebugEventMsg(
            category="system",
            data={
                "action": "memory_generation_failed",
                "error": str(e),
                "elapsed_ms": elapsed_ms,
            },
            timestamp=datetime.now(timezone.utc),
        ))
        return ""


async def stream_chat(
    body: ChatRequest,
    current_user: dict,
    session: AsyncSession,
) -> StreamingResponse:
    t0 = datetime.now(timezone.utc)

    # Verify conversation ownership
    conv = await get_conversation(session, body.conversation_id)
    if conv is None:
        raise ValueError("Conversation not found")
    if conv.user_id != current_user["id"]:
        raise PermissionError("Forbidden")

    # Save user message
    await create_message(session, body.conversation_id, "user", body.message)
    await session.commit()

    # Auto-title on first message
    if conv.title is None:
        title = body.message[:50] + ("..." if len(body.message) > 50 else "")
        await update_conversation_title(session, body.conversation_id, title)
        await session.commit()

    # Build prompt with context
    context_text = await _build_context_text(body)
    user_prompt = _build_user_prompt(body.message, context_text)

    # Create the per-request debug bus
    bus = DebugEventBus(session, body.conversation_id)
    await bus.init_seq()

    # Get conversation history for multi-turn
    history = await list_messages_by_conversation(session, body.conversation_id)
    config = get_config()

    # --- Memory compaction: summarize older messages if history exceeds MAX_TURNS ---
    memory_text = ""
    if len(history) > MAX_TURNS * 2:
        keep_count = MAX_TURNS * 2
        older = history[:-keep_count]
        recent = history[-keep_count:]

        memory_text = await _generate_memory(
            older, body.message, config, bus,
        )

        await bus.emit(DebugEventMsg(
            category="system",
            data={
                "action": "history_compacted",
                "original_count": len(history),
                "summarized_count": len(older),
                "kept_count": len(recent),
                "has_memory": bool(memory_text),
                "memory_length_chars": len(memory_text),
            },
            timestamp=datetime.now(timezone.utc),
        ))

        history = recent

    # Build messages with memory-injected system prompt if available
    system_content = SYSTEM_PROMPT
    if memory_text:
        system_content += (
            f"\n\n[Memory from earlier conversation]\n"
            f"{memory_text}\n"
            f"--- End of memory ---"
        )

    # ── Skill matching and injection ──
    matched_skills = _find_matching_skills(body.message)
    skill_context = _build_skill_context(matched_skills) if matched_skills else ""
    if skill_context:
        # Inject into system prompt (used by "none" mode)
        system_content += f"\n\n{skill_context}"
        # Also inject into user prompt (used by "dynamic" mode — agent skips system messages)
        user_prompt = f"--- Loaded Skill Context ---\n{skill_context}\n--- End Skill Context ---\n\n{user_prompt}"
        logger.info(
            "[stream_chat] conv_id=%s matched_skills=%s",
            body.conversation_id, [s["name"] for s in matched_skills],
        )

    messages = [{"role": "system", "content": system_content}]
    for msg in history:
        messages.append({"role": msg.role, "content": msg.content})

    # Replace last user message with context-enhanced version
    if messages[-1]["role"] == "user":
        messages[-1]["content"] = user_prompt

    # Classify message as data-related or common via LLM
    t_classify = datetime.now(timezone.utc)
    if not body.workflow_mode:
        body.workflow_mode = await _classify_workflow_mode(body.message, config, bus)
    classify_ms = int((datetime.now(timezone.utc) - t_classify).total_seconds() * 1000)
    logger.info(
        "[stream_chat] conv_id=%s classification=%s classify_ms=%d",
        body.conversation_id, body.workflow_mode or "(none)", classify_ms,
    )

    # Determine effective workflow mode (request override > config)
    effective_mode = body.workflow_mode or config.workflow.mode

    async def sse_generator() -> AsyncGenerator[str, None]:
        t_sse_start = datetime.now(timezone.utc)
        logger.info(
            "[sse_generator] START conv_id=%s mode=%s",
            body.conversation_id, effective_mode,
        )
        # Emit classification debug event
        for s in await bus.emit_and_flush(DebugEventMsg(
            category="system",
            data={
                "action": "workflow_classification",
                "classified_mode": body.workflow_mode,
                "effective_mode": effective_mode,
                "config_mode": config.workflow.mode,
                "user_message_preview": body.message[:200],
            },
        )):
            yield s

        if body.context and (body.context.selected_files or body.context.selected_tables):
            for s in await bus.emit_and_flush(DebugEventMsg(
                category="context",
                data={
                    "selected_files": body.context.selected_files if body.context else [],
                    "selected_tables": body.context.selected_tables if body.context else [],
                    "context_length_chars": len(context_text),
                },
            )):
                yield s

        # Dispatch to mode-specific generator
        logger.info(
            "[sse_generator] DISPATCH conv_id=%s mode=%s",
            body.conversation_id, effective_mode,
        )
        if effective_mode == "dynamic":
            from app.service.agent import run_agent_loop
            generator = run_agent_loop(
                user_message=body.message,
                messages=messages,
                conversation_id=body.conversation_id,
                session=session,
                config=config,
                bus=bus,
                user_id=current_user["id"],
                tenant_id=current_user.get("tenant_id"),
            )
        elif effective_mode == "yaml":
            from app.service.engine import run_yaml_workflow
            generator = run_yaml_workflow(
                user_message=body.message,
                messages=messages,
                conversation_id=body.conversation_id,
                session=session,
                config=config,
                bus=bus,
                user_id=current_user["id"],
                tenant_id=current_user.get("tenant_id"),
            )
        else:
            generator = _generate(body, messages, config, session, bus)

        chunk_count = 0
        async for chunk in generator:
            chunk_count += 1
            for d in bus.drain():
                yield d
            yield chunk

        t_sse_end = datetime.now(timezone.utc)
        elapsed_ms = int((t_sse_end - t_sse_start).total_seconds() * 1000)
        logger.info(
            "[sse_generator] END conv_id=%s chunks=%d elapsed_ms=%d",
            body.conversation_id, chunk_count, elapsed_ms,
        )

    return StreamingResponse(
        sse_generator(),
        media_type="text/event-stream",
    )


async def _generate(
    body: ChatRequest,
    messages: list[dict[str, str]],
    config: Any,
    session: AsyncSession,
    bus: DebugEventBus,
) -> AsyncGenerator[str, None]:
    start_time = datetime.now(timezone.utc)
    client = _get_llm_client(config)

    try:
        stream = await client.chat.completions.create(
            model=config.llm.model,
            messages=messages,  # type: ignore[arg-type]
            max_tokens=config.llm.max_tokens,
            temperature=config.llm.temperature,
            stream=True,
        )

        full_content = ""
        finish_reason = None
        usage = None

        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                full_content += content
                yield _sse_event({"type": "chunk", "content": content})

            if chunk.choices and chunk.choices[0].finish_reason:
                finish_reason = chunk.choices[0].finish_reason

            if hasattr(chunk, "usage") and chunk.usage is not None:
                usage = chunk.usage

        end_time = datetime.now(timezone.utc)

        # Save assistant message
        assistant_msg_id = await create_message(session, body.conversation_id, "assistant", full_content)

        assigned = await assign_message_id_to_debug_events(
            session, body.conversation_id, assistant_msg_id
        )
        logger.info(
            "[_generate] conv_id=%s msg_id=%s tokens={prompt=%s completion=%s total=%s} "
            "answer_len=%d elapsed_ms=%d",
            body.conversation_id, assistant_msg_id,
            usage.prompt_tokens if usage else "?",
            usage.completion_tokens if usage else "?",
            usage.total_tokens if usage else "?",
            len(full_content),
            int((end_time - start_time).total_seconds() * 1000),
        )

        # Emit llm_call debug event via bus (Principle 1: input + output)
        answer_preview = full_content[:500] + ("..." if len(full_content) > 500 else "")
        await bus.emit(DebugEventMsg(
            category="llm_call",
            data={
                "purpose": "chat_response",
                "model": config.llm.model,
                "temperature": config.llm.temperature,
                "max_tokens": config.llm.max_tokens,
                "system_prompt": SYSTEM_PROMPT,
                "user_prompt": messages[-1]["content"] if messages else "",
                "finish_reason": finish_reason,
                "output_preview": answer_preview,
                "output_length_chars": len(full_content),
                "usage": {
                    "prompt_tokens": usage.prompt_tokens if usage else None,
                    "completion_tokens": usage.completion_tokens if usage else None,
                    "total_tokens": usage.total_tokens if usage else None,
                },
                "duration_ms": int((end_time - start_time).total_seconds() * 1000),
            },
            message_id=assistant_msg_id,
            timestamp=end_time,
        ))

        # Commit the writes made during streaming
        await session.commit()

        yield _sse_event({"type": "end", "message_id": assistant_msg_id})

    except Exception as e:
        logger.error(f"LLM streaming error: {e}")
        yield _sse_event({"type": "error", "error": str(e)})
