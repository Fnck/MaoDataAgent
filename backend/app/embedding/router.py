from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_user
from app.embedding import embedding_store
from app.embedding.schemas import (
    CollectionInfo,
    SearchRequest,
    SearchResult,
    StoreRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/embedding", tags=["embedding"])


@router.post("/store", status_code=201)
async def store_embeddings(
    req: StoreRequest,
    current_user: dict = Depends(get_current_user),
):
    """Store text embeddings in a collection."""
    items = [item.model_dump() for item in req.items]
    try:
        count = await embedding_store.store_embeddings(req.collection, items)
        return {"collection": req.collection, "stored": count}
    except Exception as e:
        logger.exception("Failed to store embeddings")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search", response_model=list[SearchResult])
async def search_embeddings(
    req: SearchRequest,
    current_user: dict = Depends(get_current_user),
):
    """Semantic search across embeddings in a collection."""
    try:
        results = await embedding_store.search(req.collection, req.query, req.top_k)
        return [SearchResult(**r) for r in results]
    except Exception as e:
        logger.exception("Failed to search embeddings")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{collection}/{item_id}")
async def delete_embedding(
    collection: str,
    item_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Delete a single embedding from a collection."""
    deleted = await embedding_store.delete_embedding(collection, item_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"deleted": True}


@router.get("/collections", response_model=list[CollectionInfo])
async def get_collections(
    current_user: dict = Depends(get_current_user),
):
    """List all embedding collections with row counts."""
    try:
        collections = await embedding_store.list_collections()
        return [CollectionInfo(**c) for c in collections]
    except Exception as e:
        logger.exception("Failed to list collections")
        raise HTTPException(status_code=500, detail=str(e))
