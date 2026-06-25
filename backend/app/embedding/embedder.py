from __future__ import annotations

from typing import Any

from openai import AsyncOpenAI

from app.config import get_config


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for a list of texts using the configured embedding model."""
    if not texts:
        return []

    config = get_config()
    client = AsyncOpenAI(base_url=config.embedding.api_base, api_key=config.embedding.api_key)

    response = await client.embeddings.create(
        model=config.embedding.model,
        input=texts,
    )

    return [item.embedding for item in response.data]


async def embed_query(query: str) -> list[float]:
    """Generate embedding for a single query text."""
    results = await embed_texts([query])
    return results[0]
