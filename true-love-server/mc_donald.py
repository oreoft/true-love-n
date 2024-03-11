import json
import os
import random
import string

import requests

url = "https://us-prod.api.mcd.com/exp/v2/customer/registration"
# 设置代理
os.environ['HTTP_PROXY'] = "http://your_proxy_address:port"
os.environ['HTTPS_PROXY'] = "https://your_proxy_address:port"
def generate_random_number_uuid(length=8):
    # 生成一个指定长度的随机数字字符串
    # 每次生成的数字范围是0到9
    number_uuid = ''.join([str(random.randint(0, 9)) for _ in range(length)])
    return number_uuid


def send_mail():
    random_number_uuid = generate_random_number_uuid(8)
    gmail_addr = f"mcdonalovee+{random_number_uuid}@gmail.com"
    headers = {
        "Host": "us-prod.api.mcd.com",
        "mcd-sourceapp": "GMA",
        "cache-control": "true",
        "user-agent": "MCDSDK/8.0.0 (iPhone; 17.0.3; en-US) GMA/8.0.0",
        "mcd-uuid": "1F6DB9F7-CD21-40BF-8D13-F10563414FA5",
        "authorization": f"Bearer {get_token()}",
        "tracestate": "1248339@nr=0-2-734056-437003215-901c93fe5e4228d2--0--1710133785133",
        "mcd-clientid": "8cGckR5wPgQnFBc9deVhJ2vT94WhMBRL",
        "accept-language": "en-US",
        "accept-charset": "utf-8",
        "content-type": "application/json",
        "accept": "application/json",
        "mcd-marketid": "US",
    }
    data = {
        "lastName": "true",
        "policies": {
            "acceptancePolicies": {
                "1": True,
                "6": False,
                "4": True,
                "5": False
            }
        },
        "application": "gma",
        "firstName": "love",
        "emailAddress": gmail_addr,
        "preferences": [
            {"details": {"email": "en-US", "mobileApp": "en-US"}, "preferenceId": 1},
            {"details": {"email": "N", "mobileApp": "Y"}, "preferenceId": 2},
            {"details": {"email": "Y", "mobileApp": "Y"}, "preferenceId": 3},
            {"details": {"email": 123456, "mobileApp": 123456}, "preferenceId": 4},
            {"details": {"email": "Y", "mobileApp": "Y"}, "preferenceId": 6},
            {"details": {"email": "Y", "mobileApp": "Y"}, "preferenceId": 7},
            {"details": {"email": "Y", "mobileApp": "Y"}, "preferenceId": 8},
            {"details": {"email": "Y", "mobileApp": "Y"}, "preferenceId": 9},
            {"details": {"email": "Y", "mobileApp": "Y"}, "preferenceId": 10},
            {"details": {}, "preferenceId": 11},
            {"details": {"enabled": "Y"}, "preferenceId": 12},
            {"details": {"enabled": "Y"}, "preferenceId": 13},
            {"details": {"enabled": "Y"}, "preferenceId": 14},
            {"details": {"enabled": "Y"}, "preferenceId": 15},
            {"details": {"enabled": "Y"}, "preferenceId": 16},
            {"details": {"enabled": "Y"}, "preferenceId": 17},
            {"details": {"enabled": "Y"}, "preferenceId": 18},
            {"details": {"enabled": "Y"}, "preferenceId": 19},
            {"details": {"enabled": "Y"}, "preferenceId": 20},
            {"details": {"enabled": "Y"}, "preferenceId": 21},
            {"details": {"enabled": "Y"}, "preferenceId": 22}
        ],
        "device": {
            "isActive": "Y",
            "osVersion": "17.0.3",
            "timezone": "America/Chicago",
            "deviceIdType": "IDFV",
            "deviceId": f"{random.choice(string.ascii_uppercase)}2098F8F-CA4E-4E81-96CD-B21F618145D{random.choice(string.ascii_uppercase)}",
            "os": "ios"
        },
        "optInForMarketing": False,
        "audit": {"registrationChannel": "M"},
        "credentials": {
            "type": "email",
            "sendMagicLink": True,
            "loginUsername": gmail_addr
        },
        "address": {
            "country": "US",
            "zipCode": "60616"
        },
        "subscriptions": [
            {"subscriptionId": "1", "optInStatus": "Y"},
            {"subscriptionId": "2", "optInStatus": "Y"},
            {"subscriptionId": "3", "optInStatus": "Y"},
            {"subscriptionId": "4", "optInStatus": "Y"},
            {"subscriptionId": "5", "optInStatus": "Y"},
            {"subscriptionId": "7", "optInStatus": "Y"},
            {"subscriptionId": "10", "optInStatus": "N"},
            {"subscriptionId": "11", "optInStatus": "N"},
            {"subscriptionId": "29", "optInStatus": "N"},
            {"subscriptionId": "24", "optInStatus": "Y"},
            {"subscriptionId": "25", "optInStatus": "Y"},
            {"subscriptionId": "30", "optInStatus": "Y"}
        ]
    }
    from configuration import Config
    proxy = Config().LLM_BOT.get("proxy")
    response = requests.post(url, headers=headers, data=json.dumps(data), proxies={"http": proxy, "https": proxy})
    if response.status_code == 200 and response.json().get('status', {}).get('type') == 'Success':
        return True
    return False


auth_url = 'https://us-prod.api.mcd.com/v1/security/auth/token'

auth_headers = {
    'Host': 'us-prod.api.mcd.com',
    'content-type': 'application/x-www-form-urlencoded',
    'mcd-sourceapp': 'GMA',
    'accept': 'application/json',
    'authorization': 'Basic OGNHY2tSNXdQZ1FuRkJjOWRlVmhKMnZUOTRXaE1CUkw6WW00clZ5cXBxTnBDcG1yZFBHSmF0UnJCTUhoSmdyMjY=',
    'accept-charset': 'utf-8',
    'accept-language': 'en-US',
    'mcd-marketid': 'US',
    'user-agent': 'MCDSDK/8.0.0 (iPhone; 17.0.3; en-US) GMA/8.0.0',
}
auth_data = {
    'grantType': 'client_credentials'
}


def get_token():
    # 第一步：调用认证接口获取token
    from configuration import Config
    proxy = Config().LLM_BOT.get("proxy")
    auth_response = requests.post(auth_url, headers=auth_headers, data=auth_data, proxies={"http": proxy, "https": proxy})
    auth_response_json = auth_response.json()

    # 从响应中提取token
    token = auth_response_json['response']['token']
    return token


if __name__ == '__main__':
    send_mail()
