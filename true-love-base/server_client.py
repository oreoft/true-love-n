import base64
import json
import logging
import os
import time

import requests
from wcferry import WxMsg, Wcf

from configuration import Config

config = Config()

# 熔断器状态
circuit_breaker = {
    "fail_count": 0,
    "last_fail_time": 0
}

host = "http://localhost:8088"
text_url = f"{host}/get-chat"
LOG = logging.getLogger("ServerClient")


def get_chat(req: WxMsg, wcf: Wcf):
    try:
        base64_string = ""
        # 如果引用类型并且里面有图片, 把图片下载然后base64传过去
        if req.type == 49 and "<type>3</type>" in req.content:
            save_img_dir = os.path.dirname(os.path.abspath(__file__)) + '/save-img'
            print("req.id", req.id)
            print("req.extra", req.extra)
            print("save_img_dir", save_img_dir)
            base64_string = image_to_base64(wcf.download_image(id=req.id, extra=req.extra, dir=save_img_dir, timeout=5))
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
            "img_data": base64_string
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
        LOG.info("接收到server返回值, cost:[%.0fms], res:[%s]", (time.time() - start_time) * 1000, response)
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


def image_to_base64(image_path):
    """
    将图片文件转换为Base64编码的字符串。

    :param image_path: 图片文件的路径
    :return: Base64编码的字符串
    """
    with open(image_path, "rb") as image_file:
        # 读取文件内容
        encoded_string = base64.b64encode(image_file.read())
        return encoded_string.decode('utf-8')

def get_error_msg():
    # 更新熔断器状态
    circuit_breaker["fail_count"] += 1
    circuit_breaker["last_fail_time"] = int(time.time())

    if circuit_breaker["fail_count"] < 3:
        return "啊哦~，可能内容太长搬运超时，再试试捏"

    return "啊哦~, 服务正在重新调整，请稍后重试再试"


if __name__ == "__main__":
    while True:
        print(get_chat({}))
