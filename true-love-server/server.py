import time

from flask import Flask, g, request

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
    app.logger.info("推送消息收到请求, req: %s", request.json)
    if request.json.get('token') in http_config.get("token", []):
        send_receiver = request.json.get('sendReceiver')
        at_receiver = request.json.get('atReceiver')
        content = request.json.get('content')
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
    app.logger.info("聊天消息收到请求, req: %s", request.json)
    # 鉴权判断
    if request.json.get('token') not in http_config.get("token", []):
        return {"code": 103, "message": "failed token check", "data": None}
    # 进行消息路由
    try:
        result = msg_router.router_msg(WxMsgServer(request.json))
        return {"code": 0, "message": "success", "data": result}
    except Exception as e:
        app.logger.error("聊天消息处理失败", e)
        return {"code": 105, "message": str(e.args), "data": None}


@app.before_request
def before_request_logging():
    g.start_time = time.time()
    app.logger.info("Request:[%s %s], req:[%s]", request.method, request.path, request.get_data(as_text=True)[:200])


@app.after_request
def after_request_logging(response):
    cost = (time.time() - g.start_time) * 1000
    app.logger.info("Response:[%s %s, cost:%.0fms], res:[%s]", request.method, request.path, cost,
                    response.get_data(as_text=True)[:200])
    return response


def enable_http():
    """暴露 HTTP 发送消息接口供外部调用，不配置则忽略"""
    if not http_config:
        return
    # 启动服务
    app.run(port=http_config.get("port", "8088"), host=http_config.get("host", "0.0.0.0"), threaded=True)


if __name__ == '__main__':
    app.run(port=8088)
