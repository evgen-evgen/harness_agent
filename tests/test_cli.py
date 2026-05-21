from typer.testing import CliRunner

from harness_agent.cli import app


def test_serve_telegram_without_token_returns_cli_error() -> None:
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["serve", "--agent", "agents/example/agent.yaml", "--channel", "telegram"],
        env={"TELEGRAM_BOT_TOKEN": ""},
    )

    assert result.exit_code != 0
    assert "TELEGRAM_BOT_TOKEN is required" in result.output
