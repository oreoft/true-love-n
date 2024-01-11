import signal

from wcferry import Wcf

import server
from robot import Robot


def main():
    # 启动wcf
    wcf = Wcf(debug=True)

    # 设置信号被杀的回调
    def handler(sig, frame):
        # 退出前清理环境
        wcf.cleanup()
        exit(0)

    signal.signal(signal.SIGINT, handler)

    # 启动机器人
    robot = Robot(wcf)
    robot.send_text_msg("真爱粉启动成功...", "wxid_tqn5yglpe9gj21")
    robot.enable_receiving_msg()
    # 启动http服务
    server.enable_http(robot)


if __name__ == '__main__':
    from configuration import Config
    Config()
    main()
