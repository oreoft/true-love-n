import json
import logging
import time
from datetime import datetime

import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from pyunit_time import Time

import base_client
from configuration import Config

TIME_FORMAT = "%Y-%m-%d %H:%M:%S"

# 创建后台调度器
scheduler = BackgroundScheduler()
# 启动调度器
scheduler.start()
config = Config()


class TrigRemainderHandler:
    """ 提醒今天晚上七点记得把护照放包里
        把提示词全部做时间解析,得出提醒的时间
        提醒内容也不做解析,全部进行提醒
    """

    def __init__(self):
        self.LOG = logging.getLogger("TrigRemainderHandler")

    def router(self, question: str, sender, at):
        if question.startswith("提醒查询"):
            return self.get_reminder_by_send(at)
        if question.startswith("提醒删除"):
            return self.remove_reminder_by_id(question.replace("提醒删除", ""))
        return self.run(question, sender, at)

    def run(self, question, sender, at) -> str:
        # 先获取服务器当前时间
        current_time = datetime.now().astimezone()
        # 如果用户是utc, 那么当前时间变成uat+8时间
        if at in config.REMAINDER.get("utc+8", []):
            tz = pytz.timezone('Asia/Shanghai')
            current_time = current_time.astimezone(tz)
        # 那当前时间 解析出下次提醒时间
        parsed_list = Time(current_time).parse(question + '0秒')
        self.LOG.info("执行提醒时间解析, 得到结果:[%s]", parsed_list)
        try:
            # 解析时间
            parsed_time = parsed_list[0].get("keyDate")
            # 将时间字符串转换为datetime对象
            reminder_time = datetime.strptime(parsed_time, TIME_FORMAT).replace(tzinfo=current_time.tzinfo)
            # 判断提醒时间是否比当前更小
            if current_time > reminder_time:
                self.LOG.warning("用户设定的提醒时间 小于当前时间")
                raise ValueError
            scheduler.add_job(self.send_reminder, 'date', run_date=reminder_time, args=[question, sender, at],
                              name=f"{at}-{question}")
        except Exception as e:
            self.LOG.error("执行提醒时间失败", e)
            return "设置提醒失败, 请重新检查表述是否包含有效时间"
        return f"设置提醒成功, 将会在本地时间{[str(reminder_time)]}进行消息提醒"

    def send_reminder(self, content, sender, at):
        self.LOG.info("开始收到延迟执行消息, content:%s, sender:%s, at:%s", content, sender, at)
        base_client.send_text(sender, at, content)

    def get_reminder_by_send(self, sender):
        jobs = scheduler.get_jobs()
        result = []
        for job in jobs:
            wix_job = job.name.split("-")
            if sender == wix_job[0]:
                result.append(f"{wix_job[1]}-[{job.next_run_time}]-{job.id}")
        return json.dumps(result, indent=4)

    def remove_reminder_by_id(self, id):
        jobs = scheduler.get_jobs()
        for job in jobs:
            wix_job = job.name.split("-")
            if id == job.id:
                job.remove()
                return f"取消提醒成功, {wix_job[1]}-[{job.next_run_time}]不再提醒"
        return "取消提醒失败, 没有找到这个id"


if __name__ == "__main__":
    q = input(">>> ")
    reminder = TrigRemainderHandler()
    print(reminder.run(q, "234", "123"))
    print(reminder.run(q, "234", "123"))
    print(reminder.get_reminder_by_send("123"))
    while True:
        time.sleep(1)
