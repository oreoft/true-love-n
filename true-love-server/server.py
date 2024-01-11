import flask
from flask import Flask

import base_client
from configuration import Config

app = Flask(__name__)
http_config: dict = Config().HTTP


@app.route('/')
def root():
    return "pong"


@app.route('/ping')
def ping():
    return "pong"


@app.route('/send-msg', methods=['post'])
def send_msg():
    app.logger.info(f"推送消息收到请求, req:{flask.request.json}")
    if flask.request.json.get('token') in http_config.get("token", []):
        send_receiver = flask.request.json.get('sendReceiver')
        at_receiver = flask.request.json.get('atReceiver')
        content = flask.request.json.get('content')
        receiver_map = http_config.get("receiver_map", [])
        # 判断是否合法发送人
        if (not receiver_map.get(send_receiver)) or not content:
            return {"code": 100, "message": "input error or receivers not registered", "data": None}
        # 开始发送
        base_client.send_text(content, receiver_map.get(send_receiver, ""), receiver_map.get(at_receiver, ""))
        return {"code": 0, "message": "success", "data": None}
    return {"code": 103, "message": "failed token check", "data": None}


def enable_http():
    """暴露 HTTP 发送消息接口供外部调用，不配置则忽略"""
    if not http_config:
        return
    # 启动服务
    app.run(port=http_config.get("port", "8088"), host=http_config.get("host", "0.0.0.0"))


if __name__ == '__main__':
    app.run(port=8088)
