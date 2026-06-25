"""
Unit tests for Conversation API endpoints (/api/conversations).
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.auth import hash_password
from app.db.database import create_user, create_conversation, create_message


class TestListConversations:
    @pytest.mark.asyncio
    async def test_list_empty(self, client: AsyncClient, auth_token: str):
        resp = await client.get(
            "/api/conversations",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_list_after_create(self, client: AsyncClient, auth_token: str):
        headers = {"Authorization": f"Bearer {auth_token}"}
        await client.post("/api/conversations", json={"title": "Conv 1"}, headers=headers)
        await client.post("/api/conversations", json={"title": "Conv 2"}, headers=headers)

        resp = await client.get("/api/conversations", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2

    @pytest.mark.asyncio
    async def test_list_only_own_conversations(self, client: AsyncClient, db_session_from_app):
        # Create two users
        user1_id = await create_user(db_session_from_app, "u1", hash_password("p"), "user")
        user2_id = await create_user(db_session_from_app, "u2", hash_password("p"), "user")
        await db_session_from_app.commit()

        # Create conversations for user1
        await create_conversation(db_session_from_app, user1_id, "User1 Conv")
        await create_conversation(db_session_from_app, user2_id, "User2 Conv")
        await db_session_from_app.commit()

        # Login as user1
        resp = await client.post("/api/auth/login", json={"username": "u1", "password": "p"})
        token = resp.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.get("/api/conversations", headers=headers)
        data = resp.json()
        assert len(data) == 1
        assert data[0]["title"] == "User1 Conv"


class TestCreateConversation:
    @pytest.mark.asyncio
    async def test_create_with_title(self, client: AsyncClient, auth_token: str):
        resp = await client.post(
            "/api/conversations",
            json={"title": "Test Conversation"},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Test Conversation"
        assert "id" in data
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_create_without_title(self, client: AsyncClient, auth_token: str):
        resp = await client.post(
            "/api/conversations",
            json={},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["title"] is None


class TestGetConversationDetail:
    @pytest.mark.asyncio
    async def test_get_detail_with_messages(self, client: AsyncClient, auth_token: str, db_session_from_app):
        from app.db.database import get_user_by_username

        headers = {"Authorization": f"Bearer {auth_token}"}

        # Create conversation via API
        create_resp = await client.post(
            "/api/conversations",
            json={"title": "Detail Test"},
            headers=headers,
        )
        conv_id = create_resp.json()["id"]

        # Add messages directly to DB
        await create_message(db_session_from_app, conv_id, "user", "Hello")
        await create_message(db_session_from_app, conv_id, "assistant", "Hi there")
        await db_session_from_app.commit()

        resp = await client.get(f"/api/conversations/{conv_id}", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Detail Test"
        assert len(data["messages"]) == 2
        assert data["messages"][0]["role"] == "user"
        assert data["messages"][1]["role"] == "assistant"

    @pytest.mark.asyncio
    async def test_get_nonexistent_conversation(self, client: AsyncClient, auth_token: str):
        resp = await client.get(
            "/api/conversations/99999",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert resp.status_code == 404


class TestDeleteConversation:
    @pytest.mark.asyncio
    async def test_delete_success(self, client: AsyncClient, auth_token: str):
        headers = {"Authorization": f"Bearer {auth_token}"}

        create_resp = await client.post(
            "/api/conversations",
            json={"title": "To Delete"},
            headers=headers,
        )
        conv_id = create_resp.json()["id"]

        del_resp = await client.delete(f"/api/conversations/{conv_id}", headers=headers)
        assert del_resp.status_code == 200

        # Verify it's gone
        get_resp = await client.get(f"/api/conversations/{conv_id}", headers=headers)
        assert get_resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, client: AsyncClient, auth_token: str):
        resp = await client.delete(
            "/api/conversations/99999",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert resp.status_code == 404
