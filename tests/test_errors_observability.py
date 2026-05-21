from harness_agent.errors import ErrorKind, ToolExecutionError
from harness_agent.metrics import JsonlMetricsSink, RunMetrics
from harness_agent.observability import Tracer


def test_agent_error_serializes() -> None:
    error = ToolExecutionError("failed", details={"tool": "x"})

    assert error.to_dict() == {
        "kind": ErrorKind.TOOL.value,
        "message": "failed",
        "retryable": False,
        "details": {"tool": "x"},
    }


def test_tracer_writes_span_events(tmp_path) -> None:
    metrics = RunMetrics(JsonlMetricsSink(tmp_path / "metrics.jsonl"), agent_name="a", model="m")
    tracer = Tracer(metrics, trace_id="trace-1")

    with tracer.span("unit", key="value"):
        pass

    content = (tmp_path / "metrics.jsonl").read_text(encoding="utf-8")
    assert "span_started" in content
    assert "span_finished" in content
    assert "trace-1" in content
