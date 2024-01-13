import json
from datetime import datetime

import requests

from configuration import Config


class TrigTaskHandler:
    def __init__(self):
        config = Config()
        self.allowUser = config.GITHUB.get("allow_user", [])
        self.token: str = config.GITHUB.get("token")
        self.card_user: dict = config.CARD.get("card_user", {})

    def run(self, question: str, sender: str) -> str:
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
        return '该执行任务无法找到'

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
        print(requests.request("POST", url, headers=headers, data=payload))
        return "命令发送成功, 请等待部署平台结果"

    @staticmethod
    def _query_cafeteria_card_record_all():
        results = {}
        try:
            # 读取次数记录
            with open("cardRecord.json", "r") as file:
                record = json.load(file)

            # 读取刷卡记录
            with open("cardSwipeRecords.json", "r") as file:
                swipe_records = json.load(file)

            for wix in record:
                if record[wix] > 0:
                    result = f"当前还剩下[{record[wix]}]次"
                else:
                    result = "无效的卡号或次数不足"

                # 筛选特定卡号的最近 10 条记录
                recent_swipes = [r for r in swipe_records if r["cardNumber"] == wix][-10:]
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

    @staticmethod
    def _query_cafeteria_card_record(wix):
        try:
            # 读取次数记录
            with open("cardRecord.json", "r") as file:
                record = json.load(file)

            if wix in record and record[wix] >= 0:
                result = f"当前还剩下[{record[wix]}]次"
            else:
                result = "查询失败, 无效的卡号或次数不足"

            # 读取刷卡记录
            with open("cardSwipeRecords.json", "r") as file:
                swipe_records = json.load(file)

            # 筛选特定卡号的最近 10 条记录
            recent_swipes = [r for r in swipe_records if r["cardNumber"] == wix][-10:]
            recent_swipes.reverse()
            result += f"\n最近的刷卡记录:\n" + "\n".join([f"{r['currentTime']}" for r in recent_swipes])
        except FileNotFoundError:
            result = "查询失败, 记录文件不存在"
        except json.JSONDecodeError:
            result = "查询失败, 记录文件格式错误"
        except KeyError:
            result = "查询失败, 卡号不存在"
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
                result = "刷卡失败, 无效的卡号或次数不足"
            with open("cardRecord.json", "w") as file:
                json.dump(record, file)
        except FileNotFoundError:
            result = "刷卡失败, 记录文件不存在"
        except json.JSONDecodeError:
            result = "刷卡失败, 记录文件格式错误"
        except KeyError:
            result = "刷卡失败, 卡号不存在"
        return result

    @staticmethod
    def _record_card_swipe(card_number, rest_count):
        # 获取当前时间作为刷卡时间
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 构建刷卡记录
        swipe_record = {
            "currentTime": current_time,
            "cardNumber": card_number,
            "restCount": rest_count
        }

        # 读取现有的记录文件，如果不存在则创建一个新的列表
        try:
            with open("cardSwipeRecords.json", "r") as file:
                records = json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            records = []

        # 添加新的刷卡记录
        records.append(swipe_record)

        # 将更新后的记录写回文件
        with open("cardSwipeRecords.json", "w") as file:
            json.dump(records, file, indent=4)