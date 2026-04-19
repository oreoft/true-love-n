# -*- coding: utf-8 -*-
"""微信扫码连通道 Skill（通过 Nexu 生成二维码，后台完成绑定）"""
import asyncio
import json
import logging

from true_love_ai.agent.skill_registry import register_skill

LOG = logging.getLogger("WechatQrSkill")


@register_skill({
    "type": "function",
    "function": {
        "name": "wechat_qr_connect",
        "description": (
            "生成微信扫码登录二维码，用于将微信账号接入系统通道。"
            "当用户说[领养真爱粉]等时使用。"
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
})
async def wechat_qr_connect(params: dict, ctx: dict) -> str:
    from true_love_ai.core.config import get_config
    import httpx

    cfg = get_config()
    nexu = cfg.nexu
    if not nexu.base_url:
        return "Nexu 服务未配置，无法生成二维码"

    url = f"{nexu.base_url}/api/v1/channels/wechat/qr-start"
    headers = {"Authorization": f"Bearer {nexu.token}"} if nexu.token else {}

    qr_data = None
    last_error = None
    for attempt in range(1, 4):
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                res = await client.post(url, headers=headers)
                res.raise_for_status()
                qr_data = res.json()
                LOG.info("Nexu qr-start 响应: %s", qr_data)
                break
        except Exception as e:
            last_error = e
            LOG.warning("调用 Nexu qr-start 失败 (第%d次): %s", attempt, e)

    if qr_data is None:
        LOG.error("Nexu qr-start 重试3次均失败: %s", last_error)
        return "抱歉捏，openclaw 服务暂时不可用，请稍后再试吧~"

    session_key = qr_data.get("sessionKey")
    if session_key:
        asyncio.create_task(_wait_and_bind(session_key, nexu.base_url, headers))

    # 发送二维码图片
    qr_data_url = qr_data.get("qrDataUrl", "")
    if qr_data_url and "," in qr_data_url:
        receiver = ctx.get("receiver", "")
        if receiver:
            try:
                import base64
                import uuid
                from true_love_ai.agent.server_client import send_file

                from true_love_ai.services.image_service import GEN_IMG_DIR
                img_b64 = qr_data_url.split(",", 1)[1]
                file_id = uuid.uuid4().hex
                (GEN_IMG_DIR / f"{file_id}.jpg").write_bytes(base64.b64decode(img_b64))
                await send_file(receiver, file_id, file_type="image")
                return "好的！二维码已发送，请用微信扫描完成领养哦~"
            except Exception as e:
                LOG.error("发送二维码图片失败: %s", e)

    return qr_data.get("message", "请扫描二维码完成领养~")


async def _wait_and_bind(session_key: str, base_url: str, headers: dict) -> None:
    """后台轮询扫码结果，完成最终绑定（复用旧 ChatService 逻辑）"""
    import httpx

    wait_url = f"{base_url}/api/v1/channels/wechat/qr-wait"
    connect_url = f"{base_url}/api/v1/channels/wechat/connect"

    try:
        async with httpx.AsyncClient(timeout=600.0) as client:
            LOG.info("开始后台轮询 wechat-qr-wait, sessionKey=%s", session_key)
            wait_res = await client.post(wait_url, json={"sessionKey": session_key}, headers=headers)
            wait_res.raise_for_status()
            wait_data = wait_res.json()
            LOG.info("wechat-qr-wait 结果: %s", wait_data)

            if wait_data.get("connected") and wait_data.get("accountId"):
                account_id = wait_data["accountId"]
                LOG.info("扫码成功，绑定 accountId=%s", account_id)
                conn_res = await client.post(connect_url, json={"accountId": account_id}, headers=headers)
                conn_res.raise_for_status()
                LOG.info("微信通道绑定成功: %s", conn_res.json())
            else:
                LOG.warning("qr-wait 返回非预期结果或超时: %s", wait_data)
    except Exception as e:
        LOG.error("后台微信扫码绑定流程出错: %s", e)
