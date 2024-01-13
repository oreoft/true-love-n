import flask
from flask import Flask

import base_client
import msg_router
from configuration import Config
from models.wx_msg import WxMsgServer

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
    app.logger.info("推送消息收到请求, req: %s", flask.request.json)
    if flask.request.json.get('token') in http_config.get("token", []):
        send_receiver = flask.request.json.get('sendReceiver')
        at_receiver = flask.request.json.get('atReceiver')
        content = flask.request.json.get('content')
        receiver_map = http_config.get("receiver_map", [])
        # 判断是否合法发送人
        if (not receiver_map.get(send_receiver)) or not content:
            return {"code": 100, "message": "input error or receivers not registered", "data": None}
        # 开始发送
        try:
            base_client.send_text(receiver_map.get(send_receiver, ""), receiver_map.get(at_receiver, ""), content)
            return {"code": 0, "message": "success", "data": None}
        except Exception as e:
            app.logger.error("推送消息可能失败", e)
            return {"code": 104, "message": str(e.args), "data": None}
    return {"code": 103, "message": "failed token check", "data": None}


@app.route('/get-chat', methods=['post'])
def get_chat():
    app.logger.info("聊天消息收到请求, req: %s", flask.request.json)
    # 进行消息路由
    try:
        result = msg_router.router_msg(WxMsgServer(flask.request.json))
        return {"code": 0, "message": "success", "data": result}
    except Exception as e:
        app.logger.error("聊天消息处理失败", e)
        return {"code": 105, "message": str(e.args), "data": None}


def enable_http():
    """暴露 HTTP 发送消息接口供外部调用，不配置则忽略"""
    if not http_config:
        return
    # 启动服务
    app.run(port=http_config.get("port", "8088"), host=http_config.get("host", "0.0.0.0"))


if __name__ == '__main__':
    app.run(port=8088)
