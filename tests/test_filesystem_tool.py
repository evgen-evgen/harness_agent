import pytest

from harness_agent.tools.filesystem import FilesystemTool


@pytest.mark.anyio
async def test_filesystem_tool_writes_and_reads_inside_workspace(tmp_path) -> None:
    tool = FilesystemTool(tmp_path)

    write = await tool.run("write", "notes/todo.txt", "hello")
    read = await tool.run("read", "notes/todo.txt")

    assert write.ok
    assert read.ok
    assert read.content == "hello"
    assert (tmp_path / "notes" / "todo.txt").read_text(encoding="utf-8") == "hello"


@pytest.mark.anyio
async def test_filesystem_tool_blocks_parent_traversal(tmp_path) -> None:
    tool = FilesystemTool(tmp_path / "workspace")

    result = await tool.run("write", "../outside.txt", "bad")

    assert not result.ok
    assert "access denied" in result.content
    assert not (tmp_path / "outside.txt").exists()


@pytest.mark.anyio
async def test_filesystem_tool_blocks_absolute_path_outside_workspace(tmp_path) -> None:
    tool = FilesystemTool(tmp_path / "workspace")

    result = await tool.run("read", str(tmp_path / "outside.txt"))

    assert not result.ok
    assert "access denied" in result.content


@pytest.mark.anyio
async def test_filesystem_tool_append_is_not_cached_via_metadata_contract() -> None:
    tool = FilesystemTool("/tmp")

    assert tool.cacheable is False
