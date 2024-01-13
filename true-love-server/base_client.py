import json

import requests

from configuration import Config

config = Config()
host = config.BASE_SERVER["host"]
text_url = f"{host}/send-text"
text_img = f"{host}/send-img"


def send_text(send_receiver, at_receiver, content):
    payload = json.dumps({
        "sendReceiver": send_receiver,
        "atReceiver": at_receiver,
        "content": content
    })
    headers = {
        'Content-Type': 'application/json'
    }
    return requests.request("POST", text_url, headers=headers, data=payload, timeout=(2, 60))


def send_img(path, send_receiver):
    payload = json.dumps({
        "path": path,
        "sendReceiver": send_receiver,
    })
    headers = {
        'Content-Type': 'application/json'
    }
    return requests.request("POST", text_img, headers=headers, data=payload, timeout=(2, 60))
