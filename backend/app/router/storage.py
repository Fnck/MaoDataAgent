from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_user
from app.models import StorageItem
from app.service.storage import list_files, read_file

router = APIRouter(prefix="/api/storage", tags=["storage"])


@router.get("/list", response_model=list[StorageItem])
async def storage_list(
    prefix: str = "",
    current_user: dict = Depends(get_current_user),
) -> list[StorageItem]:
    try:
        return list_files(prefix)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Object storage error: {e}")


@router.get("/read")
async def storage_read(
    key: str,
    current_user: dict = Depends(get_current_user),
) -> dict[str, str]:
    try:
        content = read_file(key)
        return {"key": key, "content": content}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Object storage error: {e}")
