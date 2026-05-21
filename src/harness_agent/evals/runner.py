from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from harness_agent.agent import AgentRunner


class EvalCase(BaseModel):
    id: str
    input: str
    expect_contains: list[str] = Field(default_factory=list)
    expect_not_contains: list[str] = Field(default_factory=list)
    expect_guardrail_block: bool = False
    max_iterations: int | None = None


@dataclass(frozen=True)
class EvalReport:
    case_id: str
    passed: bool
    failures: list[str] = field(default_factory=list)
    output: str = ""


@dataclass(frozen=True)
class EvalSummary:
    reports: list[EvalReport]

    @property
    def passed(self) -> int:
        return sum(1 for report in self.reports if report.passed)

    @property
    def failed(self) -> int:
        return len(self.reports) - self.passed

    @property
    def ok(self) -> bool:
        return self.failed == 0


class EvalRunner:
    def __init__(self, agent_runner: AgentRunner) -> None:
        self.agent_runner = agent_runner

    async def run_cases(self, cases: list[EvalCase]) -> EvalSummary:
        reports = []
        for case in cases:
            result = await self.agent_runner.run(case.input, session_id=f"eval:{case.id}")
            reports.append(self._check(case, result.final, result.iterations))
        return EvalSummary(reports=reports)

    @staticmethod
    def load_cases(path: str | Path) -> list[EvalCase]:
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        return [EvalCase.model_validate(item) for item in raw.get("cases", [])]

    @staticmethod
    def _check(case: EvalCase, output: str, iterations: int) -> EvalReport:
        failures: list[str] = []
        lowered = output.casefold()
        for expected in case.expect_contains:
            if expected.casefold() not in lowered:
                failures.append(f"missing expected text: {expected}")
        for forbidden in case.expect_not_contains:
            if forbidden.casefold() in lowered:
                failures.append(f"found forbidden text: {forbidden}")
        if case.expect_guardrail_block and "request blocked by guardrail" not in lowered:
            failures.append("expected guardrail block")
        if case.max_iterations is not None and iterations > case.max_iterations:
            failures.append(f"iterations {iterations} exceeded {case.max_iterations}")
        return EvalReport(case_id=case.id, passed=not failures, failures=failures, output=output)

