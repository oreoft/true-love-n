import json

import requests

from configuration import Config

config = Config()
host = config.BASE_SERVER["host"]
url = f"{host}/send-text"


def send_text(send_receiver, at_receiver, content):
    payload = json.dumps({
        "sendReceiver": send_receiver,
        "atReceiver": at_receiver,
        "content": content
    })
    headers = {
        'Content-Type': 'application/json'
    }
    return requests.request("POST", url, headers=headers, data=payload, timeout=(2, 60))
