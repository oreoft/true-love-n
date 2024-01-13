from configuration import Config
from models.wx_msg import WxMsgServer
from msg_handler import MsgHandler

config = Config()


def router_msg(msg: WxMsgServer) -> str:
    # 群聊消息
    msg_handler = MsgHandler()
    if msg.from_group():
        # 如果不是全放的话, 不在配置的响应的群列表里，忽略
        if not config.GROUPS.get("all_allow") and msg.roomid not in config.GROUPS.get("allow_list", []):
            return ""
        # 被@ 才处理
        if msg.is_at(config.BASE_SERVER.get("self_wxid", "")):
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
