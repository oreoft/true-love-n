import time
from threading import Thread

import flask
from flask import Flask, g, request

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


@app.route('/send/img', methods=['post'])
def send_img():
    if robot_g is None:
        return ROBOT_MISS_ERROR_RES

    path = flask.request.json.get('path', '')
    send_receiver = flask.request.json.get('sendReceiver', '')
    if robot_g.send_img_msg(path, send_receiver):
        return SEND_ERROR_RES

    return SUCCESS_RES


@app.route('/get/all', methods=['get'])
def get_all():
    if robot_g is None:
        return ROBOT_MISS_ERROR_RES

    return {"code": 0, "message": "success", "data": robot_g.allContacts}


@app.route('/get/by/room-id', methods=['post'])
def get_contacts_by_room_id():
    if robot_g is None:
        return ROBOT_MISS_ERROR_RES
    room_id = flask.request.json.get('room_id', '')
    return {"code": 0, "message": "success", "data": robot_g.get_contacts_by_room_id(room_id)}


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


def enable_http(robot: Robot):
    # 启动服务
    global robot_g
    robot_g = robot
    Thread(target=app.run, name="ListenHttp", kwargs={"host": "0.0.0.0", "threaded": True}, daemon=True).start()


if __name__ == '__main__':
    app.run(debug=True)
