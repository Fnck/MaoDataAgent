from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class StoreItem(BaseModel):
    id: str
    text: str
    metadata: dict | None = None


class StoreRequest(BaseModel):
    collection: str
    items: list[StoreItem]


class SearchRequest(BaseModel):
    collection: str
    query: str
    top_k: int = Field(default=10, ge=1, le=100)


class SearchResult(BaseModel):
    id: str
    text: str
    score: float
    metadata: dict | None = None


class CollectionInfo(BaseModel):
    name: str
    row_count: int
