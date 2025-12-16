# context_vars.py
import contextvars

# 定义上下文变量
local_msg_id = contextvars.ContextVar('msg_id')
