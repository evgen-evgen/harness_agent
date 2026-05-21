from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from harness_agent.risk import ToolRiskLevel


class RuntimeSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    litellm_model: str | None = Field(default=None, alias="LITELLM_MODEL")
    litellm_api_key: str | None = Field(default=None, alias="LITELLM_API_KEY")
    litellm_api_base: str | None = Field(default=None, alias="LITELLM_API_BASE")
    litellm_api_version: str | None = Field(default=None, alias="LITELLM_API_VERSION")
    metrics_path: Path = Field(default=Path("runs/metrics.jsonl"), alias="METRICS_PATH")
    brave_search_api_key: str | None = Field(default=None, alias="BRAVE_SEARCH_API_KEY")
    tavily_api_key: str | None = Field(default=None, alias="TAVILY_API_KEY")
    default_channel: str = Field(default="telegram", alias="DEFAULT_CHANNEL")
    telegram_bot_token: str | None = Field(default=None, alias="TELEGRAM_BOT_TOKEN")
    telegram_thinking_message: str | None = Field(
        default="Думаю...",
        alias="TELEGRAM_THINKING_MESSAGE",
    )
    cache_path: Path = Field(default=Path("runs/cache.json"), alias="CACHE_PATH")
    cache_ttl_seconds: int | None = Field(default=3600, alias="CACHE_TTL_SECONDS")
    web_search_cache_ttl_seconds: int | None = Field(
        default=900,
        alias="WEB_SEARCH_CACHE_TTL_SECONDS",
    )
    memory_path: Path = Field(default=Path("runs/memory.jsonl"), alias="MEMORY_PATH")
    session_path: Path = Field(default=Path("runs/sessions.json"), alias="SESSION_PATH")
    scheduler_path: Path = Field(default=Path("runs/scheduled_tasks.json"), alias="SCHEDULER_PATH")
    scheduler_poll_seconds: float = Field(default=10.0, alias="SCHEDULER_POLL_SECONDS")
    file_workspace_root: Path = Field(default=Path("agent_workspace"), alias="FILE_WORKSPACE_ROOT")


class AgentConfig(BaseModel):
    name: str
    model: str
    system_prompt: str
    tools: list[str] = Field(default_factory=list)
    allowed_tool_risk_levels: list[ToolRiskLevel] = Field(
        default_factory=lambda: [ToolRiskLevel.SAFE, ToolRiskLevel.READ_ONLY]
    )
    skills: list[str] = Field(default_factory=list)
    guardrails: list[str] = Field(default_factory=lambda: ["default"])
    max_iterations: int = 8
    temperature: float = 0.2
    metadata: dict[str, Any] = Field(default_factory=dict)
    channels: list[str] = Field(default_factory=lambda: ["telegram"])
    cache: str = "local_json"
    cache_ttl_seconds: int | None = 3600
    memory: str = "local_jsonl"
    memory_top_k: int = 5
    memory_max_chars: int = 2_000
    session: str = "local_json"
    session_history_limit: int = 10
    context_max_chars: int = 24_000
    context_memory_max_chars: int = 6_000
    context_session_max_chars: int = 8_000
    scheduler: str = "local_json"

    @field_validator("max_iterations")
    @classmethod
    def max_iterations_must_be_positive(cls, value: int) -> int:
        if value < 1:
            raise ValueError("max_iterations must be >= 1")
        return value

    @classmethod
    def from_yaml(cls, path: str | Path, settings: RuntimeSettings | None = None) -> "AgentConfig":
        config_path = Path(path)
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}

        prompt_ref = raw.get("system_prompt")
        if not prompt_ref:
            raise ValueError("agent config must define system_prompt")

        prompt_path = config_path.parent / prompt_ref
        raw["system_prompt"] = prompt_path.read_text(encoding="utf-8")

        runtime = settings or RuntimeSettings()
        if runtime.litellm_model:
            raw["model"] = runtime.litellm_model

        return cls.model_validate(raw)
