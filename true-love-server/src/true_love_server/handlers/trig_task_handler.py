# -*- coding: utf-8 -*-
"""
Trigger Task Handler - 任务触发处理器

处理各种执行任务，如部署、刷卡、发号等。
"""

import json
import logging
import random
import sqlite3
from datetime import datetime

import requests

from ..services import base_client
from ..core import Config

LOG = logging.getLogger("TrigTaskHandler")


class TrigTaskHandler:
    def __init__(self):
        config = Config()
        self.allowUser = config.GITHUB.get("allow_user", [])
        self.token: str = config.GITHUB.get("token")
        self.card_user: dict = config.CARD.get("card_user", {})
        self.muninn_allow_user = config.MUNINN.get("allow_user", [])
        self.muninn_api_base_url = config.MUNINN.get("api_base_url", "")
        self.muninn_admin_token = config.MUNINN.get("admin_token", "")

    def run(self, question: str, sender: str, room_id: str) -> str:
        if 'prod1' in question:
            if sender not in self.allowUser:
                return "该执行任务您没有执行权限哦"
            return self.run_ovlerlc_deploy(1)
        if 'prod2' in question:
            if sender not in self.allowUser:
                return "该执行任务您没有执行权限哦"
            return self.run_ovlerlc_deploy(2)
        if '刷卡' in question:
            if sender not in self.card_user.values():
                return "该执行任务您没有执行权限哦"
            return self.deduct_cafeteria_card_record(sender)
        if '查卡' in question:
            if sender not in self.card_user.values():
                return "该执行任务您没有执行权限哦"
            return self._query_cafeteria_card_record(sender)
        if '更新配置' in question:
            if sender not in self.allowUser:
                return "该执行任务您没有执行权限哦"
            return self.reload_config()
        if 'job_process-' in question:
            return self.do_job_process(question)
        if '发号2' in question or '取号2' in question:
            return self.mc_fa_hao2(question, sender)
        if '发号' in question or '取号' in question:
            return self.mc_fa_hao(question, sender)
        if '销号' in question:
            return self.mc_xiao_hao(question)
        if '查号' in question:
            return self.mc_cha_hao()
        if '抽签' in question:
            return self.chou_qian(room_id)
        if '生成muninn' in question:
            return self.generate_muninn_cdk(question, sender)
        return '诶嘿~没有找到这个执行任务呢，检查一下命令吧~'

    @staticmethod
    def do_job_process(question: str) -> str:
        method_name = question.split("-")[1]
        from ..jobs import job_process
        method_to_call = getattr(job_process, method_name, None)
        if method_to_call:
            method_to_call()
            return "好耶~执行成功啦~"
        else:
            result = f"Method {method_name} not found."
            LOG.info(result)
            return result

    def run_ovlerlc_deploy(self, num: int) -> str:
        url = f"https://api.github.com/repos/oreoft/overlc-backend-n/actions/workflows/ci-prod-publish{num}.yml/dispatches"

        payload = json.dumps({
            "ref": "master"
        })
        headers = {
            'Accept': 'application/vnd.github.v3+json',
            'Authorization': f'token {self.token}',
            'Content-Type': 'application/json'
        }
        LOG.info(requests.request("POST", url, headers=headers, data=payload))
        return "好耶~命令已经发送成功啦，等待部署平台的结果吧~"

    @staticmethod
    def query_cafeteria_card_record_all():
        results = {}
        try:
            with open("cardRecord.json", "r") as file:
                record = json.load(file)

            with open("cardSwipeRecords.json", "r") as file:
                swipe_records = json.load(file)

            for wix in record:
                if record[wix] > 0:
                    result = f"当前还剩下[{record[wix]}]次"
                else:
                    result = "呜呜~卡号无效或者次数不够了捏~"

                recent_swipes = [r for r in swipe_records if r["cardNumber"] == wix][-5:]
                recent_swipes.reverse()
                result += f"\n最近的刷卡记录:\n" + "\n".join([f"{r['currentTime']}" for r in recent_swipes])

                results[wix] = result

        except FileNotFoundError:
            return "记录文件不存在"
        except json.JSONDecodeError:
            return "记录文件格式错误"
        except KeyError:
            return "某些卡号在刷卡记录中不存在"

        return results

    def _query_cafeteria_card_record(self, wix):
        try:
            with open("cardRecord.json", "r") as file:
                record = json.load(file)

            if wix in record and record[wix] >= 0:
                result = f"当前还剩下[{record[wix]}]次"
            else:
                result = "呜呜~查询失败了，卡号无效或者次数不够捏~"

            with open("cardSwipeRecords.json", "r") as file:
                swipe_records = json.load(file)

            recent_swipes = [r for r in swipe_records if r["cardNumber"] == wix][-10:]
            recent_swipes.reverse()
            result += f"\n最近的刷卡记录:\n" + "\n".join([f"{r['currentTime']}" for r in recent_swipes])
        except FileNotFoundError as e:
            LOG.error("查询失败, 记录文件不存在: %s", e)
            result = "呜呜~查询失败了，找不到记录文件捏~"
        except json.JSONDecodeError as e:
            LOG.error("查询失败, 记录文件格式错误: %s", e)
            result = "呜呜~查询失败了，记录文件格式有问题捏~"
        except KeyError:
            result = "呜呜~查询失败了，找不到这个卡号捏~"
        return result

    def deduct_cafeteria_card_record(self, wix):
        try:
            with open("cardRecord.json", "r") as file:
                record = json.load(file)
            if wix in record and record[wix] > 0:
                record[wix] -= 1
                self._record_card_swipe(wix, record[wix])
                result = f"刷卡记录成功, 当前还剩下[{record[wix]}]次"
            else:
                result = "呜呜~刷卡失败了，卡号无效或者次数不够捏~"
            with open("cardRecord.json", "w") as file:
                json.dump(record, file)
        except FileNotFoundError:
            result = "呜呜~刷卡失败了，找不到记录文件捏~"
        except json.JSONDecodeError:
            result = "呜呜~刷卡失败了，记录文件格式有问题捏~"
        except KeyError:
            result = "呜呜~刷卡失败了，找不到这个卡号捏~"
        return result

    @staticmethod
    def _record_card_swipe(card_number, rest_count):
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        swipe_record = {
            "currentTime": current_time,
            "cardNumber": card_number,
            "restCount": rest_count
        }

        try:
            with open("cardSwipeRecords.json", "r") as file:
                records = json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            records = []

        records.append(swipe_record)

        with open("cardSwipeRecords.json", "w") as file:
            json.dump(records, file, indent=4)

    @staticmethod
    def reload_config():
        Config().reload()
        return "success"

    def mc_fa_hao(self, question, sender):
        device_id = self.get_device_id(question, sender)
        if '-' not in device_id:
            return device_id

        response = requests.get(f'https://mc-fahao.someget.work/mc-fahao?token={self.token}&device_id={device_id}')
        if response.status_code == 200:
            return response.text
        else:
            return "呜呜~发号遇到错误了捏，重试一下或者暂时手动注册吧~"

    def mc_xiao_hao(self, question):
        account_prefix = None
        if ":" in question:
            account_prefix = question.split(":")[1].strip()
        if not account_prefix:
            return "诶嘿~请输入要释放的mc账户prefix哦，格式: $执行销号:xxx"
        response = requests.get(
            f'https://mc-fahao.someget.work/mc-xiaohao?token={self.token}&account_prefix={account_prefix}')
        if response.status_code == 200:
            return response.text
        else:
            return "呜呜~销号遇到错误了捏，再试一次吧~"

    def mc_cha_hao(self):
        response = requests.get(
            f'https://mc-fahao.someget.work/mc-chahao?token={self.token}')
        if response.status_code == 200:
            return response.text
        else:
            return "呜呜~查号遇到错误了捏，再试一次吧~"

    @staticmethod
    def chou_qian(room_id):
        all = base_client.get_by_room_id(room_id)
        if not all:
            return "抽取失败, 本次幸运鹅是我自己, 嘿嘿"
        random_value = random.choice(list(all.values()))
        logging.info(f"随机选择的值: {random_value}")
        return "幸运鹅是: @" + random_value

    def mc_fa_hao2(self, question, sender):
        device_id = self.get_device_id(question, sender)
        if '-' not in device_id:
            return device_id
        response = requests.get(f'https://mc-fahao.someget.work/mc-fahao2?token={self.token}&device_id={device_id}')
        if response.status_code == 200:
            return response.text
        else:
            return "呜呜~发号遇到错误了捏，重试一下或者暂时手动注册吧~"

    @staticmethod
    def get_device_id(question, sender):
        device_id = None
        if ":" in question:
            device_id = question.split(":")[1].strip()

        import os
        db_path = os.path.join('dbs', 'mc_devices.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        if device_id:
            cursor.execute('REPLACE INTO mc_devices (sender, device_id) VALUES (?, ?)', (sender, device_id))
            conn.commit()
        else:
            cursor.execute('SELECT device_id FROM mc_devices WHERE sender = ?', (sender,))
            row = cursor.fetchone()
            if row:
                device_id = row[0]
            else:
                conn.close()
                return "诶嘿~首次使用需要带上设备id哦，格式: $执行发号:xxx，其中xxx是你的设备id~"
        conn.close()
        return device_id

    def generate_muninn_cdk(self, question: str, sender: str) -> str:
        """
        生成 Muninn CDK
        命令格式: $执行 生成muninn cdk-<level>-<days>
        示例: $执行 生成muninn cdk-pro-30
        """
        # 权限检查
        if sender not in self.muninn_allow_user:
            return "该执行任务您没有执行权限哦"
        
        # 检查配置
        if not self.muninn_api_base_url or not self.muninn_admin_token:
            LOG.error("Muninn 配置不完整: api_base_url=%s, admin_token=%s", 
                     self.muninn_api_base_url, bool(self.muninn_admin_token))
            return "呜呜~Muninn 配置不完整，请联系管理员~"
        
        try:
            # 解析参数: 从 "生成muninn cdk-pro-30" 提取
            # 找到 "cdk-" 开始的部分
            cdk_part = None
            for part in question.split():
                if part.startswith("cdk-"):
                    cdk_part = part
                    break
            
            if not cdk_part:
                return "诶嘿~命令格式不对哦，正确格式: $执行 生成muninn cdk-<等级>-<天数>\n示例: $执行 生成muninn cdk-pro-30"
            
            # 移除 "cdk-" 前缀，然后按 "-" 分割
            # cdk-pro-30 -> ["pro", "30"]
            parts = cdk_part[4:].split("-")
            
            if len(parts) != 2:
                return "诶嘿~命令格式不对哦，正确格式: $执行 生成muninn cdk-<等级>-<天数>\n示例: $执行 生成muninn cdk-pro-30"
            
            level = parts[0]
            try:
                duration_days = int(parts[1])
            except ValueError:
                return f"呜呜~天数必须是数字哦，您输入的是: {parts[1]}"
            
            # 调用 Muninn API
            url = f"{self.muninn_api_base_url}/membership/admin/cdk/generate"
            headers = {
                "X-Admin-Token": self.muninn_admin_token,
                "Content-Type": "application/json"
            }
            payload = {
                "level": level,
                "duration_days": duration_days,
                "count": 1
            }
            
            LOG.info("正在调用 Muninn API 生成 CDK: level=%s, days=%d", level, duration_days)
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            
            # 处理响应
            if response.status_code == 200:
                result = response.json()
                # code == 0 表示业务成功，非 0 表示业务异常
                if result.get("code") == 0 and result.get("data"):
                    codes = result["data"].get("codes", [])
                    if codes:
                        cdk_code = codes[0]
                        return f"✅ Muninn CDK 生成成功！\n\n等级: {level}\n天数: {duration_days}天\nCDK: {cdk_code}\n\n请妥善保管 CDK 码~"
                    else:
                        return "呜呜~生成失败了，API 返回的 CDK 列表为空~"
                else:
                    # code 非 0 是业务异常
                    error_msg = result.get("message", "未知错误")
                    error_code = result.get("code", "unknown")
                    LOG.error("Muninn API 业务异常: code=%s, message=%s", error_code, error_msg)
                    return f"呜呜~生成失败了: {error_msg}"
            else:
                LOG.error("Muninn API 调用失败: status=%d, response=%s", 
                         response.status_code, response.text)
                return f"呜呜~生成失败了，API 返回状态码: {response.status_code}"
        
        except requests.exceptions.Timeout:
            LOG.error("Muninn API 调用超时")
            return "呜呜~生成失败了，API 调用超时~"
        except requests.exceptions.RequestException as e:
            LOG.error("Muninn API 调用异常: %s", e)
            return f"呜呜~生成失败了，网络错误: {str(e)}"
        except Exception as e:
            LOG.error("生成 Muninn CDK 时发生未知错误: %s", e)
            return f"呜呜~生成失败了，发生未知错误: {str(e)}"
