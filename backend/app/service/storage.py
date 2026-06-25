from __future__ import annotations

from tos import TosClientV2

from app.config import get_config
from app.models import StorageItem

_client: TosClientV2 | None = None


def get_tos_client() -> TosClientV2:
    global _client
    if _client is None:
        cfg = get_config().object_storage
        _client = tos.TosClientV2(cfg.access_key, cfg.secret_key, cfg.endpoint, cfg.region)
    return _client


def list_files(prefix: str = "") -> list[StorageItem]:
    client = get_tos_client()
    bucket = get_config().object_storage.bucket

    result = client.list_objects(Bucket=bucket, Prefix=prefix or None, Delimiter="/")

    items: list[StorageItem] = []

    # Directories (common prefixes)
    for p in (result.CommonPrefixes or []):
        items.append(StorageItem(key=p.Prefix, is_dir=True))

    # Objects
    for obj in (result.Contents or []):
        # Skip the directory marker object itself
        if obj.Key == prefix:
            continue
        items.append(
            StorageItem(
                key=obj.Key,
                size=obj.Size or 0,
                last_modified=str(obj.LastModified) if obj.LastModified else None,
                is_dir=False,
            )
        )

    return items


def read_file(key: str) -> str:
    client = get_tos_client()
    bucket = get_config().object_storage.bucket

    result = client.get_object(Bucket=bucket, Key=key)
    content = result.read().decode("utf-8")
    result.close()
    return content
