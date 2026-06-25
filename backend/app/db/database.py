from __future__ import annotations

from pathlib import Path
from typing import Any

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base
from app.db.models import Conversation, DebugEvent, Message, User
from app.db.session import engine


# ── Table Initialization ───────────────────────────────


async def init_tables() -> None:
    """Initialize database: create all tables via ORM, then seed default data from init.sql.

    Table creation uses SQLAlchemy's metadata which handles FK ordering correctly.
    Only INSERT data is in init.sql (read safely as individual statements).
    """
    # 1. Create all tables (SQLAlchemy handles FK constraints correctly)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 2. Seed default data from init.sql (INSERT statements only)
    sql_path = Path(__file__).resolve().parent.parent.parent / "data" / "init.sql"
    if not sql_path.exists():
        raise FileNotFoundError(f"init.sql not found at {sql_path}")

    raw_sql = sql_path.read_text(encoding="utf-8")

    async with engine.connect() as conn:
        autoconn = await conn.execution_options(isolation_level="AUTOCOMMIT")
        await autoconn.run_sync(_run_seed_sql, raw_sql)


def _run_seed_sql(conn, raw_sql: str) -> None:
    """Execute seed SQL statements (INSERT only) in autocommit mode."""
    import re
    statements = re.split(r';\s*\n', raw_sql)
    for stmt in statements:
        stmt = stmt.strip()
        if not stmt or stmt.upper() in ("BEGIN", "COMMIT", "CREATE", "ALTER", "DROP"):
            continue
        if any(stmt.upper().startswith(kw) for kw in ("CREATE", "ALTER", "DROP")):
            continue
        if stmt.startswith("--"):
            continue
        try:
            conn.execute(text(stmt))
        except Exception as e:
            err = str(e)
            if any(kw in err for kw in ("already exists", "duplicate key", "conflict")):
                continue
            raise


async def close_db() -> None:
    """Dispose of the engine connection pool."""
    await engine.dispose()


# ── Users ──────────────────────────────────────────────


async def get_user_by_username(
    session: AsyncSession, username: str
) -> User | None:
    stmt = select(User).where(User.username == username)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_user_by_id(
    session: AsyncSession, user_id: int
) -> User | None:
    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def create_user(
    session: AsyncSession, username: str, password_hash: str, role: str = "user",
) -> int:
    user = User(username=username, password_hash=password_hash, role=role)
    session.add(user)
    await session.flush()
    return user.id


async def update_user_password(
    session: AsyncSession, user_id: int, password_hash: str,
) -> bool:
    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        return False
    user.password_hash = password_hash
    await session.flush()
    return True


# ── Conversations ──────────────────────────────────────


async def list_conversations(
    session: AsyncSession, user_id: int
) -> list[Conversation]:
    stmt = (
        select(Conversation)
        .where(Conversation.user_id == user_id)
        .order_by(Conversation.created_at.desc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def create_conversation(
    session: AsyncSession, user_id: int, title: str | None = None
) -> int:
    conv = Conversation(user_id=user_id, title=title)
    session.add(conv)
    await session.flush()
    return conv.id


async def get_conversation(
    session: AsyncSession, conversation_id: int
) -> Conversation | None:
    stmt = select(Conversation).where(Conversation.id == conversation_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def update_conversation_title(
    session: AsyncSession, conversation_id: int, title: str
) -> None:
    stmt = select(Conversation).where(Conversation.id == conversation_id)
    result = await session.execute(stmt)
    conv = result.scalar_one_or_none()
    if conv:
        conv.title = title


async def delete_conversation(
    session: AsyncSession, conversation_id: int
) -> None:
    stmt = delete(Conversation).where(Conversation.id == conversation_id)
    await session.execute(stmt)


# ── Messages ───────────────────────────────────────────


async def create_message(
    session: AsyncSession, conversation_id: int, role: str, content: str
) -> int:
    msg = Message(conversation_id=conversation_id, role=role, content=content)
    session.add(msg)
    await session.flush()
    return msg.id


async def list_messages_by_conversation(
    session: AsyncSession, conversation_id: int
) -> list[Message]:
    stmt = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_message(
    session: AsyncSession, message_id: int
) -> Message | None:
    stmt = select(Message).where(Message.id == message_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


# ── Debug Events ────────────────────────────────────────


async def create_debug_event(
    session: AsyncSession,
    conversation_id: int,
    category: str,
    data: str,
    timestamp: str | None = None,
    message_id: int | None = None,
    step_id: int | None = None,
    seq: str = "0",
) -> int:
    event = DebugEvent(
        conversation_id=conversation_id,
        message_id=message_id,
        step_id=step_id,
        category=category,
        seq=seq,
        data=data,
        timestamp=timestamp,
    )
    session.add(event)
    await session.flush()
    return event.id


async def list_debug_events_by_conversation(
    session: AsyncSession, conversation_id: int
) -> list[DebugEvent]:
    stmt = (
        select(DebugEvent)
        .where(DebugEvent.conversation_id == conversation_id)
        .order_by(DebugEvent.seq.asc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def assign_message_id_to_debug_events(
    session: AsyncSession, conversation_id: int, message_id: int
) -> int:
    """Assign message_id to all unassigned debug events in a conversation.

    Safe because previous questions' events already have their message_id set,
    so only the current question's events match message_id IS NULL.
    """
    from sqlalchemy import update as sa_update

    stmt = (
        sa_update(DebugEvent)
        .where(
            DebugEvent.conversation_id == conversation_id,
            DebugEvent.message_id.is_(None),
        )
        .values(message_id=message_id)
    )
    result = await session.execute(stmt)
    return result.rowcount
