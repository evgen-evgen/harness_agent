from __future__ import annotations

from harness_agent.skills.base import Skill


class SkillRegistry:
    def __init__(self) -> None:
        self._skills: dict[str, Skill] = {}

    def register(self, skill: Skill) -> None:
        self._skills[skill.id] = skill

    def get(self, skill_id: str) -> Skill:
        try:
            return self._skills[skill_id]
        except KeyError as exc:
            raise KeyError(f"unknown skill: {skill_id}") from exc

    def select(self, ids: list[str]) -> list[Skill]:
        return [self.get(skill_id) for skill_id in ids]

    def names(self) -> list[str]:
        return sorted(self._skills)


def default_skill_registry() -> SkillRegistry:
    registry = SkillRegistry()
    registry.register(
        Skill(
            id="web_research",
            tools=["web_search"],
            instructions=(
                "When the user asks for current or externally verifiable facts, use web_search. "
                "Cite source URLs in the answer. Distinguish confirmed facts from inference."
            ),
        )
    )
    registry.register(
        Skill(
            id="concise_operator",
            instructions=(
                "Be direct. Prefer concrete next actions and short explanations over broad theory."
            ),
        )
    )
    return registry

