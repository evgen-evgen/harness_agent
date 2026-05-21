from pathlib import Path

from typer.testing import CliRunner

from harness_agent.cli import app
from harness_agent.config import AgentConfig, RuntimeSettings
from harness_agent.doctor import run_doctor


def _settings(tmp_path: Path) -> RuntimeSettings:
    return RuntimeSettings(
        _env_file=None,
        METRICS_PATH=tmp_path / "metrics.jsonl",
        CACHE_PATH=tmp_path / "cache.json",
        MEMORY_PATH=tmp_path / "memory.jsonl",
        SESSION_PATH=tmp_path / "sessions.json",
        SCHEDULER_PATH=tmp_path / "scheduled.json",
        DEFAULT_CHANNEL="console",
    )


def test_doctor_reports_unknown_tool_as_error(tmp_path: Path) -> None:
    config = AgentConfig(
        name="test",
        model="test/model",
        system_prompt="system",
        tools=["missing_tool"],
        channels=["console"],
    )

    report = run_doctor(config, _settings(tmp_path))

    assert not report.ok
    assert report.errors[0].code == "unknown_tool"


def test_doctor_reports_missing_openai_key_as_warning(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    config = AgentConfig(
        name="test",
        model="openai/gpt-5",
        system_prompt="system",
        tools=[],
        channels=["console"],
    )

    report = run_doctor(config, _settings(tmp_path))

    assert report.ok
    assert any(issue.code == "missing_openai_key" for issue in report.warnings)


def test_doctor_reports_disallowed_tool_risk_as_error(tmp_path: Path) -> None:
    config = AgentConfig(
        name="test",
        model="test/model",
        system_prompt="system",
        tools=["schedule_task"],
        channels=["console"],
    )

    report = run_doctor(config, _settings(tmp_path))

    assert not report.ok
    assert any(issue.code == "tool_risk_not_allowed" for issue in report.errors)


def test_doctor_cli_exits_nonzero_on_errors(tmp_path: Path) -> None:
    prompt = tmp_path / "system.md"
    prompt.write_text("system", encoding="utf-8")
    config = tmp_path / "agent.yaml"
    config.write_text(
        """
name: bad_agent
model: test/model
system_prompt: system.md
tools:
  - missing_tool
channels:
  - console
""",
        encoding="utf-8",
    )
    runner = CliRunner()

    result = runner.invoke(app, ["doctor", "--agent", str(config)])

    assert result.exit_code == 1
    assert "ERROR unknown_tool" in result.output
