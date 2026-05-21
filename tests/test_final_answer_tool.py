import pytest

from harness_agent.tools.final_answer import FinalAnswerTool


@pytest.mark.anyio
async def test_final_answer_tool_returns_content() -> None:
    result = await FinalAnswerTool().run("done")

    assert result.ok
    assert result.content == "done"
