import signal

import base_client
import server
from configuration import Config


def notice_master():
    # 启动的通知
    base_client.send_text("master", "", "真爱粉server启动成功...")

    # 设置信号被杀的回调
    def handler(sig, frame):
        # 退出前清理环境
        base_client.send_text("master", "", "真爱粉server正在关闭...")
        exit(0)

    signal.signal(signal.SIGINT, handler)


def main():
    # notice master
    notice_master()
    # 启动http 这个留到最后启动 保活进程
    server.enable_http()


if __name__ == '__main__':
    config = Config()
    main()
