import time

from flask import Flask, g, request
from flask_cors import CORS

from chat_msg_handler import ChatMsgHandler
from configuration import Config

app = Flask(__name__)
CORS(app)
http_config: dict = Config().HTTP
handler = ChatMsgHandler()


@app.route('/')
def root():
    return "pong"


@app.route('/ping')
def ping():
    return "pong"


@app.route('/get-llm', methods=['post'])
def get_chat():
    app.logger.info("llm消息收到请求, req: %s", request.json)
    # 鉴权判断
    if request.json.get('token') not in http_config.get("token", []):
        return {"code": 103, "message": "failed token check", "data": None}
    # 进行消息路由
    try:
        result = handler.get_answer(request.json.get('content'),
                                    request.json.get('wxid', ''),
                                    request.json.get('sender', ''))
        return {"code": 0, "message": "success", "data": result}
    except Exception as e:
        app.logger.error("llm处理失败", e)
        return {"code": 105, "message": str(e.args), "data": None}


@app.route('/gen-img', methods=['post'])
def gen_img():
    app.logger.info("gen-img消息收到请求, req: %s", str(request.json)[:200])
    # 鉴权判断
    if request.json.get('token') not in http_config.get("token", []):
        return {"code": 103, "message": "failed token check", "data": None}
    # 进行消息路由
    try:
        result = handler.get_img(request.json.get('content'),
                                 request.json.get('img_path'),
                                 request.json.get('wxid', ''),
                                 request.json.get('sender', ''))
        return {"code": 0, "message": "success", "data": result}
    except Exception as e:
        app.logger.error("gen-img处理失败", e)
        return {"code": 105, "message": e.args[0], "data": None}


@app.route('/api/dream/community/list', methods=['post'])
def community_list():
    import requests
    import json
    url = "https://v2-0-2---dreamorebackend-vsy7hiaoca-uc.a.run.app/api/dream/community/list"
    payload = json.dumps({
        "sort_criteria": request.json.get('sort_criteria'),
        "last_doc_id": request.json.get('last_doc_id')
    })
    headers = {
        'Content-Type': 'application/json'
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    return response.json()


@app.before_request
def before_request_logging():
    g.start_time = time.time()
    app.logger.info("Request:[%s], req:[%s]", request.url, request.get_data(as_text=True)[:200])


@app.after_request
def after_request_logging(response):
    cost = (time.time() - g.start_time) * 1000
    app.logger.info(f"Response:[cost:%.0fms], res:[%s]:", cost, response.get_data(as_text=True)[:200])
    return response


def enable_http():
    """暴露 HTTP 发送消息接口供外部调用，不配置则忽略"""
    if not http_config:
        return
    # 启动服务
    app.run(port=http_config.get("port", "8088"), host=http_config.get("host", "0.0.0.0"), threaded=True)


if __name__ == '__main__':
    app.run(port=8088)
