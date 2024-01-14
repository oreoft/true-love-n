import signal

import base_client
import job_mgmt
import server
from configuration import Config


def notice_master():
    # 启动的通知
    base_client.send_text(config.BASE_SERVER.get("master_wxid"), "", "真爱粉server启动成功...")

    # 设置信号被杀的回调
    def handler(sig, frame):
        # 退出前清理环境
        base_client.send_text(config.BASE_SERVER.get("master_wxid"), "", "真爱粉server正在关闭...")
        exit(0)

    signal.signal(signal.SIGINT, handler)


def main():
    # notice master
    notice_master()
    # 注册并且 异步启动定时任务
    job = job_mgmt.Job()
    job.async_enable_jobs()
    # 启动http 这个留到最后启动 保活进程
    server.enable_http()


if __name__ == '__main__':
    config = Config()
    main()
