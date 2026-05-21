from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from harness_agent.risk import ToolRiskLevel
from harness_agent.tools.base import ToolResult


FileOperation = Literal["read", "write", "append", "mkdir", "list"]


class FilesystemTool:
    name = "filesystem"
    description = "Read, create, and modify files inside the configured workspace root only."
    risk_level = ToolRiskLevel.WRITE
    cacheable = False
    input_schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["read", "write", "append", "mkdir", "list"],
                "description": "Filesystem operation to perform.",
            },
            "path": {
                "type": "string",
                "description": "Relative path inside FILE_WORKSPACE_ROOT.",
            },
            "content": {
                "type": "string",
                "description": "Content for write or append operations.",
                "default": "",
            },
        },
        "required": ["operation", "path"],
        "additionalProperties": False,
    }

    def __init__(self, workspace_root: str | Path) -> None:
        self.workspace_root = Path(workspace_root).resolve()

    async def run(
        self,
        operation: FileOperation,
        path: str,
        content: str = "",
    ) -> ToolResult:
        target = self._resolve_inside_workspace(path)
        if target is None:
            return ToolResult(
                ok=False,
                content=f"filesystem access denied: path must stay inside {self.workspace_root}",
            )

        if operation == "read":
            if not target.is_file():
                return ToolResult(ok=False, content=f"not a file: {path}")
            return ToolResult(ok=True, content=target.read_text(encoding="utf-8"))

        if operation == "write":
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            return ToolResult(ok=True, content=f"wrote {path}", metadata={"path": str(target)})

        if operation == "append":
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("a", encoding="utf-8") as handle:
                handle.write(content)
            return ToolResult(ok=True, content=f"appended {path}", metadata={"path": str(target)})

        if operation == "mkdir":
            target.mkdir(parents=True, exist_ok=True)
            return ToolResult(ok=True, content=f"created directory {path}", metadata={"path": str(target)})

        if operation == "list":
            if not target.exists():
                return ToolResult(ok=False, content=f"path does not exist: {path}")
            if target.is_file():
                return ToolResult(ok=True, content=target.name)
            entries = sorted(item.name + ("/" if item.is_dir() else "") for item in target.iterdir())
            return ToolResult(ok=True, content="\n".join(entries) if entries else "(empty)")

        return ToolResult(ok=False, content=f"unknown filesystem operation: {operation}")

    def _resolve_inside_workspace(self, path: str) -> Path | None:
        requested = Path(path)
        if requested.is_absolute():
            return None
        target = (self.workspace_root / requested).resolve()
        try:
            target.relative_to(self.workspace_root)
        except ValueError:
            return None
        return target
