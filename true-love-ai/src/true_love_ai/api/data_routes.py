# -*- coding: utf-8 -*-
"""
Data Routes - 数据查询接口

供 Server 侧定时 Jobs 调用，返回结构化数据（汇率、金价等）。
"""

import logging

from fastapi import APIRouter

from true_love_ai.api.deps import verify_token
from true_love_ai.models.response import APIResponse

LOG = logging.getLogger("DataRoutes")

data_router = APIRouter(prefix="/data")


@data_router.get("/currency")
async def get_currency(currency: str, token: str = ""):
    """
    查询汇率数据

    Query Parameters:
        - currency: 货币名称（美元/澳币/日元/USD/AUD/JPY）
        - token: 鉴权 token
    """
    if not verify_token(token):
        return APIResponse.token_error()

    from true_love_ai.agent.skills.currency_skill import currency_query
    result = await currency_query({"currency": currency}, {})
    return APIResponse.success({"text": result})


@data_router.get("/gold")
async def get_gold(token: str = ""):
    """
    查询黄金价格

    Query Parameters:
        - token: 鉴权 token
    """
    if not verify_token(token):
        return APIResponse.token_error()

    from true_love_ai.agent.skills.gold_skill import gold_price
    result = await gold_price({}, {})
    return APIResponse.success({"text": result})
