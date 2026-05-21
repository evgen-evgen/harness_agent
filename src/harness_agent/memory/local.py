from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import re
from uuid import uuid4

from harness_agent.memory.base import MemoryRecord


class LocalJsonlMemoryStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    async def add(self, content: str, metadata: dict[str, str] | None = None) -> None:
        normalized = content.strip()
        if not normalized:
            return
        record = {
            "id": str(uuid4()),
            "created_at": datetime.now(UTC).isoformat(),
            "content": normalized,
            "metadata": metadata or {},
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    async def search(self, query: str, limit: int) -> list[MemoryRecord]:
        if limit <= 0 or not self.path.exists():
            return []
        query_terms = self._terms(query)
        if not query_terms:
            return []

        matches: list[MemoryRecord] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            raw = json.loads(line)
            content = raw.get("content", "")
            content_terms = self._terms(content)
            overlap = query_terms & content_terms
            if not overlap:
                continue
            score = len(overlap) / max(len(query_terms), 1)
            matches.append(
                MemoryRecord(
                    content=content,
                    score=score,
                    metadata={key: str(value) for key, value in raw.get("metadata", {}).items()},
                )
            )
        matches.sort(key=lambda record: record.score, reverse=True)
        return matches[:limit]

    @staticmethod
    def _terms(text: str) -> set[str]:
        return {item.casefold() for item in re.findall(r"[\wА-Яа-яЁё]{3,}", text)}

