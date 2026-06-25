"""
Unit tests for Auth API endpoints (/api/auth).

Based on the business analysis document's user/role requirements.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.auth import hash_password
from app.db.database import create_user


class TestLogin:
    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient, db_session_from_app):
        await create_user(
            db_session_from_app,
            username="user1",
            password_hash=hash_password("pass123"),
            role="user",
        )
        await db_session_from_app.commit()

        resp = await client.post("/api/auth/login", json={
            "username": "user1",
            "password": "pass123",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "token" in data
        assert data["user"]["username"] == "user1"
        assert data["user"]["role"] == "user"

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client: AsyncClient, db_session_from_app):
        await create_user(
            db_session_from_app,
            username="user2",
            password_hash=hash_password("correct"),
            role="user",
        )
        await db_session_from_app.commit()

        resp = await client.post("/api/auth/login", json={
            "username": "user2",
            "password": "wrong",
        })
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, client: AsyncClient):
        resp = await client.post("/api/auth/login", json={
            "username": "ghost",
            "password": "nopass",
        })
        assert resp.status_code == 401


class TestMe:
    @pytest.mark.asyncio
    async def test_me_success(self, client: AsyncClient, auth_token: str):
        resp = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {auth_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "testuser"
        assert data["role"] == "user"

    @pytest.mark.asyncio
    async def test_me_no_token(self, client: AsyncClient):
        resp = await client.get("/api/auth/me")
        assert resp.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_me_invalid_token(self, client: AsyncClient):
        resp = await client.get("/api/auth/me", headers={"Authorization": "Bearer invalid.token.here"})
        assert resp.status_code == 401


class TestResetPassword:
    @pytest.mark.asyncio
    async def test_reset_password_as_admin(self, client: AsyncClient, admin_token: str, db_session_from_app):
        # Create a target user
        await create_user(
            db_session_from_app,
            username="target_user",
            password_hash=hash_password("oldpass"),
            role="user",
        )
        await db_session_from_app.commit()

        resp = await client.post(
            "/api/auth/reset-password",
            json={"target_username": "target_user", "new_password": "newpass999"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200

        # Verify new password works
        login_resp = await client.post("/api/auth/login", json={
            "username": "target_user",
            "password": "newpass999",
        })
        assert login_resp.status_code == 200

    @pytest.mark.asyncio
    async def test_reset_password_non_admin_forbidden(self, client: AsyncClient, auth_token: str):
        resp = await client.post(
            "/api/auth/reset-password",
            json={"target_username": "someone", "new_password": "hack"},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_reset_password_user_not_found(self, client: AsyncClient, admin_token: str):
        resp = await client.post(
            "/api/auth/reset-password",
            json={"target_username": "nonexistent", "new_password": "pass"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 404
