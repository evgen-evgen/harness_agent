from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path

from harness_agent.cache import default_cache_registry
from harness_agent.channels import default_channel_registry
from harness_agent.config import AgentConfig, RuntimeSettings
from harness_agent.guardrails import default_guardrail_registry
from harness_agent.memory import default_memory_registry
from harness_agent.scheduler import default_scheduler_registry
from harness_agent.sessions import default_session_registry
from harness_agent.skills import default_skill_registry
from harness_agent.tools import default_tool_registry


class DoctorSeverity:
    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True)
class DoctorIssue:
    severity: str
    code: str
    message: str


@dataclass(frozen=True)
class DoctorReport:
    issues: list[DoctorIssue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not any(issue.severity == DoctorSeverity.ERROR for issue in self.issues)

    @property
    def errors(self) -> list[DoctorIssue]:
        return [issue for issue in self.issues if issue.severity == DoctorSeverity.ERROR]

    @property
    def warnings(self) -> list[DoctorIssue]:
        return [issue for issue in self.issues if issue.severity == DoctorSeverity.WARNING]


def run_doctor(config: AgentConfig, settings: RuntimeSettings) -> DoctorReport:
    issues: list[DoctorIssue] = []
    issues.extend(_check_registries(config, settings))
    issues.extend(_check_model_env(config, settings))
    issues.extend(_check_channel_env(config, settings))
    issues.extend(_check_tool_env(config, settings))
    issues.extend(_check_storage_paths(settings))
    return DoctorReport(issues=issues)


def _check_registries(config: AgentConfig, settings: RuntimeSettings) -> list[DoctorIssue]:
    issues: list[DoctorIssue] = []
    tool_names = set(default_tool_registry(config, settings).names())
    skill_names = set(default_skill_registry().names())
    guardrail_names = set(default_guardrail_registry().names())
    channel_names = set(default_channel_registry().names())
    cache_names = set(default_cache_registry().names())
    memory_names = set(default_memory_registry().names())
    session_names = set(default_session_registry().names())
    scheduler_names = set(default_scheduler_registry().names())

    for name in config.tools:
        if name not in tool_names:
            issues.append(_error("unknown_tool", f"Unknown tool configured: {name}"))
            continue
        tool = default_tool_registry(config, settings).get(name)
        if tool.risk_level not in config.allowed_tool_risk_levels:
            issues.append(
                _error(
                    "tool_risk_not_allowed",
                    f"Tool {name} has risk level {tool.risk_level.value}, but it is not allowed",
                )
            )
    for name in config.skills:
        if name not in skill_names:
            issues.append(_error("unknown_skill", f"Unknown skill configured: {name}"))
    for name in config.guardrails:
        if name not in guardrail_names:
            issues.append(_error("unknown_guardrail", f"Unknown guardrail configured: {name}"))
    for name in config.channels:
        if name not in channel_names:
            issues.append(_error("unknown_channel", f"Unknown channel configured: {name}"))
    if config.cache not in cache_names:
        issues.append(_error("unknown_cache", f"Unknown cache store configured: {config.cache}"))
    if config.memory not in memory_names:
        issues.append(_error("unknown_memory", f"Unknown memory store configured: {config.memory}"))
    if config.session not in session_names:
        issues.append(_error("unknown_session", f"Unknown session store configured: {config.session}"))
    if config.scheduler not in scheduler_names:
        issues.append(_error("unknown_scheduler", f"Unknown scheduler store configured: {config.scheduler}"))
    return issues


def _check_model_env(config: AgentConfig, settings: RuntimeSettings) -> list[DoctorIssue]:
    model = config.model.casefold()
    if settings.litellm_api_key:
        return []
    if model.startswith("openai/") and not os.getenv("OPENAI_API_KEY"):
        return [_warning("missing_openai_key", "OPENAI_API_KEY or LITELLM_API_KEY is required for OpenAI models")]
    if model.startswith("anthropic/") and not os.getenv("ANTHROPIC_API_KEY"):
        return [_warning("missing_anthropic_key", "ANTHROPIC_API_KEY or LITELLM_API_KEY is required for Anthropic models")]
    return []


def _check_channel_env(config: AgentConfig, settings: RuntimeSettings) -> list[DoctorIssue]:
    issues: list[DoctorIssue] = []
    if settings.default_channel not in config.channels:
        issues.append(
            _warning(
                "default_channel_disabled",
                f"DEFAULT_CHANNEL={settings.default_channel} is not enabled in agent channels",
            )
        )
    if settings.default_channel == "telegram" and "telegram" in config.channels and not settings.telegram_bot_token:
        issues.append(_warning("missing_telegram_token", "TELEGRAM_BOT_TOKEN is required to serve Telegram"))
    return issues


def _check_tool_env(config: AgentConfig, settings: RuntimeSettings) -> list[DoctorIssue]:
    return []


def _check_storage_paths(settings: RuntimeSettings) -> list[DoctorIssue]:
    issues: list[DoctorIssue] = []
    for code, path in {
        "metrics_path": settings.metrics_path,
        "cache_path": settings.cache_path,
        "memory_path": settings.memory_path,
        "session_path": settings.session_path,
        "scheduler_path": settings.scheduler_path,
        "file_workspace_root": settings.file_workspace_root / ".harness_agent_workspace_probe",
    }.items():
        parent = Path(path).parent
        try:
            parent.mkdir(parents=True, exist_ok=True)
            probe = parent / ".harness_agent_write_check"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink()
        except OSError as exc:
            issues.append(_error(f"{code}_not_writable", f"{parent} is not writable: {exc}"))
    return issues


def _error(code: str, message: str) -> DoctorIssue:
    return DoctorIssue(DoctorSeverity.ERROR, code, message)


def _warning(code: str, message: str) -> DoctorIssue:
    return DoctorIssue(DoctorSeverity.WARNING, code, message)
