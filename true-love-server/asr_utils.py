import base64
import hashlib
import hmac
import json
import logging
import time
from datetime import datetime

import requests

from configuration import Config

LOG = logging.getLogger("asr_utils")
config = Config()
SECRET_ID = config.ASR['secret_id']
SECRET_KEY = config.ASR['secret_key']
ASR_APPID = config.ASR['asr_appid']
ASR_SECRET_ID = config.ASR['asr_secret_id']
ASR_SECRET_KEY = config.ASR['asr_secret_key']
endpoint = "asr.tencentcloudapi.com"


def get_signature(secret_key, date, service, string_to_sign):
    # ************* 步骤 3：计算签名 *************
    # 计算派生签名密钥
    secret_date = hmac.new(('TC3' + secret_key).encode('UTF-8'), date.encode('UTF-8'), hashlib.sha256).digest()
    secret_service = hmac.new(secret_date, service.encode('UTF-8'), hashlib.sha256).digest()
    secret_signing = hmac.new(secret_service, 'tc3_request'.encode('UTF-8'), hashlib.sha256).digest()

    # 计算签名
    signature = hmac.new(secret_signing, string_to_sign.encode('UTF-8'), hashlib.sha256).hexdigest()
    return signature


def get_string_to_sign(method, endpoint, payload, service, date, headers):
    # ************* 步骤 1：拼接规范请求串 *************
    http_request_method = method.upper()
    canonical_uri = '/'
    canonical_querystring = ''

    # 拼接 CanonicalHeaders
    canonical_headers = 'content-type:' + headers['content-type'] + '\n' + 'host:' + endpoint + '\n'

    # 拼接 SignedHeaders
    signed_headers = 'content-type;host'

    # 计算 HashedRequestPayload
    hashed_request_payload = hashlib.sha256(payload.encode('utf-8')).hexdigest().lower()

    canonical_request = (http_request_method + '\n' +
                         canonical_uri + '\n' +
                         canonical_querystring + '\n' +
                         canonical_headers + '\n' +
                         signed_headers + '\n' +
                         hashed_request_payload)

    # ************* 步骤 2：拼接待签名字符串 *************
    algorithm = 'TC3-HMAC-SHA256'
    timestamp = int(time.time())
    credential_scope = date + '/' + service + '/' + 'tc3_request'
    hashed_canonical_request = hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()
    string_to_sign = (algorithm + '\n' +
                      str(timestamp) + '\n' +
                      credential_scope + '\n' +
                      hashed_canonical_request)

    return string_to_sign


def get_auth_header(secret_id, secret_key, service, method, endpoint, payload, headers):
    # 获取当前时间的 UTC 日期,格式为 YYYYMMDD
    date = datetime.utcfromtimestamp(int(time.time())).strftime("%Y-%m-%d")

    # ************* 步骤 2：拼接待签名字符串 *************
    string_to_sign = get_string_to_sign(method, endpoint, payload, service, date, headers)

    # ************* 步骤 3：计算签名 *************
    signature = get_signature(secret_key, date, service, string_to_sign)

    # ************* 步骤 4：拼接 Authorization *************
    algorithm = 'TC3-HMAC-SHA256'
    credential_scope = date + '/' + service + '/' + 'tc3_request'
    signed_headers = 'content-type;host'  # 修改这一行
    auth_header = (algorithm + ' ' +
                   'Credential=' + secret_id + '/' + credential_scope + ', ' +
                   'SignedHeaders=' + signed_headers + ', ' +
                   'Signature=' + signature)
    return auth_header


def get_submit_headers(service, method, endpoint, payload):
    headers = {
        "X-Tc-Host": endpoint,
        "X-Tc-Timestamp": str(int(time.time())),
        "X-Tc-Action": "CreateRecTask",
        "X-Tc-Version": "2019-06-14",
        "X-Tc-Region": "ap-guangzhou",
        "content-type": "application/json; charset=utf-8",
        "Host": endpoint,  # 添加这一行
    }
    headers["Authorization"] = get_auth_header(ASR_SECRET_ID, ASR_SECRET_KEY, service, method, endpoint, payload,
                                               headers)
    return headers


def upload_audio(audio_file_path):
    with open(audio_file_path, "rb") as f:
        audio_data = f.read()
    service = "asr"
    method = "POST"
    params = {
        "ChannelNum": 1,
        "EngineModelType": "16k_zh-PY",
        "ResTextFormat": 0,
        "Data": base64.b64encode(audio_data).decode('utf-8'),
        "SourceType": 1,
    }
    payload = json.dumps(params)
    headers = get_submit_headers(service, method, endpoint, payload)
    response = requests.post(f"https://{endpoint}/", headers=headers, data=payload)
    return response.json()


def do_asr(audio_file_path):
    try:
        start_time = time.time()
        task_info = upload_audio(audio_file_path)
        logging.info(f"do_asr submit success cost:{int(time.time() - start_time)} task:{task_info}")
        if task_info.task_info.get('Response').get('Error'):
            return f"语言识别失败, 请让用户再试一次, 理由是: f{task_info.task_info.get('Response').get('Error').get('Message')}"
        start_time = time.time()
        result = get_result(task_info.get('Response').get('Data').get('TaskId'))
        logging.info(f"do_asr result success cost:{int(time.time() - start_time)} result:{result}")
        return result
    except Exception:
        return "语言识别失败, 让用户再试一次"


def get_result_headers(service, method, endpoint, payload):
    headers = {
        "X-Tc-Host": endpoint,
        "X-Tc-Timestamp": str(int(time.time())),
        "X-Tc-Action": "DescribeTaskStatus",
        "X-Tc-Version": "2019-06-14",
        "X-Tc-Region": "ap-guangzhou",
        "content-type": "application/json; charset=utf-8",
        "Host": endpoint,  # 添加这一行
    }
    headers["Authorization"] = get_auth_header(ASR_SECRET_ID, ASR_SECRET_KEY, service, method, endpoint, payload,
                                               headers)
    return headers


def get_result(task_id, polling_interval=2):
    """
    根据TaskId轮询获取语音识别结果

    Args:
        task_id (str): 语音识别任务ID
        polling_interval (int): 轮询间隔时间(秒)

    Returns:
        dict: 语音识别结果,包含识别文本和其他信息
    """
    params = {
        "TaskId": task_id
    }
    payload = json.dumps(params)
    service = "asr"
    method = "POST"
    headers = get_result_headers(service, method, endpoint, payload)

    while True:
        try:
            # 发送GET请求获取结果
            response = requests.post(f"https://{endpoint}/", data=payload, headers=headers)
            # 解析响应数据
            result = response.json()
            # 如果任务已完成,返回结果
            if result.get("Response", {}).get("Data").get("Status") == 2:
                return result.get("Response", {}).get("Data").get("Result")
            # 如果任务正在进行中,等待一段时间后继续轮询
            logging.info(f"获取结果为{result}, 等待下一次重试")
            time.sleep(polling_interval)
        except Exception:
            logging.exception("asr get_result error")
            return "语言识别失败, 让用户再试一次"


if __name__ == '__main__':
    # 使用示例
    audio_file_path = "/Users/oreoft/Downloads/2023-12-04T17:40:50Z.m4a"
    result = upload_audio(audio_file_path)
    print(result)
    print(get_result(result.get('Response').get('Data').get('TaskId')))
