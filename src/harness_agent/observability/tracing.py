from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from time import perf_counter
from typing import Iterator
from uuid import uuid4

from harness_agent.metrics import RunMetrics


@dataclass(frozen=True)
class TraceContext:
    trace_id: str


class Tracer:
    def __init__(self, metrics: RunMetrics, trace_id: str | None = None) -> None:
        self.metrics = metrics
        self.context = TraceContext(trace_id=trace_id or str(uuid4()))

    @contextmanager
    def span(self, name: str, **attributes: object) -> Iterator[str]:
        span_id = str(uuid4())
        started = perf_counter()
        self.metrics.event(
            "span_started",
            trace_id=self.context.trace_id,
            span_id=span_id,
            span=name,
            **attributes,
        )
        try:
            yield span_id
        except Exception as exc:
            self.metrics.event(
                "span_failed",
                trace_id=self.context.trace_id,
                span_id=span_id,
                span=name,
                duration_ms=round((perf_counter() - started) * 1000, 2),
                error_type=type(exc).__name__,
                error=str(exc),
            )
            raise
        else:
            self.metrics.event(
                "span_finished",
                trace_id=self.context.trace_id,
                span_id=span_id,
                span=name,
                duration_ms=round((perf_counter() - started) * 1000, 2),
            )
