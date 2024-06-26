import re

from configuration import Config
from models.wx_msg import WxMsgServer
from msg_handler import MsgHandler

config = Config()


def router_msg(msg: WxMsgServer) -> str:
    # 群聊消息
    msg_handler = MsgHandler()
    # 引用消息
    if msg.type == 49:
        # 提取<title>
        title_search = re.search(r'<title>(.*?)</title>', msg.content)
        title = title_search.group(1) if title_search else ""

        # 提取<content>
        content_search = re.search(r'<content>(.*?)</content>', msg.content, re.DOTALL)
        content = content_search.group(1) if content_search else ""

        # 保证提取的由内容
        if title != "" and content != "" and '?xml' not in content:
            # 如果是群,但是没有艾特
            if msg.from_group() and (
                    not msg.is_at(config.BASE_SERVER.get("self_wxid", "")) and '@真爱粉' not in msg.content):
                return ""
            msg.content = f"{title}, quoted content:{content}"
            return msg_handler.handler_msg(msg)
        return "啊哦~引用内容我暂时看不懂哦, 不如你把内容复制出来给我看看呢"

    if msg.from_group():
        # 如果不是全放的话, 不在配置的响应的群列表里，忽略
        if not config.GROUPS.get("all_allow") and msg.roomid not in config.GROUPS.get("allow_list", []):
            return ""
        # 被@ 才处理
        if msg.is_at(config.BASE_SERVER.get("self_wxid", "")) or '@真爱粉' in msg.content:
            return msg_handler.handler_msg(msg)
        # 如果没有被at 忽略
        return ""

    # 文本消息 默认都处理
    elif msg.type == 0x01:
        # 如果不是全放的话, 不在配置的响应的人列表里，忽略
        if not config.PRIVATES.get("all_allow") and msg.roomid not in config.PRIVATES.get("allow_list", []):
            return ""
        return msg_handler.handler_msg(msg)

    # 好友请求
    if msg.type == 37:
        pass
        # self.autoAcceptFriendRequest(msg)

    # 系统信息
    elif msg.type == 10000:
        pass
        # self.sayHiToNewFriend(msg)
    return ""
