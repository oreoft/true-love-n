import concurrent
import os
import re
import urllib.request
from concurrent import futures
from datetime import datetime

import requests

import base_client
from trig_search_handler import TrigSearchHandler
from trig_task_handler import TrigTaskHandler

trig_search_handler = TrigSearchHandler()
trig_task_handler = TrigTaskHandler()
executor = concurrent.futures.ThreadPoolExecutor(max_workers=3)


def notice_mei_yuan():
    roomId = '35053039913@chatroom'
    sender = 'wxid_tqn5yglpe9gj21'
    rsp = trig_search_handler.run("查询美元汇率")
    numbers = re.findall('\d+\.\d+|\d+', rsp)
    print(numbers)
    if len(numbers) > 2 and float(numbers[2]) <= 725:
        print()
        # base_client.send_text("提醒现在的美元汇率情况低于725：\n" + rsp, roomId, sender)
    return True


def notice_library_schedule():
    roomId = '39094040348@chatroom'
    # roomId = '2666401439@chatroom'
    sender = ''
    rsp = trig_search_handler.run("查询图书馆时间")
    rsp2 = trig_search_handler.run("查询美元汇率")
    rsp3 = trig_search_handler.run("查询gym时间")
    msg = "早上好☀️宝子们，\n\n"
    if rsp != "": msg = msg + "今日图书馆情况：\n" + rsp + "\n\n"
    if rsp3 != "": msg = msg + "今日gym情况：\n" + rsp3 + "\n\n"
    if rsp2 != "": msg = msg + "今日汇率情况：\n" + rsp2

    base_client.send_text(roomId, "", msg)
    return True


def notice_ao_yuan_schedule():
    roomId = '39121926591@chatroom'
    # roomId = '2666401439@chatroom'
    sender = ''
    rsp = trig_search_handler.run("查询澳币汇率")
    rsp2 = trig_search_handler.run("查询美元汇率")
    msg = "早上好☀️宝宝，\n\n"
    if rsp != "": msg = msg + "今日澳币汇率情况：\n" + rsp + "\n\n"
    if rsp != "": msg = msg + "今日美元汇率情况：\n" + rsp2
    base_client.send_text(roomId, "", msg)
    return True


def send_daily_notice(roomId):
    moyu_dir = os.path.dirname(os.path.abspath(__file__)) + '/moyu-jpg/' + datetime.now().strftime(
        '%m-%d-%Y') + '.jpg'
    zao_bao_dir = os.path.dirname(os.path.abspath(__file__)) + '/zaobao-jpg/' + datetime.now().strftime(
        '%m-%d-%Y') + '.jpg'

    base_client.send_text(roomId, '', '早上好☀️家人萌~')
    moyu_res = base_client.send_img(moyu_dir, roomId)
    zao_bao_res = base_client.send_img(zao_bao_dir, roomId)
    print(f"send_image: {moyu_dir}, result: {moyu_res}")
    print(f"send_image: {moyu_dir}, result: {zao_bao_res}")


def notice_moyu_schedule():
    roomIdDachang = '20923342619@chatroom'
    roomIdB = '34977591657@chatroom'
    roomIdLiu = '39295953189@chatroom'
    roomIdWuhan = '20624707540@chatroom'

    send_daily_notice(roomIdDachang)
    send_daily_notice(roomIdB)
    send_daily_notice(roomIdLiu)
    send_daily_notice(roomIdWuhan)
    return True


def notice_card_schedule():
    roomId = '39190072732@chatroom'
    # roomId = '2666401439@chatroom'

    msg = "今日结余一览\n\n"
    result = trig_task_handler.query_cafeteria_card_record_all()
    for key, value in trig_task_handler.card_user.items():
        try:
            msg += key + '\n' + result[value] + '\n\n'
        except KeyError:
            pass
    base_client.send_text(roomId, "", msg)
    return True


def async_download_file():
    executor.submit(download_zao_bao_file)


def async_download_moyu_file():
    executor.submit(download_moyu_file)


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
    file_url = 'https://moyu.qqsuu.cn/'
    # 使用urllib.request库下载文件并保存到指定的位置
    urllib.request.urlretrieve(file_url, full_file_path)
    print(f'{local_filename} 已下载到 {download_directory}')


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
    print(f'{local_filename} 已下载到 {download_directory}')
