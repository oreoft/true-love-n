# -*- coding: utf-8 -*-
"""
Job Process - 定时任务处理

包含各种定时任务的具体实现。
"""

import concurrent
import functools
import logging
import os
import re
import time
from concurrent import futures
from datetime import datetime

import pytz
import requests
from bs4 import BeautifulSoup
from PIL import Image

from ..services import base_client
from ..core import Config
from ..handlers import TrigSearchHandler, TrigTaskHandler

trig_search_handler = TrigSearchHandler()
trig_task_handler = TrigTaskHandler()
executor = concurrent.futures.ThreadPoolExecutor(max_workers=3)
# 使用新的 AUTO_NOTICE 配置（兼容旧的 groups.auto_notice）
_config = Config()
config = _config.AUTO_NOTICE
alapi_config = _config.ALAPI
test_room_ids: list = config.get("test", [])
LOG = logging.getLogger("JobProcess")

# 默认网络请求超时时间（秒）
DEFAULT_TIMEOUT = 60


def log_function_execution(func):
    """装饰器：在函数执行前后打印信息，并记录执行时间。"""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        LOG.info("开始执行job:[%s]", func.__name__)

        result = func(*args, **kwargs)

        LOG.info("job:[%s]执行完毕，cost:[%s]ms", func.__name__, (time.time() - start_time) * 1000)
        return result

    return wrapper


@log_function_execution
def notice_mei_yuan():
    room_ids: list = config.get("notice_mei_yuan")
    rsp = trig_search_handler.run("查询美元汇率")
    numbers = re.findall(r'\d+\.\d+|\d+', rsp)
    LOG.info(numbers)
    if len(numbers) > 2 and float(numbers[2]) <= 700:
        for room_id in room_ids:
            base_client.send_text(room_id, "", "提醒现在的美元汇率情况低于700：\n" + rsp)
            time.sleep(5)
    return True


@log_function_execution
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
        time.sleep(5)
    return True


@log_function_execution
def notice_ao_yuan_schedule():
    room_ids: list = config.get("notice_ao_yuan_schedule")
    rsp = trig_search_handler.run("查询澳币汇率")
    rsp2 = trig_search_handler.run("查询美元汇率")
    msg = "早上好☀️宝宝，\n\n"
    if rsp != "": msg = msg + "今日澳币汇率情况：\n" + rsp + "\n\n"
    if rsp2 != "": msg = msg + "今日美元汇率情况：\n" + rsp2
    moyu_dir = "https://api.vvhan.com/api/moyu"
    # 使用相对路径，base 端会自动解析到 true-love-server 目录
    zao_bao_path = 'zaobao-jpg/' + datetime.now().strftime('%m-%d-%Y') + '.jpg'
    for room_id in room_ids:
        base_client.send_text(room_id, "", msg)
        base_client.send_img(moyu_dir, room_id)
        base_client.send_img(zao_bao_path, room_id)
        time.sleep(5)
    return True


@log_function_execution
def send_daily_notice(room_id, content='早上好☀️家人萌~', tz: str = "Asia/Shanghai"):
    # 使用指定时区的日期，确保文件名与下载任务的触发时间一致
    current_date = datetime.now(pytz.timezone(tz)).strftime('%m-%d-%Y')
    moyu_file_path = f'moyu-jpg/{current_date}.jpg'
    zao_bao_file_path = f'zaobao-jpg/{current_date}.jpg'
    r_resp = trig_search_handler.run("查询日元汇率")
    if r_resp != "": content += "\n\n今日日元汇率情况：\n" + r_resp
    base_client.send_text(room_id, '', content)
    if check_image_openable(moyu_file_path):
        moyu_res = base_client.send_img(moyu_file_path, room_id)
        LOG.info(f"send_image: {moyu_file_path}, result: {moyu_res}")
    if check_image_openable(zao_bao_file_path):
        zao_bao_res = base_client.send_img(zao_bao_file_path, room_id)
        LOG.info(f"send_image: {moyu_file_path}, result: {zao_bao_res}")


@log_function_execution
def send_aoyun_notice(room_id):
    aoyun_news = trig_search_handler.run("奥运赛事")
    base_client.send_text(room_id, '', aoyun_news)
    if aoyun_news:
        base_client.send_text(room_id, '', trig_search_handler.run("奥运奖牌"))


@log_function_execution
def notice_moyu_schedule():
    room_ids: list = config.get("notice_moyu_schedule")
    for room_id in room_ids:
        send_daily_notice(room_id)
        time.sleep(30)
    return True


