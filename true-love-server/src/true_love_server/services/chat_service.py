# -*- coding: utf-8 -*-
"""
Chat Service - 聊天服务

处理 AI 聊天相关的业务逻辑。
"""

import logging
import random

from . import base_client
from .ai_client import AIClient

LOG = logging.getLogger("ChatService")


def process_ban(sender: str) -> str:
    """处理被禁言用户的固定回复"""
    if sender == 'Dante516':
        advice_list = [
            "大野猫,我们应该尊重这个群体,避免发送任何令人反感的言论。",
            "大野猫,那种言语可能会冒犯或伤害他人,希望你能三思而行。",
            "我理解每个人都有自己的私密空间,但请不要在公共场合发这种内容。",
            "作为群友,我建议你寻求专业的心理咨询,释放内心的压力。",
            "让我们共同维护这个群体的和谐氛围,互相尊重。",
            "这种言语可能会给人一种性骚扰的感觉,我希望大野猫哥你能改正。",
            "我相信大野猫是一个善良的人,只是暂时失去了分寸。",
            "用文字表达想法时,请三思而后行,避免伤害他人。",
            "作为朋友,我愿意倾听你的烦恼,但请不要以这种方式发泄。",
            "让我们携手共创一个积极向上、互相尊重的良好环境。"
        ]
        return random.choice(advice_list)
    return ''


