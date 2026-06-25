from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

# Path to skills directory relative to the backend package root
_SKILLS_DIR = Path(__file__).resolve().parent.parent.parent / "skills"


@dataclass
class Skill:
    name: str
    group: str
    display_name: str
    description: str
    instruction: str


@dataclass
class SkillGroup:
    name: str
    skills: list[Skill] = field(default_factory=list)


class SkillRegistry:
    """Loads and manages skills from YAML files organized by directory groups."""

    def __init__(self):
        self._skills: dict[str, Skill] = {}
        self._groups: dict[str, SkillGroup] = {}
        self._loaded = False

    def load(self, skills_dir: Path | None = None) -> None:
        """Load all skill YAML files from the skills directory."""
        if self._loaded:
            return

        directory = skills_dir or _SKILLS_DIR
        logger.info("Loading skills from %s", directory)

        if not directory.is_dir():
            logger.warning("Skills directory not found: %s", directory)
            self._loaded = True
            return

        loaded_count = 0
        # Iterate group directories (e.g., sql/, ontology/)
        for group_dir in sorted(directory.iterdir()):
            if not group_dir.is_dir():
                continue

            group_name = group_dir.name
            group = SkillGroup(name=group_name)

            for yaml_file in sorted(group_dir.glob("*.yaml")):
                try:
                    with open(yaml_file, "r", encoding="utf-8") as f:
                        data = yaml.safe_load(f)

                    if not data or "name" not in data:
                        logger.warning("Invalid skill file: %s", yaml_file)
                        continue

                    skill = Skill(
                        name=data["name"],
                        group=data.get("group", group_name),
                        display_name=data.get("display_name", data["name"]),
                        description=data.get("description", ""),
                        instruction=data.get("instruction", ""),
                    )
                    self._skills[skill.name] = skill
                    group.skills.append(skill)
                    loaded_count += 1
                except Exception as e:
                    logger.warning("Failed to load skill %s: %s", yaml_file, e)

            if group.skills:
                self._groups[group.name] = group

        self._loaded = True
        logger.info("Loaded %d skills in %d groups", loaded_count, len(self._groups))

    def get_skill(self, name: str) -> Skill | None:
        return self._skills.get(name)

    def list_skills(self, group: str | None = None) -> list[Skill]:
        if group:
            g = self._groups.get(group)
            return list(g.skills) if g else []
        return list(self._skills.values())

    def list_groups(self) -> list[SkillGroup]:
        return list(self._groups.values())

    def list_skill_summaries(self, group: str | None = None) -> list[dict[str, Any]]:
        """Return lightweight summaries for the agent's context (no full instructions)."""
        skills = self.list_skills(group)
        return [
            {
                "name": s.name,
                "group": s.group,
                "display_name": s.display_name,
                "description": s.description,
            }
            for s in skills
        ]


# Global singleton
skill_registry = SkillRegistry()
