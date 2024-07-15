import json
import logging
import time

import requests

from configuration import Config

config = Config()
host = config.BASE_SERVER["host"]
text_url = f"{host}/send/text"
text_img = f"{host}/send/img"
LOG = logging.getLogger("BaseClient")


def send_text(send_receiver, at_receiver, content):
    payload = json.dumps({
        "sendReceiver": send_receiver,
        "atReceiver": at_receiver,
        "content": content
    })
    headers = {
        'Content-Type': 'application/json'
    }
    try:
        start_time = time.time()
        LOG.info("开始请求base推送text内容, req:[%s]", payload)
        res = requests.request("POST", text_url, headers=headers, data=payload, timeout=(2, 60))
        # 检查HTTP响应状态
        res.raise_for_status()
        LOG.info("请求成功, cost:[%.0fms], res:[%s]", (time.time() - start_time) * 1000, res.json())
    except Exception as e:
        LOG.info("send_text 失败", e)
    return ""


def send_img(path, send_receiver):
    payload = json.dumps({
        "path": path,
        "sendReceiver": send_receiver,
    })
    headers = {
        'Content-Type': 'application/json'
    }

    try:
        start_time = time.time()
        LOG.info("开始请求base推送img内容, req:[%s]", payload[:200])
        res = requests.request("POST", text_img, headers=headers, data=payload, timeout=(2, 60))
        LOG.info("请求成功, cost:[%.0fms], res:[%s]", (time.time() - start_time) * 1000, res.json())
    except Exception as e:
        LOG.info("send_img 失败", e)
    return ""


if __name__ == "__main__":
    config = Config()
    send_img("123", config.BASE_SERVER.get("master_group"))
    send_text(config.BASE_SERVER.get("master_group"), config.BASE_SERVER.get("master_wxid"), "asfs")