class ChatService:
    """
    聊天服务
    
    处理普通文本聊天的 AI 交互。
    """
    
    def __init__(self):
        self.ai_client = AIClient()
    
    def get_answer(self, question: str, wxid: str, sender: str) -> None:
        """
        获取 AI 回答并发送
        
        Args:
            question: 问题内容
            wxid: 会话 ID
            sender: 发送者
        """
        # 处理被禁言用户
        rsp = process_ban(sender)
        # 私聊时不@（wxid == sender 表示私聊）
        at_user = sender if wxid != sender else ""
        
        if rsp != '':
            base_client.send_text(wxid, at_user, rsp)
            return
        
        # 调用 AI 服务
        result = self._get_answer_type(question, wxid, sender)
        
        # 根据返回类型分发处理
        if 'type' in result and result['type'] == 'gen-img':
            # 导入避免循环依赖
            from .image_service import ImageService
            ImageService().async_generate(
                f"user_input:{question}, supplementary:{result['answer']}",
                wxid,
                sender
            )
            return
        
        if 'type' in result and result['type'] == 'wechat-qr':
            # 处理微信扫码连通道请求
            import json
            try:
                qr_data = json.loads(result['answer'])
                qr_url = qr_data.get('qrDataUrl')
                message = qr_data.get('message', "使用微信扫描以下二维码，以完成领养。")
                
                if qr_url:
                    # 获取文件名并生成二维码
                    from .ai_client import get_file_path
                    import time
                    import qrcode
                    temp_msg_id = f"qr_{int(time.time())}"
                    file_path = get_file_path(temp_msg_id)
                    
                    try:
                        # 使用 QRCode 类以获得更好的控制
                        qr = qrcode.QRCode(
                            version=1,
                            error_correction=qrcode.constants.ERROR_CORRECT_L,
                            box_size=10,
                            border=4,
                        )
                        qr.add_data(qr_url)
                        qr.make(fit=True)
                        
                        # 生成图片并强制转换为 RGB 格式，确保兼容性
                        img = qr.make_image(fill_color="black", back_color="white").convert('RGB')
                        img.save(file_path)
                        
                        # 转换并发送图片路径
                        win_path = file_path.replace('/', '\\')
                        # 先发提示语
                        base_client.send_text(wxid, at_user, message)
                        # 再发送图片
                        base_client.send_img(win_path, wxid)
                        return
                    except Exception as ge:
                        LOG.error(f"本地生成二维码失败: {ge}")
                        base_client.send_text(wxid, at_user, "呜呜，我本想给你画个二维码的，但是笔断了捏，稍后再试试吧~")
                        return
                else:
                    base_client.send_text(wxid, at_user, "呜呜，连接服务没排期，稍后再试试吧~")
                    return
            except Exception as e:
                LOG.error(f"处理 wechat-qr 响应失败: {e}")
                base_client.send_text(wxid, at_user, "呀~处理连接请求出错了，稍后再试试吧~")
                return

        if 'type' in result and result['type'] == 'gen-video':
            from .video_service import VideoService
            VideoService().async_generate(
                f"user_input:{question}, supplementary:{result['answer']}",
                wxid,
                sender
            )
            return
            
        if 'type' in result and result['type'] == 'analyze-speech':
            # 异步处理以免阻塞消息循环
            from concurrent.futures import ThreadPoolExecutor
            _executor = ThreadPoolExecutor(max_workers=5)
            _executor.submit(self._handle_analyze_speech, result['answer'], wxid, sender)
            return
        
        # 普通聊天回复
        rsp = result.get('answer', '')
        if 'debug' in result:
            rsp = rsp + '\n\n' + str(result['debug']).replace('$', str(result.get('ioCost', '')))
        
        base_client.send_text(wxid, at_user, rsp)
    
    def _get_answer_type(self, question: str, wxid: str, sender: str) -> dict:
        """
        获取回答及类型
        
        Returns:
            dict: 包含 type, answer, ioCost 等字段
        """
        LOG.info("开始发送给 get_answer_type")
        
        response = self.ai_client.get_llm(question, wxid, sender)
        
        if not response.success:
            return {"type": "chat", "answer": response.error_msg}
        
        result = response.data if isinstance(response.data, dict) else {"type": "chat", "answer": response.data}
        result["ioCost"] = str(response.io_cost)
        
        LOG.info("get_answer_type 回答时间为：%ss, result: %s", response.io_cost, result)
        return result

    def _handle_analyze_speech(self, target: str, wxid: str, sender: str) -> None:
        """
        在 Server 端处理发言分析请求
        包含：发安抚语 -> 查 DB -> 请求 AI 端汇总分析 -> 发送结果回群
        """
        at_user = sender if wxid != sender else ""
        
        # 1. 甄别分析目标
        if not target or len(target) > 30:
            target = "self"
            
        if ',' in target or '，' in target:
            base_client.send_text(wxid, at_user, "我现在还不能同时分析多个人哦，麻烦@你最想放的那个人试试吧~")
            return
            
        is_self = target.strip().lower() == 'self'
        target_person = sender if is_self else target.strip()
        
        # 设置展示名字，防止带有@符号
        display_name = target_person.strip('@').strip()
        target_person_query = display_name
        
        # 2. 发送安抚语
        wait_msgs = [
            f"正在戴上老花镜，翻阅[{display_name}]在群里所有的发言，请稍等哈...",
            f"收到！正在在群里扒[{display_name}]的黑历史，稍微等我一下哦~",
            f"正在检索[{display_name}]最近的发言数据，看我稍后怎么评价...",
            f"好滴，我正在连夜读[{display_name}]的群聊消息，等我出个报告！"
        ]
        base_client.send_text(wxid, at_user, random.choice(wait_msgs))
        
        # 3. 查询数据库
        from ..core.db_engine import SessionLocal
        from ..services.group_message_repository import GroupMessageRepository
        
        history = []
        try:
            with SessionLocal() as db:
                repo = GroupMessageRepository(db)
                history = repo.get_recent_messages(chat_id=wxid, sender=target_person_query, limit=100)
        except Exception as e:
            LOG.error(f"查询发言历史报错: {e}")
            
        if not history:
            base_client.send_text(wxid, at_user, f"我没能获取到[{display_name}]在群里以前的发言记录哦，所以我没有足够的信息来分析捏~")
            return
            
        # 4. 组装并发送给 AI 端
        speech_history_text = "\n".join([f"[{item['created_at']}] {item['content']}" for item in history])
        LOG.info(f"查到 [{display_name}] 的 {len(history)} 条记录，开始跨 RPC 请求 AI...")
        
        prompt_target = f"分析群成员 {display_name} 的发言特点、性格或意图" if not is_self else "分析这位用户的发言特点、性格或意图"
        response = self.ai_client.analyze_speech(prompt_target, speech_history_text, wxid)
        
        # 4. 接收报告并发送
        if not response.success:
            base_client.send_text(wxid, at_user, response.error_msg)
            return
            
        final_answer = response.data.get('answer', '啊哦，分析结果没拿到~') if isinstance(response.data, dict) else response.data
        base_client.send_text(wxid, at_user, final_answer)
