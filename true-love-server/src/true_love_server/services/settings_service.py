# -*- coding: utf-8 -*-
"""
Settings Service - 后台可改的设置

每个机器人各不相同、又需要随时调整的设置放在这台 server 的数据库里，
由管理后台修改，改完立即生效。所有机器共用的密钥和地址仍然在配置文件里。
"""

import json
import logging
from datetime import datetime
from typing import Any, Optional

from ..core.db_engine import SessionLocal
from ..models.setting import Setting

LOG = logging.getLogger("SettingsService")

TEXT = "text"

DEFINITIONS: dict[str, dict[str, str]] = {
    "reply_to": {
        "label": "本机回调地址",
        "type": TEXT,
        "hint": "AI 访问这台 server 用的地址，如 http://机器名:8088。"
                "多台 server 共用 AI 时必须填；不填时 AI 从它配置里的默认 server 回复",
    },
}


def _definition(key: str) -> dict[str, str]:
    if key not in DEFINITIONS:
        raise ValueError(f"未知的设置项: {key}")
    return DEFINITIONS[key]


def _clean(key: str, value: Any) -> Any:
    """校验并整理要保存的值，不合法时抛 ValueError"""
    definition = _definition(key)
    if not isinstance(value, str):
        raise ValueError(f"{definition['label']}必须是文本")
    value = value.strip().rstrip("/")
    if value and not value.startswith(("http://", "https://")):
        raise ValueError(f"{definition['label']}必须以 http:// 或 https:// 开头")
    return value


def _read(key: str) -> Optional[Any]:
    """读出已保存的值，从没保存过时返回 None"""
    with SessionLocal() as db:
        row = db.get(Setting, key)
        return None if row is None else json.loads(row.value)


def get(key: str) -> Any:
    """读取设置，没设置过时为空串"""
    _definition(key)
    value = _read(key)
    return "" if value is None else value


def update(key: str, value: Any) -> Any:
    """保存设置，返回整理后的值；不合法时抛 ValueError"""
    value = _clean(key, value)
    with SessionLocal() as db:
        row = db.get(Setting, key)
        if row is None:
            row = Setting(key=key)
            db.add(row)
        row.value = json.dumps(value, ensure_ascii=False)
        row.updated_at = datetime.now()
        db.commit()
    LOG.info("setting [%s] updated: %s", key, value)
    return value


def list_all() -> list[dict[str, Any]]:
    """全部设置项及当前值，供管理后台展示"""
    return [{"key": key, **definition, "value": get(key)} for key, definition in DEFINITIONS.items()]

