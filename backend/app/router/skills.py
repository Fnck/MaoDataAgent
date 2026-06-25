from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_user
from app.service.skills import skill_registry

router = APIRouter(prefix="/api/skills", tags=["skills"])


@router.get("")
async def list_skills(
    current_user: dict = Depends(get_current_user),
):
    """Return all skills with groups."""
    groups = []
    for g in skill_registry.list_groups():
        groups.append({
            "name": g.name,
            "skills": [
                {
                    "name": s.name,
                    "display_name": s.display_name,
                    "description": s.description,
                }
                for s in g.skills
            ],
        })
    return {"groups": groups}


@router.get("/{name}")
async def load_skill(
    name: str,
    current_user: dict = Depends(get_current_user),
):
    """Load a single skill's full details including instructions."""
    skill = skill_registry.get_skill(name)
    if skill is None:
        raise HTTPException(status_code=404, detail=f"Skill not found: {name}")
    return {
        "name": skill.name,
        "group": skill.group,
        "display_name": skill.display_name,
        "description": skill.description,
        "instruction": skill.instruction,
    }
