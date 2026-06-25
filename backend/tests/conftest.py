from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Ensure backend is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.base import Base
import app.db.models  # noqa: F401 — register core models
import app.ontology.models  # noqa: F401 — register ontology models
import app.db.business_models  # noqa: F401 — register business domain models
from app.config import AppConfig
from app.service.debug_bus import DebugEventBus


@pytest.fixture(scope="session")
def event_loop():
    """Create a session-scoped event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def db_session():
    """Provide an async SQLAlchemy session backed by an in-memory SQLite database."""
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        echo=False,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
def test_config():
    """Return a minimal AppConfig for unit tests."""
    return AppConfig(
        llm={
            "api_base": "http://fake-api",
            "api_key": "test-key",
            "model": "test-model",
            "max_tokens": 256,
            "temperature": 0.0,
        },
        workflow={
            "mode": "none",
            "tools": [],
            "yaml_dir": "tests/workflows",
            "max_iterations": 3,
        },
        datasources=[
            {"name": "test_db", "type": "sqlite", "path": ":memory:"},
        ],
    )


@pytest.fixture
def bus(db_session):
    """Provide a DebugEventBus backed by the test session."""
    return DebugEventBus(db_session, conversation_id=1)


# ── FastAPI Test Client fixtures ──────────────────────────────

@pytest_asyncio.fixture
async def app():
    """Create a FastAPI app instance for testing with in-memory SQLite."""
    from unittest.mock import patch

    test_engine = create_async_engine(
        "sqlite+aiosqlite://",
        echo=False,
        connect_args={"check_same_thread": False},
    )

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    test_session_factory = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )

    async def override_get_session():
        async with test_session_factory() as session:
            yield session

    # Patch config singleton
    test_cfg = AppConfig(
        llm={
            "api_base": "http://fake-api",
            "api_key": "test-key",
            "model": "test-model",
            "max_tokens": 256,
            "temperature": 0.0,
        },
        auth={"jwt_secret": "test-secret-key-for-unit-tests", "token_expire_hours": 24},
        workflow={"mode": "none", "tools": [], "yaml_dir": "workflows", "max_iterations": 3},
        datasources=[{"name": "test_db", "type": "sqlite", "path": ":memory:"}],
    )

    with patch("app.config._config", test_cfg):
        from app.main import app as fastapi_app
        from app.db.session import get_async_session

        fastapi_app.dependency_overrides[get_async_session] = override_get_session

        yield fastapi_app

        fastapi_app.dependency_overrides.clear()

    await test_engine.dispose()


@pytest_asyncio.fixture
async def client(app):
    """Provide an async HTTP test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def db_session_from_app(app):
    """Get a db session from the test app's engine for direct DB operations."""
    from app.db.session import get_async_session
    # The override is already set in the app fixture; get a session manually
    gen = app.dependency_overrides[get_async_session]()
    session = await gen.__anext__()
    yield session
    try:
        await gen.__anext__()
    except StopAsyncIteration:
        pass


@pytest_asyncio.fixture
async def auth_token(client, db_session_from_app):
    """Create a test user and return a valid JWT token."""
    from app.auth import hash_password
    from app.db.database import create_user

    user_id = await create_user(
        db_session_from_app,
        username="testuser",
        password_hash=hash_password("testpass123"),
        role="user",
    )
    await db_session_from_app.commit()

    resp = await client.post("/api/auth/login", json={
        "username": "testuser",
        "password": "testpass123",
    })
    assert resp.status_code == 200
    data = resp.json()
    return data["token"]


@pytest_asyncio.fixture
async def admin_token(client, db_session_from_app):
    """Create an admin user and return a valid JWT token."""
    from app.auth import hash_password
    from app.db.database import create_user

    user_id = await create_user(
        db_session_from_app,
        username="admin",
        password_hash=hash_password("adminpass123"),
        role="admin",
    )
    await db_session_from_app.commit()

    resp = await client.post("/api/auth/login", json={
        "username": "admin",
        "password": "adminpass123",
    })
    assert resp.status_code == 200
    data = resp.json()
    return data["token"]


def auth_headers(token: str) -> dict:
    """Return authorization headers for a given token."""
    return {"Authorization": f"Bearer {token}"}


# ── Shared SSE / LLM mock helpers ──────────────────────────────

async def collect_sse_events(generator) -> list[dict]:
    """Collect all SSE events from an async generator into a list of parsed dicts."""
    events = []
    async for raw in generator:
        body = raw[len("data: "):-2]  # strip "data: " prefix and "\n\n" suffix
        events.append(json.loads(body))
    return events


def make_llm_response(content: str, finish_reason: str = "stop", usage=None) -> AsyncMock:
    """Create a mock non-streaming LLM response."""
    mock = AsyncMock()
    mock.choices = [AsyncMock()]
    mock.choices[0].message.content = content
    mock.choices[0].finish_reason = finish_reason
    mock.usage = usage
    return mock


async def make_streaming_response(chunks_text: list[str]):
    """Create a mock streaming LLM response as an async generator of chunks."""
    for text in chunks_text:
        chunk = MagicMock()
        chunk.choices = [MagicMock()]
        chunk.choices[0].delta.content = text
        chunk.choices[0].finish_reason = None
        chunk.usage = None
        yield chunk
    # Final chunk with finish_reason
    final = MagicMock()
    final.choices = [MagicMock()]
    final.choices[0].delta.content = None
    final.choices[0].finish_reason = "stop"
    final.usage = MagicMock(prompt_tokens=10, completion_tokens=20, total_tokens=30)
    yield final
