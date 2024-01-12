from configuration import Config
from models.wx_msg import WxMsgServer
from msg_handler import MsgHandler
config = Config()


def router_msg(msg: WxMsgServer) -> str:
    # 群聊消息
    if msg.from_group():
        # 不在配置的响应的群列表里，忽略
        if msg.roomid not in config.GROUPS:
            return ""
        # 被@ 才处理
        if msg.is_at(config.BASE_SERVER.get("wxid", "")):
            return MsgHandler.handler_msg(msg)
        # 如果没有被at 忽略
        return ""

    # 文本消息 默认都处理
    elif msg.type == 0x01:
        MsgHandler.handler_msg(msg)

    # 好友请求
    if msg.type == 37:  # 好友请求
        pass
        # self.autoAcceptFriendRequest(msg)

    # 系统信息
    elif msg.type == 10000:  # 系统信息
        pass
        # self.sayHiToNewFriend(msg)
    return ""
