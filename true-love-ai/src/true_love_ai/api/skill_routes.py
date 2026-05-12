# -*- coding: utf-8 -*-
"""
Skill Routes - 动态技能管理接口

供 Server Admin 调用，管理 DynamicSkill 数据。
所有端点使用 POST，token 放在请求体中。
"""
import json
import logging
import re

from fastapi import APIRouter

from true_love_ai.api.deps import verify_token
from true_love_ai.core.db_engine import SessionLocal
from true_love_ai.memory.dynamic_skill_repository import DynamicSkillRepository
from true_love_ai.models.response import APIResponse

LOG = logging.getLogger("SkillRoutes")

skill_router = APIRouter(prefix="/skill")

_SKILL_ID_RE = re.compile(r'^[a-z0-9][a-z0-9_]{1,62}$')


def _to_dict(skill) -> dict:
    return {
        "id": skill.id,
        "name": skill.name,
        "description": skill.description,
        "command": skill.command,
        "parameters": skill.parameters,
        "creator": skill.creator,
        "usage_count": skill.usage_count,
        "last_used_at": skill.last_used_at.isoformat() if skill.last_used_at else None,
        "created_at": skill.created_at.isoformat() if skill.created_at else None,
    }


@skill_router.post("/list")
async def list_skills(request: dict):
    if not verify_token(request.get("token", "")):
        return APIResponse.token_error()
    with SessionLocal() as db:
        repo = DynamicSkillRepository(db)
        skills = repo.list_all()
    data = [_to_dict(s) for s in skills]
    LOG.info("skill/list: count=%d", len(data))
    return APIResponse.success({"skills": data, "total": len(data)})


@skill_router.post("/save")
async def save_skill(request: dict):
    if not verify_token(request.get("token", "")):
        return APIResponse.token_error()

    skill_id = request.get("id", "").strip()
    name = request.get("name", "").strip()
    description = request.get("description", "").strip()
    command = request.get("command", "").strip()
    parameters = request.get("parameters") or ""
    creator = request.get("creator", "admin").strip()

    if not skill_id or not name or not description or not command:
        return APIResponse.error("id、name、description、command 不能为空")
    if not _SKILL_ID_RE.match(skill_id):
        return APIResponse.error("id 格式不合法，必须是小写英文+数字+下划线，长度 2-63")

    if isinstance(parameters, dict):
        params_json = json.dumps(parameters, ensure_ascii=False) if parameters else None
    elif isinstance(parameters, str) and parameters.strip():
        try:
            json.loads(parameters)
            params_json = parameters.strip()
        except json.JSONDecodeError:
            return APIResponse.error("parameters 必须是合法的 JSON 格式")
    else:
        params_json = None

    with SessionLocal() as db:
        repo = DynamicSkillRepository(db)
        ok = repo.save(
            id=skill_id,
            name=name,
            description=description,
            command=command,
            parameters=params_json,
            creator=creator,
        )
    if not ok:
        return APIResponse.error("保存失败，请稍后重试")
    LOG.info("skill/save: id=%s", skill_id)
    return APIResponse.success({"id": skill_id})


@skill_router.post("/delete")
async def delete_skill(request: dict):
    if not verify_token(request.get("token", "")):
        return APIResponse.token_error()
    skill_id = request.get("id", "").strip()
    if not skill_id:
        return APIResponse.error("id 不能为空")
    with SessionLocal() as db:
        repo = DynamicSkillRepository(db)
        ok = repo.delete(skill_id)
    if not ok:
        return APIResponse.error(f"未找到技能 '{skill_id}'")
    LOG.info("skill/delete: id=%s", skill_id)
    return APIResponse.success({"id": skill_id})
