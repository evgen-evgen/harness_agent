from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from time import perf_counter
from typing import Any
from uuid import uuid4


class JsonlMetricsSink:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def emit(self, event: str, **payload: Any) -> None:
        record = {
            "ts": datetime.now(UTC).isoformat(),
            "event": event,
            **payload,
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


class RunMetrics:
    def __init__(self, sink: JsonlMetricsSink, *, agent_name: str, model: str) -> None:
        self.run_id = str(uuid4())
        self._sink = sink
        self._agent_name = agent_name
        self._model = model
        self._started = perf_counter()
        self.tool_calls = 0
        self.llm_calls = 0

    def event(self, event: str, **payload: Any) -> None:
        self._sink.emit(
            event,
            run_id=self.run_id,
            agent=self._agent_name,
            model=self._model,
            **payload,
        )

    def finish_payload(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "duration_ms": round((perf_counter() - self._started) * 1000, 2),
            "tool_calls": self.tool_calls,
            "llm_calls": self.llm_calls,
        }

