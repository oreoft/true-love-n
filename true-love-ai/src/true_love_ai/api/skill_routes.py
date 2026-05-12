# -*- coding: utf-8 -*-
"""
Skill Routes - 动态技能管理接口

供 Server Admin 调用，管理 DynamicSkill 数据。
所有端点使用 POST，token 放在请求体中。
"""
import logging

from fastapi import APIRouter

from true_love_ai.api.deps import verify_token
from true_love_ai.memory import dynamic_skill_service as _ss
from true_love_ai.models.response import APIResponse

LOG = logging.getLogger("SkillRoutes")

skill_router = APIRouter(prefix="/skill")


@skill_router.post("/list")
async def list_skills(request: dict):
    if not verify_token(request.get("token", "")):
        return APIResponse.token_error()
    data = _ss.list_skills()
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

    try:
        result = _ss.save_skill(skill_id, name, description, command, parameters, creator)
    except (ValueError, RuntimeError) as e:
        return APIResponse.error(str(e))

    LOG.info("skill/save: id=%s", result["id"])
    return APIResponse.success({"id": result["id"]})


@skill_router.post("/delete")
async def delete_skill(request: dict):
    if not verify_token(request.get("token", "")):
        return APIResponse.token_error()
    skill_id = request.get("id", "").strip()
    try:
        result = _ss.delete_skill(skill_id)
    except ValueError as e:
        return APIResponse.error(str(e))
    LOG.info("skill/delete: id=%s", skill_id)
    return APIResponse.success(result)
