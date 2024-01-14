import json
import logging

import requests

from configuration import Config

config = Config()
host = config.BASE_SERVER["host"]
text_url = f"{host}/send/text"
text_img = f"{host}/send/img"
LOG = logging.getLogger("BaseClient")


def send_text(send_receiver, at_receiver, content):
    LOG.info("send_text start..., content:%s, send_receiver:%s", content, send_receiver)
    payload = json.dumps({
        "sendReceiver": send_receiver,
        "atReceiver": at_receiver,
        "content": content
    })
    headers = {
        'Content-Type': 'application/json'
    }
    try:
        requests.request("POST", text_url, headers=headers, data=payload, timeout=(2, 60))
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
        requests.request("POST", text_img, headers=headers, data=payload, timeout=(2, 60))
    except Exception as e:
        LOG.info("send_img 失败", e)
    return ""


if __name__ == "__main__":
    config = Config()
    send_img("123", config.BASE_SERVER.get("master_group"))
    send_text(config.BASE_SERVER.get("master_group"), config.BASE_SERVER.get("master_wxid"), "asfs")
