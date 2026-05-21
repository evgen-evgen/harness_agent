from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path

from harness_agent.sessions.base import SessionMessage


class LocalJsonSessionStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._data: dict[str, list[dict[str, object]]] | None = None

    async def recent(self, session_id: str, limit: int) -> list[SessionMessage]:
        if limit <= 0:
            return []
        records = self._load().get(session_id, [])[-limit:]
        return [
            SessionMessage(
                role=str(record["role"]),  # type: ignore[arg-type]
                content=str(record["content"]),
                metadata={key: str(value) for key, value in dict(record.get("metadata", {})).items()},
            )
            for record in records
        ]

    async def append(self, session_id: str, message: SessionMessage) -> None:
        data = self._load()
        data.setdefault(session_id, []).append(
            {
                "ts": datetime.now(UTC).isoformat(),
                "role": message.role,
                "content": message.content,
                "metadata": message.metadata,
            }
        )
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _load(self) -> dict[str, list[dict[str, object]]]:
        if self._data is not None:
            return self._data
        if not self.path.exists():
            self._data = {}
            return self._data
        self._data = json.loads(self.path.read_text(encoding="utf-8") or "{}")
        return self._data

