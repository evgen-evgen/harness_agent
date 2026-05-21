import pytest

from harness_agent.tools.current_time import CurrentTimeTool


@pytest.mark.anyio
async def test_current_time_tool_returns_time_for_valid_timezone() -> None:
    result = await CurrentTimeTool().run("Europe/Minsk")

    assert result.ok
    assert "The current local time in Europe/Minsk is:" in result.content
    assert result.metadata["timezone"] == "Europe/Minsk"


@pytest.mark.anyio
async def test_current_time_tool_handles_unknown_timezone() -> None:
    result = await CurrentTimeTool().run("No/Such_Zone")

    assert not result.ok
    assert "unknown timezone" in result.content
