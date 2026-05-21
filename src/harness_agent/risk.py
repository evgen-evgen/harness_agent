from __future__ import annotations

from enum import StrEnum


class ToolRiskLevel(StrEnum):
    SAFE = "safe"
    READ_ONLY = "read_only"
    WRITE = "write"
    EXTERNAL_SIDE_EFFECT = "external_side_effect"
