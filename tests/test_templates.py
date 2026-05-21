from pathlib import Path

import pytest
from typer.testing import CliRunner

from harness_agent.cli import app
from harness_agent.config import AgentConfig, RuntimeSettings
from harness_agent.templates import default_template_registry


def test_template_scaffolder_creates_agent(tmp_path: Path) -> None:
    root = default_template_registry().create(name="test_agent", output_dir=tmp_path)

    assert (root / "agent.yaml").exists()
    assert (root / "prompts" / "system.md").exists()
    assert (root / "evals" / "smoke.yaml").exists()
    loaded = AgentConfig.from_yaml(root / "agent.yaml", settings=RuntimeSettings(_env_file=None))
    assert loaded.name == "test_agent"


def test_template_scaffolder_rejects_invalid_name(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        default_template_registry().create(name="Bad-Name", output_dir=tmp_path)


def test_new_agent_cli_creates_agent(tmp_path: Path) -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["new-agent", "cli_agent", "--output-dir", str(tmp_path)])

    assert result.exit_code == 0
    assert (tmp_path / "cli_agent" / "agent.yaml").exists()
    assert "Created agent template" in result.output
