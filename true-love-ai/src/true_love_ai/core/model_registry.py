# -*- coding: utf-8 -*-
"""
模型注册表
统一管理所有 LiteLLM 模型字符串，支持 override 文件持久化覆盖。

配置直接写完整 LiteLLM 字符串（如 openai/gpt-5.4），不再做前缀转换。
"""
import json
import logging
from pathlib import Path
from typing import Optional

LOG = logging.getLogger(__name__)

OVERRIDE_FILE = Path("models_override.json")


class ModelRegistry:

    def __init__(self):
        # {category: {key: model_string}}
        # 单一模型类别只有 "default" key；支持降级的有 "default" + "fallback"
        self._models: dict[str, dict[str, str]] = {}

    def load(self, config) -> None:
        llm = config.llm
        if not llm:
            return

        def _entry(m) -> dict[str, str]:
            e = {"default": m.default}
            if m.fallback:
                e["fallback"] = m.fallback
            return e

        self._models = {
            "chat":     _entry(llm.chat),
            "compress": _entry(llm.compress),
            "vision":   _entry(llm.vision),
            "image":    _entry(llm.image),
            "video":    _entry(llm.video),
        }

        if OVERRIDE_FILE.exists():
            try:
                overrides = json.loads(OVERRIDE_FILE.read_text(encoding="utf-8"))
                for cat, keys in overrides.items():
                    for key, value in keys.items():
                        self._models.setdefault(cat, {})[key] = value
                LOG.info("已加载模型 override: %s", OVERRIDE_FILE)
            except Exception as e:
                LOG.error("加载 models_override.json 失败: %s", e)

        LOG.info("ModelRegistry 加载完成: %d 个类别", len(self._models))

    def get(self, category: str, key: str = "default") -> str:
        try:
            return self._models[category][key]
        except KeyError:
            raise KeyError(f"模型未找到: {category}.{key}，当前配置: {self._models}")

    def set(self, category: str, key: str, value: str) -> None:
        self._models.setdefault(category, {})[key] = value
        self._save_override()
        LOG.info("模型已更新: %s.%s = %s", category, key, value)

    def reload(self, config) -> None:
        self.load(config)

    def all(self) -> dict[str, dict[str, str]]:
        return {cat: dict(keys) for cat, keys in self._models.items()}

    def _save_override(self) -> None:
        try:
            OVERRIDE_FILE.write_text(
                json.dumps(self._models, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            LOG.error("写入 models_override.json 失败: %s", e)


_registry: Optional[ModelRegistry] = None


def get_model_registry() -> ModelRegistry:
    global _registry
    if _registry is None:
        _registry = ModelRegistry()
    return _registry
