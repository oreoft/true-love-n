# llm_bootstrap.py
import logging

from true_love_ai.core.config import get_config
from true_love_ai.core.model_registry import get_model_registry

LOG = logging.getLogger(__name__)


def init_llm():
    config = get_config()
    get_model_registry().load(config)

    # 提前实例化客户端，config 错误在启动时暴露
    from true_love_ai.llm.router import get_openai_client
    get_openai_client()
    LOG.info("OpenAI client 初始化完成")
