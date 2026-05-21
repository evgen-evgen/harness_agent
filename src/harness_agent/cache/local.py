from __future__ import annotations

from datetime import UTC, datetime, timedelta
import json
from pathlib import Path
from typing import Any


class LocalJsonCacheStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._data: dict[str, dict[str, Any]] | None = None

    async def get(self, namespace: str, key: str) -> str | None:
        data = self._load()
        value = data.get(namespace, {}).get(key)
        if value is None:
            return None
        if isinstance(value, str):
            return value
        expires_at = value.get("expires_at")
        if expires_at and datetime.fromisoformat(expires_at) <= datetime.now(UTC):
            del data[namespace][key]
            self._save(data)
            return None
        content = value.get("value")
        return content if isinstance(content, str) else None

    async def set(
        self,
        namespace: str,
        key: str,
        value: str,
        *,
        ttl_seconds: int | None = None,
    ) -> None:
        data = self._load()
        expires_at = None
        if ttl_seconds is not None and ttl_seconds > 0:
            expires_at = (datetime.now(UTC) + timedelta(seconds=ttl_seconds)).isoformat()
        data.setdefault(namespace, {})[key] = {
            "value": value,
            "expires_at": expires_at,
            "created_at": datetime.now(UTC).isoformat(),
        }
        self._save(data)

    def _load(self) -> dict[str, dict[str, Any]]:
        if self._data is not None:
            return self._data
        if not self.path.exists():
            self._data = {}
            return self._data
        self._data = json.loads(self.path.read_text(encoding="utf-8") or "{}")
        return self._data

    def _save(self, data: dict[str, dict[str, Any]]) -> None:
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
