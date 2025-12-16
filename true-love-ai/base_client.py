import json
import logging
import time

import requests

from configuration import Config

config = Config()
host = config.BASE_SERVER["host"]
token = config.HTTP["token"][0]
LOG = logging.getLogger("BaseClient")


def send_text(send_receiver, at_receiver, content):
    payload = json.dumps({
        "token": token,
        "sendReceiver": send_receiver,
        "atReceiver": at_receiver,
        "content": content
    })
    headers = {
        'Content-Type': 'application/json'
    }
    try:
        start_time = time.time()
        LOG.info("开始请求base推送内容, req:[%s]", payload)
        res = requests.request("POST", host, headers=headers, data=payload, timeout=(2, 60))
        # 检查HTTP响应状态
        res.raise_for_status()
        LOG.info("请求成功, cost:[%.0fms], res:[%s]", (time.time() - start_time) * 1000, res.json())
    except Exception as e:
        LOG.info("send_text 失败", e)
    return ""


if __name__ == "__main__":
    config = Config()
    send_text("master", "", "asfs")
