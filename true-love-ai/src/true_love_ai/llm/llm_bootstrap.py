# llm_bootstrap.py
import litellm
from true_love_ai.core.config import get_config

def init_litellm():
    litellm.modify_params = True
    litellm.drop_params = True
    litellm.api_key = get_config().platform_key.litellm_api_key
    litellm.api_base = get_config().platform_key.litellm_base_url