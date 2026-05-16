"""
消息处理服务
学习和回复是两套独立的流程
"""
import os
import time
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any
from joha.ai.generator import generator
from joha.core.builders.message_builder import message_builder
from joha.ai.bot import get_ai_bot
from joha.decision.command_analyzer import command_analyzer
from joha.decision.tools import SearchTool, WebpageTool, kb_search_tool
from joha.managers.history_manager import history_manager
from joha.managers.style_learner import style_learner
from joha.config.infrastructure.logger import johalog_logger, ai_logger, tprint
from joha.config.managers.config_manager import config
from joha.config.managers.group_mode_config import group_mode_config
from joha.decision.reply_decision import should_reply, compute_reply_prob, build_context
from joha.decision.cooldown import cooldown_manager
from joha.decision.knowledge.base import get_knowledge_base


# ==================== 多模态能力检测 ====================

MULTIMODAL_MODEL_PREFIXES = (
    "gpt-4o", "gpt-4-vision", "gpt-4-turbo",
    "claude-3", "claude-3.5", "claude-3.7",
    "gemini-1.5", "gemini-2", "gemini-2.5",
    "qwen-vl", "qwen2-vl", "qwen2.5-vl", "qwen3-vl",
    "qwen-omni", "qwen3.5-omni",
    "glm-4v", "cogvlm", "cogagent",
    "yi-vision", "yi-vl",
    "internvl", "internlm-xcomposer",
    "llava", "bakllava", "llama3.2-vision", "llama-3.2-vision",
    "pixtral", "deepseek-vl",
)


def supports_multimodal(model_name: str) -> bool:
    model_lower = model_name.lower()
    return any(model_lower.startswith(prefix.lower()) for prefix in MULTIMODAL_MODEL_PREFIXES)


# ==================== 工具函数 ====================

def get_latest_json_file() -> str | None:
    """获取最近一次生成的 JSON 分片文件路径"""
    try:
        txt_dir = os.path.join(os.path.dirname(__file__), "..", "storage", "txt")
        if not os.path.exists(txt_dir):
            return None
        
        files = [f for f in os.listdir(txt_dir) if f.startswith('knowledge_') and f.endswith('.json')]
        if not files:
            return None
        
        files.sort(reverse=True)
        latest_file = os.path.join(txt_dir, files[0])
        return latest_file
    except Exception as e:
        tprint("error", f"[获取最新记录] 错误：{e}")
        return None


def save_conversation(question: str, response: str):
    """保存对话记录到知识库（使用结构化 JSON 格式）"""
    try:
        # 直接添加到知识库，由 KnowledgeBase 统一管理分片存储
        from joha.decision.knowledge.base import get_knowledge_base
        
        kb = get_knowledge_base()
        kb.add_document(
            question=question,
            response=response,
            title=question[:50],
        )
        
        tprint("info", f"[保存记录] 成功：已添加到知识库分片")
        
    except Exception as e:
        tprint("error", f"[保存记录] 错误：{e}")


