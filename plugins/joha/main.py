"""
Joha 插件 - 智能聊天机器人 (rqhbot 插件规范适配版)

将原有 ncatbot 独立的 joha 机器人适配为 rqhbot 的 PluginBase 规范插件。
核心逻辑（AI 对话、回复决策、风格学习、知识库等）完全复用 joha 原有模块。
"""
import sys
import logging
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

# ========== 包路径注入 ==========
# 将 plugins/ 加入 sys.path，使 from joha.xxx import yyy 能正确解析
_JOHA_PARENT = str(Path(__file__).resolve().parent.parent)  # plugins/
if _JOHA_PARENT not in sys.path:
    sys.path.insert(0, _JOHA_PARENT)

# ========== rqhbot SDK 导入 ==========
from sdk.pluginsystem import PluginBase, group_message, private_message
from sdk.core.events import GroupMessageEvent, PrivateMessageEvent
from sdk.core.interfaces import IBotAPI
from sdk.core.event_bus import EventBus

# ========== joha 核心模块导入 ==========
# 注意：直接导入具体模块，避免触发 core/handlers/__init__.py (依赖 ncatbot)
from joha.core.handlers.service import message_service
from joha.core.handlers.commands import command_handler, normalize_fallback_command
from joha.core.builders.message_queue import message_queue_manager
from joha.core.utils.runtime_context import runtime_context
from joha.decision.group_state import group_state_manager
from joha.config.infrastructure.logger import johalog_logger, tprint
from joha.config.managers.config_manager import config as joha_config

logger = logging.getLogger(__name__)


# ==================== API 适配器 ====================

class BotAPIAdapter:
    """将 rqhbot 的 IBotAPI 适配为 joha 命令处理器期望的接口

    joha 的 command_handler.handle_command() 内部调用
    bot_api.post_group_msg(group_id, text) 发送回复，
    此适配器将其桥接到 self.api.send_group_message()。
    """

    def __init__(self, api: IBotAPI) -> None:
        self._api = api

    async def post_group_msg(self, group_id: int, text: str) -> None:
        """发送群消息（joha 命令处理器兼容接口）"""
        await self._api.send_group_message(int(group_id), text)

    async def post_private_msg(self, user_id: int, text: str) -> None:
        """发送私聊消息（joha 命令处理器兼容接口）"""
        await self._api.send_private_message(int(user_id), text)

    def __getattr__(self, name: str) -> Any:
        """代理其他 IBotAPI 方法"""
        return getattr(self._api, name)


# ==================== 消息工具函数 ====================

def extract_images_from_rqhbot_event(event: GroupMessageEvent) -> List[str]:
    """从 rqhbot 群消息事件中提取图片 base64 data URL

    Args:
        event: rqhbot 群消息事件

    Returns:
        base64 data URL 列表
    """
    image_urls: List[str] = []
    for seg in event.message.segments:
        if seg.get("type") == "image":
            data = seg.get("data", {})
            file_name = data.get("file", "")
            # 尝试从 file 字段提取 base64（NapCat 格式）
            if file_name and file_name.startswith("base64://"):
                b64 = file_name[len("base64://"):]
                image_urls.append(f"data:image/jpeg;base64,{b64}")
                continue
            # 尝试从 url 字段获取
            url = data.get("url", "")
            if url:
                image_urls.append(url)
    return image_urls


# ==================== 插件主类 ====================

