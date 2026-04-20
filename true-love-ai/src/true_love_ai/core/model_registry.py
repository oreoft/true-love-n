# -*- coding: utf-8 -*-
"""
模型注册表
统一管理所有 LiteLLM 模型字符串，支持 override 文件持久化覆盖。

两层加载：
  1. config.yaml  → 基准值（裸模型名，由 registry 加前缀）
  2. models_override.json → 运行时覆盖（存完整 LiteLLM 字符串）
"""
import json
import logging
from pathlib import Path
from typing import Optional

LOG = logging.getLogger(__name__)

OVERRIDE_FILE = Path("models_override.json")

# 前缀规则：category.key → 前缀模板
_PREFIX_RULES: dict[tuple[str, str], str] = {
    ("chat",     "openai"):   "openai/{}",
    ("chat",     "claude"):   "openai/claude/{}",
    ("chat",     "gemini"):   "openai/gemini/{}",
    ("chat",     "deepseek"): "openai/deepseek/{}",
    ("compress", "openai"):   "openai/{}",
    ("vision",   "openai"):   "openai/{}",
    ("image",    "openai"):   "openai/{}",
    ("image",    "gemini"):   "openai/gemini/{}",
    ("video",    "openai"):   "openai/{}",
    ("video",    "gemini"):   "gemini/{}",   # 直连，不走代理
}


class ModelRegistry:

    def __init__(self):
        self._models: dict[str, dict[str, str]] = {}

    def load(self, config) -> None:
        """从 LLMConfig 构建基准，再叠加 override 文件"""
        llm = config.llm
        if not llm:
            return

        base: dict[str, dict[str, str]] = {
            "chat": {
                "openai":   _apply("chat",     "openai",   llm.chat.openai),
                "claude":   _apply("chat",     "claude",   llm.chat.claude),
                "gemini":   _apply("chat",     "gemini",   llm.chat.gemini),
                "deepseek": _apply("chat",     "deepseek", llm.chat.deepseek),
            },
            "compress": {
                "openai":   _apply("compress", "openai",   llm.compress.openai),
            },
            "vision": {
                "openai":   _apply("vision",   "openai",   llm.vision.openai),
            },
            "image": {
                "openai":   _apply("image",    "openai",   llm.image.openai),
                "gemini":   _apply("image",    "gemini",   llm.image.gemini),
            },
            "video": {
                "openai":   _apply("video",    "openai",   llm.video.openai),
                "gemini":   _apply("video",    "gemini",   llm.video.gemini),
            },
        }

        # 叠加 override
        if OVERRIDE_FILE.exists():
            try:
                overrides = json.loads(OVERRIDE_FILE.read_text(encoding="utf-8"))
                for cat, models in overrides.items():
                    for key, value in models.items():
                        base.setdefault(cat, {})[key] = value
                LOG.info("已加载模型 override: %s", OVERRIDE_FILE)
            except Exception as e:
                LOG.error("加载 models_override.json 失败: %s", e)

        self._models = base
        LOG.info("ModelRegistry 加载完成: %d 个类别", len(self._models))

    def get(self, category: str, key: str) -> str:
        try:
            return self._models[category][key]
        except KeyError:
            raise KeyError(f"模型未找到: {category}.{key}，当前配置: {self._models}")

    def set(self, category: str, key: str, value: str) -> None:
        """动态修改模型，持久化到 override 文件"""
        self._models.setdefault(category, {})[key] = value
        self._save_override()
        LOG.info("模型已更新: %s.%s = %s", category, key, value)

    def reload(self, config) -> None:
        self.load(config)

    def all(self) -> dict[str, dict[str, str]]:
        return {cat: dict(models) for cat, models in self._models.items()}

    def _save_override(self) -> None:
        """读取现有 override 文件，合并当前内存值后写回"""
        existing: dict = {}
        if OVERRIDE_FILE.exists():
            try:
                existing = json.loads(OVERRIDE_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass

        # 只把和 base 不同的值写进 override（简化：直接写全量内存）
        try:
            OVERRIDE_FILE.write_text(
                json.dumps(self._models, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            LOG.error("写入 models_override.json 失败: %s", e)


def _apply(category: str, key: str, bare_name: str) -> str:
    """根据前缀规则把裸模型名转成完整 LiteLLM 字符串"""
    rule = _PREFIX_RULES.get((category, key))
    if rule:
        return rule.format(bare_name)
    return bare_name


_registry: Optional[ModelRegistry] = None


def get_model_registry() -> ModelRegistry:
    global _registry
    if _registry is None:
        _registry = ModelRegistry()
    return _registry
