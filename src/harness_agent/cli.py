from __future__ import annotations

import asyncio
from pathlib import Path

import typer
from rich.console import Console

from harness_agent.agent import AgentRunner
from harness_agent.cache import default_cache_registry
from harness_agent.channels import default_channel_registry
from harness_agent.config import AgentConfig, RuntimeSettings
from harness_agent.doctor import DoctorSeverity, run_doctor
from harness_agent.evals import EvalRunner
from harness_agent.guardrails import default_guardrail_registry
from harness_agent.memory import default_memory_registry
from harness_agent.runtime import AgentRuntime
from harness_agent.scheduler import TaskStatus, default_scheduler_registry
from harness_agent.sessions import default_session_registry
from harness_agent.skills import default_skill_registry
from harness_agent.templates import default_template_registry
from harness_agent.tools import default_tool_registry

app = typer.Typer(no_args_is_help=True)
tasks_app = typer.Typer(no_args_is_help=True)
app.add_typer(tasks_app, name="tasks")
console = Console()


@app.command()
def run(
    prompt: str = typer.Argument(..., help="User prompt for the agent."),
    agent: Path = typer.Option(Path("agents/example/agent.yaml"), "--agent", "-a"),
) -> None:
    """Run one agent turn."""

    settings = RuntimeSettings()
    config = AgentConfig.from_yaml(agent, settings=settings)
    result = asyncio.run(AgentRunner(config, settings=settings).run(prompt))
    console.print(result.final)


@app.command()
def list_extensions() -> None:
    """List built-in tools and skills."""

    console.print("Tools:")
    for name in default_tool_registry().names():
        console.print(f"- {name}")
    console.print("- schedule_task (agent-scoped)")
    console.print("- filesystem (agent-scoped)")
    console.print("\nSkills:")
    for name in default_skill_registry().names():
        console.print(f"- {name}")
    console.print("\nGuardrails:")
    for name in default_guardrail_registry().names():
        console.print(f"- {name}")
    console.print("\nChannels:")
    for name in default_channel_registry().names():
        console.print(f"- {name}")
    console.print("\nCache stores:")
    for name in default_cache_registry().names():
        console.print(f"- {name}")
    console.print("\nMemory stores:")
    for name in default_memory_registry().names():
        console.print(f"- {name}")
    console.print("\nSession stores:")
    for name in default_session_registry().names():
        console.print(f"- {name}")
    console.print("\nAgent templates:")
    for name in default_template_registry().names():
        console.print(f"- {name}")
    console.print("\nScheduler stores:")
    for name in default_scheduler_registry().names():
        console.print(f"- {name}")


@app.command()
def serve(
    agent: Path = typer.Option(Path("agents/example/agent.yaml"), "--agent", "-a"),
    channel: str | None = typer.Option(None, "--channel", "-c"),
) -> None:
    """Serve an agent through a UI/channel connector."""

    settings = RuntimeSettings()
    config = AgentConfig.from_yaml(agent, settings=settings)
    channel_id = channel or settings.default_channel
    if channel_id not in config.channels:
        raise typer.BadParameter(
            f"channel '{channel_id}' is not enabled for agent '{config.name}'"
        )
    runtime = AgentRuntime(config, settings=settings)
    try:
        selected = default_channel_registry().create(channel_id, settings)
    except (KeyError, RuntimeError, ValueError) as exc:
        raise typer.BadParameter(str(exc)) from exc
    asyncio.run(runtime.serve_with_scheduler(selected))


@app.command()
def doctor(
    agent: Path = typer.Option(Path("agents/example/agent.yaml"), "--agent", "-a"),
) -> None:
    """Validate agent configuration and runtime prerequisites."""

    settings = RuntimeSettings()
    config = AgentConfig.from_yaml(agent, settings=settings)
    report = run_doctor(config, settings)
    if not report.issues:
        console.print("OK: no issues found")
        return
    for issue in report.issues:
        label = "ERROR" if issue.severity == DoctorSeverity.ERROR else "WARN"
        console.print(f"{label} {issue.code}: {issue.message}")
    if not report.ok:
        raise typer.Exit(code=1)


@app.command("eval")
def eval_command(
    agent: Path = typer.Option(Path("agents/example/agent.yaml"), "--agent", "-a"),
    cases: Path = typer.Option(Path("agents/example/evals/smoke.yaml"), "--cases", "-c"),
) -> None:
    """Run eval cases against an agent."""

    settings = RuntimeSettings()
    config = AgentConfig.from_yaml(agent, settings=settings)
    runner = AgentRunner(config, settings=settings)
    eval_runner = EvalRunner(runner)
    summary = asyncio.run(eval_runner.run_cases(EvalRunner.load_cases(cases)))
    for report in summary.reports:
        status = "PASS" if report.passed else "FAIL"
        console.print(f"{status} {report.case_id}")
        for failure in report.failures:
            console.print(f"  - {failure}")
    console.print(f"\nPassed: {summary.passed}; Failed: {summary.failed}")
    if not summary.ok:
        raise typer.Exit(code=1)


@app.command("new-agent")
def new_agent(
    name: str = typer.Argument(..., help="New agent directory name."),
    output_dir: Path = typer.Option(Path("agents"), "--output-dir", "-o"),
    template: str = typer.Option("basic", "--template", "-t"),
    model: str = typer.Option("openai/gpt-4o-mini", "--model", "-m"),
    force: bool = typer.Option(False, "--force", help="Overwrite existing template files."),
) -> None:
    """Create a new agent from a template."""

    try:
        root = default_template_registry().create(
            name=name,
            output_dir=output_dir,
            template_id=template,
            model=model,
            force=force,
        )
    except (ValueError, FileExistsError) as exc:
        raise typer.BadParameter(str(exc)) from exc
    console.print(f"Created agent template at {root}")
    console.print(f"Run: uv run harness-agent eval --agent {root / 'agent.yaml'} --cases {root / 'evals' / 'smoke.yaml'}")


@tasks_app.command("list")
def list_tasks(
    status: str | None = typer.Option(None, "--status"),
) -> None:
    """List scheduled tasks."""

    settings = RuntimeSettings()
    store = default_scheduler_registry().create("local_json", settings)
    parsed_status = TaskStatus(status) if status else None
    tasks = asyncio.run(store.list(status=parsed_status))
    for task in tasks:
        console.print(
            f"{task.id} {task.status.value} {task.run_at.isoformat()} agent={task.agent} session={task.session_id}"
        )
        console.print(f"  {task.prompt}")
        if task.result:
            console.print(f"  result: {task.result}")
        if task.error:
            console.print(f"  error: {task.error}")


@tasks_app.command("run-due")
def run_due_tasks(
    agent: Path = typer.Option(Path("agents/example/agent.yaml"), "--agent", "-a"),
) -> None:
    """Run due scheduled tasks for an agent."""

    from harness_agent.scheduler.runner import ScheduledTaskRunner

    settings = RuntimeSettings()
    config = AgentConfig.from_yaml(agent, settings=settings)
    store = default_scheduler_registry().create(config.scheduler, settings)
    completed = asyncio.run(ScheduledTaskRunner(store, config).run_due())
    console.print(f"Completed scheduled tasks: {completed}")
