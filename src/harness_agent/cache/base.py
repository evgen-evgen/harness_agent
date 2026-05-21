from __future__ import annotations

from typing import Protocol


class CacheStore(Protocol):
    async def get(self, namespace: str, key: str) -> str | None:
        ...

    async def set(
        self,
        namespace: str,
        key: str,
        value: str,
        *,
        ttl_seconds: int | None = None,
    ) -> None:
        ...
