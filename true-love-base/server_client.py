import json
import time

import requests

from configuration import Config
from wcf_utils import *
from wcf_utils import WcfUtils

config = Config()

# 熔断器状态
circuit_breaker = {
    "fail_count": 0,
    "last_fail_time": 0
}

host = "http://localhost:8088"
text_url = f"{host}/get-chat"
LOG = logging.getLogger("ServerClient")


def get_chat(req: WxMsg):
    try:
        img_path = ""
        # 如果引用类型并且里面有图片, 把图片下载然后base64传过去
        if req.type == 49:
            chat = WcfUtils().get_refer_content(req)
            if chat.type == ContentType.image:
                img_path = chat.content
                LOG.info(f"文件已下载到: {img_path}")
            LOG.info(f"refer type but files skip, type:{chat.type}, path:{chat.content}")
        # 构建传输对象
        payload = json.dumps({
            "token": config.http_token,
            "_is_self": req._is_self,
            "_is_group": req._is_group,
            "type": req.type,
            "id": req.id,
            "ts": req.ts,
            "sign": req.sign,
            "xml": req.xml,
            "sender": req.sender,
            "roomid": req.roomid,
            "content": req.content,
            "thumb": req.thumb,
            "extra": req.extra,
            "img_path": img_path
        })
        headers = {
            'Content-Type': 'application/json'
        }

        # 暂不检查熔断器, 只是做文案分流
        # current_time = int(time.time())
        # if circuit_breaker["fail_count"] >= 3 and current_time - circuit_breaker["last_fail_time"] < 60:
        #     return "正在部署，请稍后重试"

        # 发起请求
        start_time = time.time()
        LOG.info("开始请求server获取内容, req:[%s]", payload)
        response = requests.request("POST", text_url, headers=headers, data=payload, timeout=(2, 60))
        LOG.info("接收到server返回值, cost:[%.0fms], res:[%s]", (time.time() - start_time) * 1000, response.json())
        # 检查HTTP响应状态
        response.raise_for_status()

        # 解析响应
        return_data = response.json()
        if return_data.get("code") == 0:
            # 成功返回 重置熔断器状态
            circuit_breaker["fail_count"] = 0
            circuit_breaker["last_fail_time"] = 0
            return return_data.get("data")
        else:
            LOG.error("get_chat 返回值返回异常: %s", return_data)
            return get_error_msg()

    except Exception as e:
        LOG.error("get_chat 发生错误", e)
        return get_error_msg()


def get_error_msg():
    # 更新熔断器状态
    circuit_breaker["fail_count"] += 1
    circuit_breaker["last_fail_time"] = int(time.time())

    if circuit_breaker["fail_count"] < 3:
        return "啊哦~，可能内容太长搬运超时，再试试捏"

    return "啊哦~, 服务正在重新调整，请稍后重试再试"
