from configuration import Config
from models.wx_msg import WxMsgServer
from msg_handler import MsgHandler

config = Config()
msg_handler = MsgHandler()


def router_msg(msg: WxMsgServer) -> str:
    # 如果是来自群的消息
    if msg.from_group():
        # 如果不是全放的话, 不在配置的响应的群列表里，忽略
        if not config.GROUPS.get("all_allow") and msg.roomid not in config.GROUPS.get("allow_list", []):
            return ""
        # 被@ 才处理, 默认处理全部类型消息, 内部判断返回值
        if msg.is_at(config.BASE_SERVER.get("self_wxid", "")) or '@真爱粉' in msg.content or 'zaf' in msg.content:
            return msg_handler.handler_msg(msg)
        # 如果没有被at 忽略
        return ""

    # 好友请求
    if msg.type == 37:
        pass
        # self.autoAcceptFriendRequest(msg)

    # 系统信息
    elif msg.type == 10000:
        pass
        # self.sayHiToNewFriend(msg)

    # 走到这里大概率是私聊消息, 没在配置都忽略
    if not config.PRIVATES.get("all_allow") and msg.roomid not in config.PRIVATES.get("allow_list", []):
        return ""
    # 默认走消息处理
    return msg_handler.handler_msg(msg)
