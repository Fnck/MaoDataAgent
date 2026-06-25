from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


# ── Auth ───────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    role: str


class LoginResponse(BaseModel):
    token: str
    user: UserOut


class ResetPasswordRequest(BaseModel):
    target_username: str
    new_password: str


# ── Conversations ──────────────────────────────────────

class ConversationCreate(BaseModel):
    title: str | None = None


class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str | None
    created_at: datetime


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: str
    content: str
    created_at: datetime


class ConversationDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str | None
    created_at: datetime
    messages: list[MessageOut] = []


# ── Chat ───────────────────────────────────────────────

class ChatContext(BaseModel):
    selected_files: list[str] = []
    selected_tables: list[str] = []


class ChatRequest(BaseModel):
    message: str
    conversation_id: int
    context: ChatContext | None = None
    workflow_mode: str | None = None  # Override config: "none" | "dynamic" | "yaml"


# ── Workflow ───────────────────────────────────────────

class WorkflowStepOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    step_index: int
    step_type: str
    step_name: str
    input: str | None = None
    output: str | None = None
    status: str
    error: str | None = None
    started_at: datetime
    finished_at: datetime | None = None


class WorkflowExecutionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    conversation_id: int
    message_id: int | None = None
    mode: str
    workflow_name: str | None = None
    status: str
    final_answer: str | None = None
    started_at: datetime
    finished_at: datetime | None = None
    steps: list[WorkflowStepOut] = []


# ── Storage ────────────────────────────────────────────

class StorageItem(BaseModel):
    key: str
    size: int = 0
    last_modified: str | None = None
    is_dir: bool = False


# ── Datasource ─────────────────────────────────────────

class TableInfo(BaseModel):
    datasource_name: str
    table_name: str


class ColumnInfo(BaseModel):
    name: str
    type: str
    comment: str | None = None


# ── Debug ──────────────────────────────────────────────

class DebugEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event_id: int
    conversation_id: int
    message_id: int | None = None
    step_id: int | None = None
    category: str
    data: dict[str, Any]
    timestamp: datetime
