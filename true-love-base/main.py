import signal
import time

from wcferry import Wcf

import server
from configuration import Config
from robot import Robot
from wcf_utils import WcfUtils

config = Config()


# 打开并读取XML文件
def load_xml_as_string(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        xml_string = file.read()
    return xml_string


def main():
    # 启动wcf
    wcf = Wcf(debug=True)

    # 设置信号被杀的回调
    def handler(sig, frame):
        # 退出前清理环境
        wcf.send_text("真爱粉base正在关闭...", config.master_wix)
        wcf.cleanup()
        exit(0)

    signal.signal(signal.SIGINT, handler)

    # 启动机器人
    robot = Robot(wcf)
    robot.send_text_msg("真爱粉base启动成功...", config.master_wix)
    # 启动接受消息
    robot.enable_receiving_msg()
    # 启动http服务
    server.enable_http(robot)
    # 加载小助手
    WcfUtils(wcf)
    wcf.send_xml(config.master_wix, load_xml_as_string('music.xml'), 3)
    # 让服务保持不关闭
    while True:
        time.sleep(1)


if __name__ == '__main__':
    main()
