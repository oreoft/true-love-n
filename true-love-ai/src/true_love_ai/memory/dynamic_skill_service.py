# -*- coding: utf-8 -*-
"""
Dynamic Skill Service - 动态技能业务逻辑层

dynamic_skill_manage.py（AI function-call）和 skill_routes.py（Admin API）
共用此模块，统一校验规则和数据操作。
"""
import json
import logging
import re

from true_love_ai.core.db_engine import SessionLocal
from true_love_ai.memory.dynamic_skill_repository import DynamicSkillRepository

LOG = logging.getLogger("DynamicSkillService")

# ID 格式：小写英文+数字+下划线，长度 2-63
SKILL_ID_RE = re.compile(r'^[a-z0-9][a-z0-9_]{1,62}$')

# 保存时拦截的危险命令模式
_BLOCKED_CMD = re.compile(
    r'\brm\s+-[rf]'
    r'|\brmdir\b'
    r'|\bdd\s+if='
    r'|\bsudo\b'
    r'|\bsu\s'
    r'|\bchmod\b'
    r'|\bchown\b'
    r'|\bpasswd\b'
    r'|\bshutdown\b'
    r'|\breboot\b'
    r'|\bpoweroff\b'
    r'|\|\s*(sh|bash|zsh|fish)\b'
    r'|>\s*/',
    re.IGNORECASE,
)


def validate_skill_id(skill_id: str) -> str | None:
    """检查 ID 格式，返回错误消息；None 表示通过。"""
    if not SKILL_ID_RE.match(skill_id):
        return "id 格式不合法，必须是小写英文+数字+下划线，长度 2-63"
    return None


def validate_command(command: str) -> str | None:
    """检查命令安全性，返回拦截原因；None 表示通过。"""
    if _BLOCKED_CMD.search(command):
        return "命令包含危险操作（rm -rf / sudo / 写入系统路径等），已拒绝保存"
    if len(command) > 2000:
        return "命令长度超过 2000 字符限制"
    return None


def normalize_parameters(parameters) -> str | None:
    """将 parameters 规范化为 JSON 字符串或 None；格式非法时抛 ValueError。"""
    if isinstance(parameters, dict):
        return json.dumps(parameters, ensure_ascii=False) if parameters else None
    if isinstance(parameters, str) and parameters.strip():
        try:
            json.loads(parameters)
            return parameters.strip()
        except json.JSONDecodeError:
            raise ValueError("parameters 必须是合法的 JSON 格式")
    return None


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


def save_skill(skill_id: str, name: str, description: str, command: str,
               parameters, creator: str = "admin") -> dict:
    """验证并保存技能（upsert），返回 {"id": skill_id, "is_update": bool}。

    校验失败抛 ValueError，保存失败抛 RuntimeError。
    """
    if not skill_id or not name or not description or not command:
        raise ValueError("id、name、description、command 不能为空")

    id_err = validate_skill_id(skill_id)
    if id_err:
        raise ValueError(id_err)

    cmd_err = validate_command(command)
    if cmd_err:
        raise ValueError(cmd_err)

    params_json = normalize_parameters(parameters)

    with SessionLocal() as db:
        repo = DynamicSkillRepository(db)
        existing = repo.get(skill_id)
        ok = repo.save(
            id=skill_id,
            name=name,
            description=description,
            command=command,
            parameters=params_json,
            creator=creator,
        )

    if not ok:
        raise RuntimeError("保存失败，请稍后重试")

    LOG.info("skill/save: id=%s is_update=%s", skill_id, existing is not None)
    return {"id": skill_id, "is_update": existing is not None}


def delete_skill(skill_id: str) -> dict:
    """删除技能，返回 {"id": skill_id}；未找到时抛 ValueError。"""
    if not skill_id:
        raise ValueError("id 不能为空")
    with SessionLocal() as db:
        repo = DynamicSkillRepository(db)
        ok = repo.delete(skill_id)
    if not ok:
        raise ValueError(f"未找到技能 '{skill_id}'")
    LOG.info("skill/delete: id=%s", skill_id)
    return {"id": skill_id}


def list_skills() -> list[dict]:
    """返回所有技能的字典列表，按 id 排序。"""
    with SessionLocal() as db:
        repo = DynamicSkillRepository(db)
        skills = repo.list_all()
        return [_to_dict(s) for s in skills]


def get_skill(skill_id: str) -> dict | None:
    """按 ID 查询技能，返回字典；不存在返回 None。"""
    with SessionLocal() as db:
        repo = DynamicSkillRepository(db)
        skill = repo.get(skill_id)
        return _to_dict(skill) if skill else None


def increment_skill_usage(skill_id: str) -> None:
    """递增技能使用计数（失败静默）。"""
    with SessionLocal() as db:
        repo = DynamicSkillRepository(db)
        repo.increment_usage(skill_id)