@log_function_execution
def notice_usa_moyu_schedule():
    room_ids: list = config.get("notice_usa_moyu_schedule", [])
    for room_id in room_ids:
        send_daily_notice(room_id, "早上好☀️友友们~, \n现在国内太阳已经落下, 多赢阿美莉卡一天", tz="America/Chicago")
        time.sleep(30)
    return True


@log_function_execution
def notice_test():
    for test_room_id in test_room_ids:
        base_client.send_text(test_room_id, "", "test")
        LOG.info("notice_test success")


@log_function_execution
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


@log_function_execution
def download_moyu_file():
    # 使用当前工作目录
    download_directory = 'moyu-jpg/'
    if not os.path.exists(download_directory):
        os.makedirs(download_directory)
    local_filename = f'{get_current_date_utc8()}.jpg'
    full_file_path = os.path.join(download_directory, local_filename)
    retry_count = 3
    file_url = ''
    for i in range(retry_count):
        try:
            file_url = get_moyu_url_by_wx()
            if file_url:
                break
        except Exception as e:
            LOG.error(f"download_moyu_file Failed to fetch data. Retry count:{i}, Error:{e}")
            time.sleep(5)
    if file_url:
        response = requests.get(file_url, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        with open(full_file_path, 'wb') as f:
            f.write(response.content)
        LOG.info(f'{local_filename}已下载到 {download_directory}')
    else:
        LOG.error(f"未能获取到摸鱼文件的链接 {download_directory}")


@log_function_execution
def download_zao_bao_file():
    # 使用当前工作目录
    download_directory = 'zaobao-jpg/'
    if not os.path.exists(download_directory):
        os.makedirs(download_directory)
    local_filename = f'{get_current_date_utc8()}.jpg'
    full_file_path = os.path.join(download_directory, local_filename)

    url = "https://v3.alapi.cn/api/zaobao"
    token = alapi_config.get("token", "")
    if not token:
        LOG.error("ALAPI token 未配置，请在 config.yaml 中设置 alapi.token")
        return
    payload = f"token={token}&format=image"
    headers = {'Content-Type': "application/x-www-form-urlencoded"}
    response = requests.post(url, data=payload, headers=headers, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()

    with open(full_file_path, 'wb') as file:
        file.write(response.content)
    LOG.info(f'{local_filename} 已下载到 {download_directory}')


def async_download_zao_bao_file():
    executor.submit(download_zao_bao_file)


def async_download_moyu_file():
    executor.submit(download_moyu_file)


def get_moyu_url_by_wx():
    url = "https://mp.weixin.qq.com/mp/appmsgalbum?action=getalbum&album_id=3743225907507462153"
    response = requests.get(url, timeout=DEFAULT_TIMEOUT)

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        album_items = soup.find_all('li', class_='album__list-item')

        for item in album_items:
            title = item.find('div', class_='album__item-title').text.strip()
            if f"[摸鱼人日历]{get_current_date_utc8()}" in title or f"[摸鱼人日历]{get_current_date_utc8().lstrip('0')}" in title:
                link = item['data-link']
                LOG.info(f"article link: {link}")
                result = send_to_jina(link)
                LOG.info(f"result link: {result}")
                return result
    else:
        LOG.error(f"download_moyu_file_by_wx Failed to fetch data. Status code:{response.status_code}")


def send_to_jina(link):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36'
    }
    response = requests.get(link, headers=headers, timeout=DEFAULT_TIMEOUT)

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        target_text = "今天你摸鱼了吗？"
        found_target = False

        for element in soup.descendants:
            if isinstance(element, str) and target_text in element:
                found_target = True
                continue

            if found_target and element.name == 'img' and element.get('data-src'):
                image_url = element['data-src']
                if not image_url.startswith('http'):
                    image_url = 'https:' + image_url
                LOG.info(f"Found image URL after target text: {image_url}")
                return image_url

        LOG.error("No suitable image found after target text in the article")
        return None
    else:
        LOG.error(f"Failed to fetch data from WeChat article. Status code:{response.status_code}")
        return None


def get_current_date_utc8():
    tz = pytz.timezone('Asia/Shanghai')
    current_date_utc8 = datetime.now(tz)
    formatted_date = current_date_utc8.strftime('%m月%d号')
    return formatted_date


def check_image_openable(image_path):
    try:
        with Image.open(image_path) as img:
            img.verify()
            LOG.info("Image is openable and appears to be valid.")
            return True
    except (IOError, SyntaxError) as e:
        LOG.error(f"Cannot open image: {e}")
        return False
