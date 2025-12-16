# -*- coding: utf-8 -*-
"""
Job Management - 定时任务管理

提供定时任务的注册和调度功能。
"""

import time
from threading import Thread
from typing import Any, Callable

import schedule

from . import job_process


class Job(object):

    def on_every_seconds(self, seconds: int, task: Callable[..., Any], *args, **kwargs) -> None:
        """
        每 seconds 秒执行
        :param seconds: 间隔，秒
        :param task: 定时执行的方法
        :return: None
        """
        schedule.every(seconds).seconds.do(task, *args, **kwargs)

    def on_every_minutes(self, minutes: int, task: Callable[..., Any], *args, **kwargs) -> None:
        """
        每 minutes 分钟执行
        :param minutes: 间隔，分钟
        :param task: 定时执行的方法
        :return: None
        """
        schedule.every(minutes).minutes.do(task, *args, **kwargs)

    def on_every_hours(self, hours: int, task: Callable[..., Any], *args, **kwargs) -> None:
        """
        每 hours 小时执行
        :param hours: 间隔，小时
        :param task: 定时执行的方法
        :return: None
        """
        schedule.every(hours).hours.do(task, *args, **kwargs)

    def on_every_days(self, days: int, task: Callable[..., Any], *args, **kwargs) -> None:
        """
        每 days 天执行
        :param days: 间隔，天
        :param task: 定时执行的方法
        :return: None
        """
        schedule.every(days).days.do(task, *args, **kwargs)

    def on_every_time(self, times: Any, task: Callable[..., Any], *args, **kwargs) -> None:
        """
        每天定时执行
        :param times: 时间字符串列表，格式:
            - For daily jobs -> HH:MM:SS or HH:MM
            - For hourly jobs -> MM:SS or :MM
            - For minute jobs -> :SS
        :param task: 定时执行的方法
        :return: None

        例子: times=["10:30", "10:45", "11:00"]
        """
        if not isinstance(times, list):
            times = [times]

        for t in times:
            schedule.every(1).days.at(t).do(task, *args, **kwargs)

    def async_enable_jobs(self):
        Thread(target=self.enable_jobs, name="enableJobs", daemon=True).start()

    @staticmethod
    def enable_jobs() -> None:
        while True:
            schedule.run_pending()
            time.sleep(1)


# 导入这个包的时候,就会把这里的代码都执行一遍
daytime_list = ["10:00", "10:30", "11:00", "11:30", "12:00", "12:30", "13:00", "13:30", "14:00", "14:30", "15:00",
                "15:30", "16:00", "16:30", "17:00", "17:30", "18:00", "18:30", "19:00", "19:30", "20:00", "20:30",
                "21:00", "21:30", "22:00"]
job = Job()
# job.on_every_time(daytime_list, job_process.notice_mei_yuan)
# job.on_every_time("07:00", job_process.notice_library_schedule)
# job.on_every_time("20:00", job_process.async_download_zao_bao_file)
# job.on_every_time("20:01", job_process.async_download_moyu_file)
# job.on_every_time("20:05", job_process.notice_moyu_schedule)
# job.on_every_time("20:08", job_process.notice_usa_moyu_schedule)

# job.on_every_time("22:00", job_process.notice_card_schedule)
