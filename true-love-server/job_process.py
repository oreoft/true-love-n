import concurrent
import logging
import os
import re
import urllib.request
from concurrent import futures
from datetime import datetime

import requests

import base_client
from configuration import Config
from trig_search_handler import TrigSearchHandler
from trig_task_handler import TrigTaskHandler

trig_search_handler = TrigSearchHandler()
trig_task_handler = TrigTaskHandler()
executor = concurrent.futures.ThreadPoolExecutor(max_workers=3)
config = Config().GROUPS.get("auto_notice", {})
test_room_ids: list = config.get("test")
LOG = logging.getLogger("JobProcess")


def notice_mei_yuan():
    room_ids: list = config.get("notice_mei_yuan")
    rsp = trig_search_handler.run("查询美元汇率")
    numbers = re.findall('\d+\.\d+|\d+', rsp)
    LOG.info(numbers)
    if len(numbers) > 2 and float(numbers[2]) <= 700:
        for room_id in room_ids:
            base_client.send_text(room_id, "", "提醒现在的美元汇率情况低于700：\n" + rsp)
    return True


def notice_library_schedule():
    room_ids: list = config.get("notice_library_schedule")
    rsp = trig_search_handler.run("查询图书馆时间")
    rsp2 = trig_search_handler.run("查询美元汇率")
    rsp3 = trig_search_handler.run("查询gym时间")
    msg = "早上好☀️宝子们，\n\n"
    if rsp != "": msg = msg + "今日图书馆情况：\n" + rsp + "\n\n"
    if rsp3 != "": msg = msg + "今日gym情况：\n" + rsp3 + "\n\n"
    if rsp2 != "": msg = msg + "今日汇率情况：\n" + rsp2
    for room_id in room_ids:
        base_client.send_text(room_id, "", msg)
    return True


def notice_ao_yuan_schedule():
    room_ids: list = config.get("notice_ao_yuan_schedule")
    rsp = trig_search_handler.run("查询澳币汇率")
    rsp2 = trig_search_handler.run("查询美元汇率")
    msg = "早上好☀️宝宝，\n\n"
    if rsp != "": msg = msg + "今日澳币汇率情况：\n" + rsp + "\n\n"
    if rsp != "": msg = msg + "今日美元汇率情况：\n" + rsp2
    for room_id in room_ids:
        base_client.send_text(room_id, "", msg)
    return True


def send_daily_notice(room_id):
    moyu_dir = os.path.dirname(os.path.abspath(__file__)) + '/moyu-jpg/' + datetime.now().strftime(
        '%m-%d-%Y') + '.jpg'
    zao_bao_dir = os.path.dirname(os.path.abspath(__file__)) + '/zaobao-jpg/' + datetime.now().strftime(
        '%m-%d-%Y') + '.jpg'

    base_client.send_text(room_id, '', '早上好☀️家人萌~')
    moyu_res = base_client.send_img(moyu_dir, room_id)
    zao_bao_res = base_client.send_img(zao_bao_dir, room_id)
    LOG.info(f"send_image: {moyu_dir}, result: {moyu_res}")
    LOG.info(f"send_image: {moyu_dir}, result: {zao_bao_res}")


def notice_moyu_schedule():
    room_ids: list = config.get("notice_moyu_schedule")
    for room_id in room_ids:
        send_daily_notice(room_id)
    return True


def notice_test():
    for test_room_id in test_room_ids:
        base_client.send_text(test_room_id, "", "test")
        LOG.info("notice_test success")


def notice_card_schedule():
    room_ids: list = config.get("notice_card_schedule")

    msg = "今日结余一览\n\n"
    result = trig_task_handler.query_cafeteria_card_record_all()
    for key, value in trig_task_handler.card_user.items():
        try:
            msg += key + '\n' + result[value] + '\n\n'
        except KeyError:
            pass
    for room_id in room_ids:
        base_client.send_text(room_id, "", msg)
    return True


def download_moyu_file():
    # 获取当前脚本所在的目录，即项目目录
    project_directory = os.path.dirname(os.path.abspath(__file__))
    download_directory = project_directory + '/moyu-jpg/'
    # 获取当前日期并将其格式化为所需的字符串
    current_date = datetime.now().strftime('%m-%d-%Y')
    # 构建文件名，例如：10-20-2023.jpg
    local_filename = f'{current_date}.jpg'
    # 构建完整的文件路径
    full_file_path = os.path.join(download_directory, local_filename)
    # 指定要下载的文件的URL
    file_url = 'https://api.vvhan.com/api/moyu'
    # file_url = 'https://dayu.qqsuu.cn/moyuribao/apis.php'
    # 使用urllib.request库下载文件并保存到指定的位置
    urllib.request.urlretrieve(file_url, full_file_path)
    LOG.info(f'{local_filename} 已下载到 {download_directory}')


def download_zao_bao_file():
    # 获取当前脚本所在的目录，即项目目录
    project_directory = os.path.dirname(os.path.abspath(__file__))
    download_directory = project_directory + '/zaobao-jpg/'
    # 获取当前日期并将其格式化为所需的字符串
    current_date = datetime.now().strftime('%m-%d-%Y')
    # 构建文件名，例如：10-20-2023.jpg
    local_filename = f'{current_date}.jpg'
    # 构建完整的文件路径
    full_file_path = os.path.join(download_directory, local_filename)

    # 获取文件内容
    url = "https://v2.alapi.cn/api/zaobao"
    payload = "token=ODECJI71rCNDt6DO&format=image"
    headers = {'Content-Type': "application/x-www-form-urlencoded"}
    response = requests.request("POST", url, data=payload, headers=headers)

    # 保存到指定的位置
    with open(full_file_path, 'wb') as file:
        file.write(response.content)
    LOG.info(f'{local_filename} 已下载到 {download_directory}')


def async_download_file():
    executor.submit(download_zao_bao_file)


def async_download_moyu_file():
    executor.submit(download_moyu_file)