class JohaPlugin(PluginBase):
    """Joha 智能聊天机器人插件

    功能：
    - AI 对话（支持多 Provider 切换）
    - 智能回复决策（概率 + 场景阈值判断）
    - 风格学习
    - 知识库（RAG）
    - 工具调用（搜索、网页抓取）
    - 人设管理
    """

    def __init__(self) -> None:
        super().__init__()
        self.name = "Joha"
        self.version = "1.0.0"
        self.description = "智能聊天机器人，支持 AI 对话、风格学习、知识库、工具调用"
        self.author = "Joha Team"
        self._bot_api_adapter: Optional[BotAPIAdapter] = None

    # ==================== 生命周期 ====================

    async def on_load(
        self,
        api: IBotAPI,
        event_bus: EventBus,
        plugin_dir: Optional[Path] = None,
    ) -> None:
        """插件加载：初始化 API 适配器、bot_uin、配置文件等"""
        await super().on_load(api, event_bus, plugin_dir)
        self._bot_api_adapter = BotAPIAdapter(api)

        # 1. 确保 joha 的 config.json 存在
        self._ensure_config_exists(plugin_dir)

        # 2. 设置机器人 QQ 号
        self._setup_bot_uin()

        # 3. 重新加载 joha 配置（如果刚创建了 config.json）
        joha_config.load()

        logger.info(f"Joha 插件 v{self.version} 加载成功 — bot_uin={runtime_context.bot_uin}")

    # ==================== 内部初始化 ====================

    def _ensure_config_exists(self, plugin_dir: Optional[Path]) -> None:
        """确保 joha 的 config.json 存在，不存在则从 config.example.json 复制

        joha 的 ConfigManager(默认) 在 config/managers/ 下寻找 config.json。
        这里同时在 managers/ 目录和 config/ 目录创建，确保兼容。
        """
        if plugin_dir is None:
            return

        # joha 期望的位置：plugins/joha/config/managers/config.json
        managers_dir = plugin_dir / "config" / "managers"
        managers_config = managers_dir / "config.json"
        example_config = plugin_dir / "config" / "config.example.json"

        if not managers_config.exists() and example_config.exists():
            managers_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(example_config), str(managers_config))
            logger.info(f"Joha: 已从示例创建配置文件: {managers_config}")

    def _setup_bot_uin(self) -> None:
        """从 rqhbot 配置中读取 bot_uin 并注入 joha 运行时上下文"""
        try:
            from sdk.config import config_manager as rqh_config
            bot_uin = rqh_config.get("napcat.bot_uin", 0)
            runtime_context.bot_uin = int(bot_uin) if bot_uin else 0
        except Exception as e:
            logger.warning(f"Joha: 获取 bot_uin 失败: {e}")
            runtime_context.bot_uin = 0

    # ==================== 私聊消息处理 ====================

    @private_message()
    async def on_private_message(self, event: PrivateMessageEvent) -> None:
        """处理私聊消息"""
        if self._bot_api_adapter is None or not self.enabled:
            return

        user_id = str(event.user_id)
        text = event.message.plain_text.strip()

        if not text:
            return

        # 调用服务层生成回复（私聊默认强制回复模式）
        response = await message_service.process_message(
            userid=user_id,
            message=text,
            group_id=None,
            force_reply=True,
            is_at_bot=True,
        )

        if response:
            try:
                await self.api.send_private_message(event.user_id, response)
            except Exception as e:
                logger.error(f"Joha: 发送私聊消息失败: {e}")

    # ==================== 群消息处理 ====================

    @group_message()
    async def on_group_message(self, event: GroupMessageEvent) -> None:
        """处理群消息 — 完整的 joha 对话流程"""
        if self._bot_api_adapter is None or not self.enabled:
            return

        user_id = str(event.user_id)
        group_id = str(event.group_id)
        text = event.message.plain_text.strip()
        raw_message = event.raw_message

        # 1. 提取图片
        images = extract_images_from_rqhbot_event(event)

        # 既没有文字也没有图片，跳过
        if not text and not images:
            return

        # 2. 记录群消息到状态追踪器（用于决策模型）
        group_state_manager.record_message(
            group_id=group_id,
            user_id=user_id,
            text=text or "[图片]",
            is_bot=False,
        )

        # 3. 处理斜杠命令
        fallback_command = normalize_fallback_command(text)
        if fallback_command:
            handled = await command_handler.handle_command(
                fallback_command,
                user_id,
                event.group_id,
                self._bot_api_adapter,
            )
            # 纯命令或已处理则返回
            if handled is not None or text.startswith("/"):
                return

        # 4. 提取消息元数据
        is_at_bot = self._check_at_bot(raw_message)
        reply_to_bot = self._check_reply_to_bot(raw_message)
        is_pure_sticker_or_image = bool(images and not text)

        # 5. 使用消息队列处理（智能合并）
        merged_msg = await message_queue_manager.add_message(
            user_id=user_id,
            group_id=group_id,
            message=text,
            images=images,
            is_at_bot=is_at_bot,
            reply_to_bot=reply_to_bot,
            is_pure_sticker_or_image=is_pure_sticker_or_image,
        )

        # 如果队列返回了合并消息，则处理
        if merged_msg:
            await self._process_merged_message(event, merged_msg)

    # ==================== 消息元数据提取 ====================

    def _check_at_bot(self, raw_message: str) -> bool:
        """检查消息是否 @ 了机器人"""
        bot_uin = runtime_context.bot_uin
        if not bot_uin or not raw_message:
            return False
        return f"[CQ:at,qq={bot_uin}]" in raw_message

    def _check_reply_to_bot(self, raw_message: str) -> bool:
        """检查消息是否回复了机器人（需要从 raw_message 中解析）"""
        bot_uin = runtime_context.bot_uin
        if not bot_uin or not raw_message:
            return False
        # NapCat 的回复格式：[CQ:reply,id=xxx][CQ:at,qq=bot_uin]...
        # 如果同时有 reply 和 @bot，且 @bot 紧随 reply，说明是回复机器人
        if "[CQ:reply" in raw_message:
            return f"[CQ:at,qq={bot_uin}]" in raw_message
        return False

    # ==================== 消息处理核心流程 ====================

    async def _process_merged_message(
        self,
        event: GroupMessageEvent,
        merged_msg: Any,
    ) -> None:
        """处理合并后的消息：服务层生成回复 -> 发送

        Args:
            event: 原始群消息事件（用于获取群 ID 等）
            merged_msg: 消息队列合并后的消息对象
        """
        # 调用 joha 服务层生成回复
        response = await message_service.process_message(
            userid=merged_msg.user_id,
            message=merged_msg.merged_text,
            group_id=merged_msg.group_id,
            is_at_bot=merged_msg.is_at_bot,
            reply_to_bot=merged_msg.reply_to_bot,
            is_pure_sticker_or_image=merged_msg.is_pure_sticker_or_image,
            images=merged_msg.images,
        )

        # 发送回复
        if response:
            try:
                await self.api.send_group_message(event.group_id, response)
                # 记录机器人回复到群组状态
                group_state_manager.record_bot_reply(
                    group_id=str(event.group_id),
                    text=response,
                )
            except Exception as e:
                logger.error(f"Joha: 发送群消息失败: {e}")
