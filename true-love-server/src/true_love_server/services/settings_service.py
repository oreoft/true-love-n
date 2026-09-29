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
LIST = "list"

DEFINITIONS: dict[str, dict[str, str]] = {
    "reply_to": {
        "label": "本机回调地址",
        "type": TEXT,
        "hint": "AI 访问这台 server 用的地址，如 http://机器名:8088。"
                "多台 server 共用 AI 时必须填；不填时 AI 从它配置里的默认 server 回复",
    },
    "moyu_groups": {
        "label": "每日摸鱼推送的群",
        "type": LIST,
        "hint": "每天 09:05（北京时间）推送",
    },
    "usa_moyu_groups": {
        "label": "美国摸鱼推送的群",
        "type": LIST,
        "hint": "每天 08:00（美中时间）推送",
    },
}

# 配置文件 auto_notice 里的旧名字 → 设置项
_LEGACY_GROUPS = {
    "notice_moyu_schedule": "moyu_groups",
    "notice_usa_moyu_schedule": "usa_moyu_groups",
}


def _definition(key: str) -> dict[str, str]:
    if key not in DEFINITIONS:
        raise ValueError(f"未知的设置项: {key}")
    return DEFINITIONS[key]


def _clean(key: str, value: Any) -> Any:
    """校验并整理要保存的值，不合法时抛 ValueError"""
    definition = _definition(key)
    if definition["type"] == LIST:
        if not isinstance(value, list):
            raise ValueError(f"{definition['label']}必须是列表")
        names = [str(item).strip() for item in value]
        return list(dict.fromkeys(name for name in names if name))

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
    """读取设置，没设置过时文本为空串、列表为空列表"""
    definition = _definition(key)
    value = _read(key)
    if value is None:
        return [] if definition["type"] == LIST else ""
    return value


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


def import_from_config(auto_notice: Optional[dict]) -> None:
    """
    把配置文件里原有的推送群搬进数据库

    只搬数据库里还没有的设置项，所以后台改过的值不会被下一次启动覆盖。
    配置文件里的旧条目清理掉之后，这里什么都不做。
    """
    for legacy_key, key in _LEGACY_GROUPS.items():
        groups = (auto_notice or {}).get(legacy_key)
        if not groups or _read(key) is not None:
            continue
        update(key, list(groups))
        LOG.info("setting [%s] imported from config auto_notice.%s", key, legacy_key)
