# llm_bootstrap.py
import litellm
from true_love_ai.core.config import get_config
from true_love_ai.core.model_registry import get_model_registry


def init_litellm():
    config = get_config()
    litellm.modify_params = True
    litellm.drop_params = True
    litellm.api_key = config.platform_key.litellm_api_key
    litellm.api_base = config.platform_key.litellm_base_url

    registry = get_model_registry()
    registry.load(config)
