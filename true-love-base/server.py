from threading import Thread

import flask
from flask import Flask

from robot import Robot

app = Flask(__name__)
robot_g: Robot

ROBOT_MISS_ERROR_RES = {"code": 101, "message": "server exception, unknown error occurred", "data": None}
SEND_ERROR_RES = {"code": 102, "message": "send fail, please retry", "data": None}
SUCCESS_RES = {"code": 0, "message": "success", "data": None}


@app.route('/')
def root():
    return "pong"


@app.route('/ping')
def ping():
    return "pong"


@app.route('/send/text', methods=['post'])
def send_text():
    if robot_g is None:
        return ROBOT_MISS_ERROR_RES

    send_receiver = flask.request.json.get('sendReceiver', '')
    at_receiver = flask.request.json.get('atReceiver', '')
    content = flask.request.json.get('content', '')
    robot_g.send_text_msg(content, send_receiver, at_receiver)

    return SUCCESS_RES
    pass


@app.route('/send/img', methods=['post'])
def send_img():
    if robot_g is None:
        return ROBOT_MISS_ERROR_RES

    path = flask.request.json.get('path', '')
    send_receiver = flask.request.json.get('sendReceiver', '')
    if robot_g.send_img_msg(path, send_receiver):
        return SEND_ERROR_RES

    return SUCCESS_RES
    pass


@app.route('/get/all', methods=['get'])
def get_all():
    if robot_g is None:
        return ROBOT_MISS_ERROR_RES

    return {"code": 0, "message": "success", "data": robot_g.allContacts}
    pass


def enable_http(robot: Robot):
    # 启动服务
    global robot_g
    robot_g = robot
    try:
        Thread(target=app.run, name="ListenHttp").start()
    except Exception as e:
        app.logger.erro("enable_http 发生致命错误", e)


if __name__ == '__main__':
    app.run(debug=True)