class MessageService:
   
    
    def __init__(self):
        self.mode = config.get('bot.mode', 'passive')
        self.started_at = time.time()
        self.total_messages = 0
        self.learned_messages = 0
        self.reply_decisions = 0
        self.skipped_replies = 0
        self.generated_replies = 0
        self.failed_replies = 0
        
        # 初始化知识库
        self.knowledge_base = get_knowledge_base()
        message_builder.knowledge_base = self.knowledge_base
        johalog_logger.info(f"已加载 {len(self.knowledge_base.get_all_documents())} 个知识库文档")
        
        self.group_modes: Dict[str, str] = group_mode_config.get_all_modes()
        johalog_logger.info(f"已初始化 {len(self.group_modes)} 个群组模式")

    async def process_message(
        self,
        userid: str,
        message: str,
        group_id: Optional[str] = None,
        force_reply: bool = False,
        is_at_bot: bool = False,
        reply_to_bot: bool = False,
        is_pure_sticker_or_image: bool = False,
        images: list = None,
    ) -> Optional[str]:
        """
        处理消息 - 学习和回复分离
        
        Args:
            userid: 用户 ID
            message: 消息内容
            group_id: 群 ID（可选）
            force_reply: 是否强制回复
            is_at_bot: 是否@机器人
            reply_to_bot: 是否回复机器人消息
            is_pure_sticker_or_image: 是否为纯表情/贴纸/图片
            images: 图片 base64 data URL 列表（多模态用）
        
        Returns:
            回复内容或 None
        """
        userid_str = str(userid)
        message = message.strip()
        images = images or []
        
        if not message and not images:
            return None
        
        self.total_messages += 1
        log_msg = message if message else f"[图片 x{len(images)}]"
        ai_logger.info(f"收到消息", extra={"userid": userid_str, "msg_content": log_msg})
        tprint("info", f"[消息] 群{group_id} | 用户{userid_str}: {log_msg}")
        
        group_mode = self.get_group_mode(group_id) if group_id else self.get_global_mode()
        should_generate_reply = group_mode == "active" or force_reply
        learn_msg = message if message else f"[用户发送了一张图片]"
        
        if should_generate_reply:
            # 使用 build_context 自动填充群组动态特征
            ctx = build_context(
                text=log_msg,
                user_id=userid_str,
                group_id=group_id or "",
                is_at_bot=is_at_bot,
                reply_to_bot=reply_to_bot,
                is_pure_media=is_pure_sticker_or_image,
            )
            prob = compute_reply_prob(ctx, cooldown_manager)
            decision = should_reply(ctx, cooldown_manager)
            self.reply_decisions += 1
            tprint("info",
                f"[决策] 概率={prob:.3f} | 阈值={ctx.group_msg_per_minute:.1f}msg/min | "
                f"意图={ctx.intent} | {'✅ 回复' if decision else '❌ 跳过'}"
            )
            johalog_logger.debug(
                f"[回复决策] 概率={prob:.3f}, 意图={ctx.intent}, "
                f"决策={'✅回复' if decision else '❌不回复'}"
            )
            if not decision:
                self.skipped_replies += 1
                self._learn_message(userid_str, learn_msg, group_id)
                return None
            return await self._handle_active_mode(userid_str, message, images, group_id)
        else:
            self._learn_message(userid_str, learn_msg, group_id)
            return None
    
    def _learn_message(self, userid_str: str, message: str, group_id: Optional[str] = None) -> None:
        try:
            history_manager.add_message(userid_str, message, "", group_id=group_id)
            style_learner.learn_from_message(userid_str, message)
            self.learned_messages += 1
            
            johalog_logger.debug(f"[学习] 记录用户 {userid_str} 的消息并学习风格")
        except Exception as e:
            johalog_logger.error(f"学习失败：{e}")
    
    async def _handle_active_mode(
        self,
        userid_str: str,
        message: str,
        images: list = None,
        group_id: Optional[str] = None,
    ) -> Optional[str]:
        """回复流程：主动模式生成回复（支持图片多模态 + RAG 知识库检索）"""
        try:
            images = images or []

            if images:
                current_model = getattr(get_ai_bot(), 'model', generator.current_model)
                if not supports_multimodal(current_model):
                    tprint("warning", f"[多模态] 模型 {current_model} 不支持图片，已跳过 {len(images)} 张图片")
                    johalog_logger.warning(f"模型 {current_model} 不支持多模态，已跳过图片")
                    images = []
            # 获取历史记录
            history = history_manager.load_history(userid_str, group_id=group_id)

            # 使用统一消息构建器
            context_messages = message_builder.build(
                user_id=userid_str,
                message=message,
                images=images,
                persona_name="joha",
                history=history,
                include_style=True,
                include_rag=True,
                group_id=group_id,
            )

            # 调用LLM生成回复（支持自然语言指令解析）
            log_msg = message[:30] if message else f"[图片]"
            tprint("info", f"[AI] 请求中... | 用户{userid_str} | 消息: {log_msg}{'...' if len(message) > 30 else ''}")
            
            # 1. 命令分析：判断是否需要调工具
            analysis = command_analyzer.analyze(message)
            response = None
            
            if analysis['action'] == 'search':
                tprint("info", f"[工具] 触发搜索: {analysis['query']}")
                search_tool = SearchTool()
                response = f"🔍 搜索结果：\n{search_tool.search(analysis['query'])}"
            elif analysis['action'] == 'knowledge':
                tprint("info", f"[工具] 触发知识库: {analysis['query']}")
                response = f"📚 记忆检索：\n{kb_search_tool.search(analysis['query'])}"
            elif analysis['action'] == 'webpage':
                import re
                urls = re.findall(r'http[s]?://\S+', message)
                if urls:
                    tprint("info", f"[工具] 触发网页抓取: {urls[0]}")
                    webpage_tool = WebpageTool()
                    response = f"🌐 网页摘要：\n{webpage_tool.fetch(urls[0])}"
            
            # 2. 如果没触发工具，或者工具返回为空，则进行普通聊天
            if not response:
                try:
                    ai_bot = get_ai_bot()
                    response = await asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda: ai_bot.chat(message, temperature=0.7)
                    )
                except Exception as bot_err:
                    tprint("warning", f"[AIBot] 失败，回退到生成器: {bot_err}")
                    response = await generator.chat(
                        messages=context_messages,
                        temperature=0.7,
                        max_tokens=1024,
                    )
            if not response:
                self.failed_replies += 1
                tprint("warning", f"[AI] 未生成回复，已跳过发送到群 | 用户{userid_str} | 消息: {log_msg}")
                johalog_logger.warning(
                    f"[回复生成失败] 用户:{userid_str}, 消息:{log_msg[:20]}..., 已跳过群发送"
                )
                return None

            tprint("info", f"[AI] 回复: {response}")
            
            johalog_logger.info(
                f"[回复生成] 用户:{userid_str}, 消息:{log_msg[:20]}..., 回复:{response[:20]}..."
            )
            
            # 记录回复到历史
            history_manager.add_message(userid_str, message or "[图片]", response, group_id=group_id)
            
            self.generated_replies += 1
            return response
        
        except Exception as e:
            self.failed_replies += 1
            johalog_logger.error(f"生成回复失败：{e}", exc_info=True)
            tprint("error", f"[AI] 生成回复失败，已跳过发送到群：{e}")
            return None
    
    def get_global_mode(self) -> str:
        """获取全局模式"""
        config.load()
        mode = config.get('bot.mode', self.mode)
        if mode not in ["active", "passive"]:
            return self.mode
        self.mode = mode
        return mode

    def set_global_mode(self, mode: str) -> None:
        """设置全局模式"""
        if mode not in ["active", "passive"]:
            raise ValueError(f"无效的模式: {mode}")
        config.load()
        config.set('bot.mode', mode)
        config.save()
        self.mode = mode

    def get_group_mode(self, group_id: str) -> str:
        """获取群组模式"""
        return group_mode_config.get_mode(group_id, self.get_global_mode())
    
    def set_group_mode(self, group_id: str, mode: str) -> None:
        """设置群组模式"""
        if mode not in ["active", "passive"]:
            raise ValueError(f"无效的模式: {mode}")
        
        group_mode_config.set_mode(group_id, mode)
        self.group_modes = group_mode_config.get_all_modes()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取服务统计信息"""
        uptime = int(time.time() - self.started_at)
        from joha.decision.group_state import group_state_manager
        gs = group_state_manager.get_stats()
        return {
            "uptime": uptime,
            "total_messages": self.total_messages,
            "learned_messages": self.learned_messages,
            "reply_decisions": self.reply_decisions,
            "skipped_replies": self.skipped_replies,
            "generated_replies": self.generated_replies,
            "failed_replies": self.failed_replies,
            "active_groups": len([g for g, m in self.group_modes.items() if m == "active"]),
            "passive_groups": len([g for g, m in self.group_modes.items() if m == "passive"]),
            "tracked_groups": gs["total_groups"],
            "group_total_messages": gs["total_messages"],
            "group_bot_replies": gs["total_bot_replies"],
            "avg_msg_per_min": round(gs["avg_msg_per_min"], 1),
        }
    
    def get_stats_str(self) -> str:
        """获取统计信息字符串"""
        stats = self.get_stats()
        return (
            f"=== Joha 服务统计 ===\n"
            f"运行时间: {stats['uptime']} 秒\n"
            f"收到消息: {stats['total_messages']}\n"
            f"学习消息: {stats['learned_messages']}\n"
            f"回复决策: {stats['reply_decisions']}\n"
            f"生成回复: {stats['generated_replies']}\n"
            f"跳过回复: {stats['skipped_replies']}\n"
            f"失败回复: {stats['failed_replies']}\n"
            f"活跃群组: {stats['active_groups']}\n"
            f"被动群组: {stats['passive_groups']}\n"
            f"追踪群组: {stats['tracked_groups']}\n"
            f"群总消息: {stats['group_total_messages']}\n"
            f"知识库文档数: {len(self.knowledge_base.get_all_documents())}\n"
            f"=================="
        )
    
    def refresh_knowledge_base(self) -> int:
        """刷新知识库，重新加载所有文档"""
        self.knowledge_base.refresh()
        count = len(self.knowledge_base.get_all_documents())
        johalog_logger.info(f"知识库已刷新，当前文档数: {count}")
        return count


# 全局服务实例
message_service = MessageService()