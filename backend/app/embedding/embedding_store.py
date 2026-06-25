from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import lancedb
import pyarrow as pa
from lancedb.db import LanceDBConnection

from app.config import get_config
from app.embedding.embedder import embed_texts, embed_query

logger = logging.getLogger(__name__)

_db: LanceDBConnection | None = None


def _get_db() -> LanceDBConnection:
    global _db
    if _db is None:
        config = get_config()
        db_path = Path(config.embedding.lancedb_path)
        db_path.mkdir(parents=True, exist_ok=True)
        _db = lancedb.connect(str(db_path))
        logger.info("LanceDB connected at %s", db_path)
    return _db


def _ensure_key_field(schema: pa.Schema, existing: pa.Schema) -> pa.Schema:
    """LanceDB requires a key field. Use 'id' as the key."""
    if any(f.name == "id" for f in existing):
        return existing
    # Add id metadata if needed; LanceDB handles this via the create_table schema
    return existing


async def init_embedding_store() -> None:
    """Initialize the embedding store on application startup."""
    db = _get_db()
    logger.info("Embedding store initialized, existing tables: %s", db.table_names())


async def store_embeddings(collection_name: str, items: list[dict]) -> int:
    """Store embeddings in a LanceDB collection.

    Each item should have: id, text, and optionally metadata.
    Embeddings are generated and stored automatically.
    Returns the number of items stored.
    """
    if not items:
        return 0

    db = _get_db()
    texts = [item["text"] for item in items]
    embeddings = await embed_texts(texts)

    # Build rows with embeddings
    now = datetime.now(timezone.utc).isoformat()
    rows = []
    for i, item in enumerate(items):
        rows.append({
            "id": item["id"],
            "text": item["text"],
            "embedding": embeddings[i],
            "metadata": json.dumps(item.get("metadata") or {}, ensure_ascii=False),
            "created_at": now,
        })

    # Determine embedding dimension from the first embedding
    dim = len(embeddings[0]) if embeddings else 1536

    schema = pa.schema([
        pa.field("id", pa.string()),
        pa.field("text", pa.string()),
        pa.field("embedding", pa.list_(pa.float32(), dim)),
        pa.field("metadata", pa.string()),
        pa.field("created_at", pa.string()),
    ])

    try:
        table = db.open_table(collection_name)
    except Exception:
        table = db.create_table(collection_name, schema=schema)

    table.add(rows)
    logger.info("Stored %d embeddings in collection '%s'", len(rows), collection_name)
    return len(rows)


async def search(collection_name: str, query_text: str, top_k: int = 10) -> list[dict]:
    """Search for the most similar embeddings to the query text."""
    db = _get_db()

    try:
        table = db.open_table(collection_name)
    except Exception:
        logger.debug("Collection '%s' not found", collection_name)
        return []

    query_embedding = await embed_query(query_text)

    results = table.search(query_embedding).limit(top_k).to_list()

    return [
        {
            "id": r["id"],
            "text": r["text"],
            "score": 1.0 / (1.0 + r.get("_distance", 0)),
            "metadata": json.loads(r["metadata"]) if r.get("metadata") else None,
        }
        for r in results
    ]


async def delete_embedding(collection_name: str, item_id: str) -> bool:
    """Delete an embedding by its ID."""
    db = _get_db()

    try:
        table = db.open_table(collection_name)
    except Exception:
        logger.debug("Collection '%s' not found", collection_name)
        return False

    table.delete(f"id = '{item_id}'")
    logger.debug("Deleted embedding '%s' from collection '%s'", item_id, collection_name)
    return True


async def list_collections() -> list[dict]:
    """List all embedding collections with row counts."""
    db = _get_db()
    names = db.table_names()
    result = []
    for name in names:
        try:
            table = db.open_table(name)
            count = table.count_rows()
        except Exception:
            count = 0
        result.append({"name": name, "row_count": count})
    return result
