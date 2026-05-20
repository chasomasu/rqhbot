"""
API 接口层
提供发送消息、获取记录等操作的强类型接口封装
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, TypeAlias

from sdk.core.client import NapCatClient
from sdk.core.interfaces import MessageSegmentType

logger = logging.getLogger(__name__)

# ---- 类型别名 ----
APIResponse: TypeAlias = Dict[str, Any]


class BotAPI:
    """机器人 API 封装类 —— 对 NapCatClient 的方法调用做上层转发"""

    def __init__(self, client: NapCatClient) -> None:
        self.client: NapCatClient = client

    async def call(self, action: str, params: Optional[Dict[str, Any]] = None) -> APIResponse:
        """调用任意 OneBot API"""
        return await self.client.call_api(action, params)

    # ======================== 消息发送 ========================

    async def send_group_message(
        self,
        group_id: int,
        message: str = "",
        image_path: Optional[str] = None,
        at_user_id: Optional[int] = None,
        reply_message_id: Optional[int] = None,
    ) -> APIResponse:
        """发送群聊消息

        Args:
            group_id: 群组 ID
            message: 文字内容
            image_path: 图片文件路径（可选）
            at_user_id: @ 的用户 ID（可选）
            reply_message_id: 回复的消息 ID（可选）

        Returns:
            APIResponse
        """
        return await self.client.send_group_message(
            group_id, message, image_path, at_user_id, reply_message_id
        )

    async def send_private_message(
        self,
        user_id: int,
        message: str = "",
        image_path: Optional[str] = None,
        reply_message_id: Optional[int] = None,
    ) -> APIResponse:
        """发送私聊消息

        Args:
            user_id: 用户 ID
            message: 文字内容
            image_path: 图片文件路径（可选）
            reply_message_id: 回复的消息 ID（可选）

        Returns:
            APIResponse
        """
        return await self.client.send_private_message(
            user_id, message, image_path, reply_message_id
        )

    async def send_group_message_segments(
        self,
        group_id: int,
        segments: List[MessageSegmentType],
        reply_message_id: Optional[int] = None,
    ) -> APIResponse:
        """发送图文混排群消息（数组格式）

        Args:
            group_id: 群号
            segments: 消息段列表，使用 MessageSegment 构建
            reply_message_id: 回复的消息 ID（可选）

        Returns:
            APIResponse

        Example:
            ```python
            await api.send_group_message_segments(
                group_id=123,
                segments=[
                    MessageSegment.text("你好，"),
                    MessageSegment.image("https://example.com/pic.png"),
                ]
            )
            ```
        """
        return await self.client.send_group_message_segments(
            group_id, segments, reply_message_id
        )

    async def send_private_message_segments(
        self,
        user_id: int,
        segments: List[MessageSegmentType],
        reply_message_id: Optional[int] = None,
    ) -> APIResponse:
        """发送图文混排私聊消息（数组格式）

        Args:
            user_id: 用户 ID
            segments: 消息段列表，使用 MessageSegment 构建
            reply_message_id: 回复的消息 ID（可选）

        Returns:
            APIResponse
        """
        return await self.client.send_private_message_segments(
            user_id, segments, reply_message_id
        )

    # ======================== 消息管理 ========================

    async def delete_message(self, message_id: int) -> APIResponse:
        """撤回 / 删除消息

        Args:
            message_id: 消息 ID

        Returns:
            APIResponse
        """
        return await self.client.delete_message(message_id)

    async def get_message(self, message_id: int) -> APIResponse:
        """获取指定消息

        Args:
            message_id: 消息 ID

        Returns:
            APIResponse
        """
        return await self.client.get_message(message_id)

    # ======================== 互动操作 ========================

    async def group_poke(self, group_id: int, user_id: int) -> APIResponse:
        """群内戳一戳

        Args:
            group_id: 群号
            user_id: 要戳的用户 ID

        Returns:
            APIResponse
        """
        return await self.client.group_poke(group_id, user_id)

    async def friend_poke(self, user_id: int) -> APIResponse:
        """好友戳一戳

        Args:
            user_id: 要戳的用户 ID

        Returns:
            APIResponse
        """
        return await self.client.friend_poke(user_id)

    # ======================== 娱乐消息 ========================

    async def send_group_dice(self, group_id: int) -> APIResponse:
        """发送群骰子消息

        Args:
            group_id: 群号

        Returns:
            APIResponse
        """
        return await self.client.send_group_dice(group_id)

    async def send_group_rps(self, group_id: int) -> APIResponse:
        """发送群猜拳消息

        Args:
            group_id: 群号

        Returns:
            APIResponse
        """
        return await self.client.send_group_rps(group_id)

    async def send_private_dice(self, user_id: int) -> APIResponse:
        """发送私聊骰子消息

        Args:
            user_id: 用户 ID

        Returns:
            APIResponse
        """
        return await self.client.send_private_dice(user_id)

    async def send_private_rps(self, user_id: int) -> APIResponse:
        """发送私聊猜拳消息

        Args:
            user_id: 用户 ID

        Returns:
            APIResponse
        """
        return await self.client.send_private_rps(user_id)

    # ======================== 历史记录 ========================

    async def get_group_message_history(
        self,
        group_id: int,
        message_seq: Optional[int] = None,
        count: int = 20,
        reverse_order: bool = False,
    ) -> APIResponse:
        """获取群消息历史记录

        Args:
            group_id: 群号
            message_seq: 消息序号，提供则从该消息开始获取
            count: 获取数量，默认 20
            reverse_order: 是否倒序，默认 False

        Returns:
            APIResponse
        """
        return await self.client.get_group_message_history(
            group_id, message_seq, count, reverse_order
        )

    async def get_private_message_history(
        self,
        user_id: int,
        message_seq: int,
        count: int = 20,
        reverse_order: bool = False,
    ) -> APIResponse:
        """获取私聊消息历史记录

        Args:
            user_id: 用户 ID
            message_seq: 消息序号
            count: 获取数量，默认 20
            reverse_order: 是否倒序，默认 False

        Returns:
            APIResponse
        """
        return await self.client.get_private_message_history(
            user_id, message_seq, count, reverse_order
        )

    # ======================== 群组管理 ========================

    async def get_group_list(self) -> APIResponse:
        """获取群列表

        Returns:
            APIResponse
        """
        return await self.client.get_group_list()

    async def get_group_member_list(self, group_id: int) -> APIResponse:
        """获取群成员列表

        Args:
            group_id: 群号

        Returns:
            APIResponse
        """
        return await self.client.get_group_member_list(group_id)

    async def get_group_member_info(self, group_id: int, user_id: int) -> APIResponse:
        """获取群成员信息

        Args:
            group_id: 群号
            user_id: 用户 ID

        Returns:
            APIResponse
        """
        return await self.client.get_group_member_info(group_id, user_id)

    async def set_group_ban(self, group_id: int, user_id: int, duration: int = 1800) -> APIResponse:
        """设置群禁言

        Args:
            group_id: 群号
            user_id: 用户 ID
            duration: 禁言时长（秒），默认 1800

        Returns:
            APIResponse
        """
        return await self.client.set_group_ban(group_id, user_id, duration)

    async def set_group_kick(self, group_id: int, user_id: int, reject_add_request: bool = False) -> APIResponse:
        """踢出群成员

        Args:
            group_id: 群号
            user_id: 用户 ID
            reject_add_request: 是否拒绝后续加群请求

        Returns:
            APIResponse
        """
        return await self.client.set_group_kick(group_id, user_id, reject_add_request)

    async def set_group_card(self, group_id: int, user_id: int, card: str = "") -> APIResponse:
        """设置群成员名片

        Args:
            group_id: 群号
            user_id: 用户 ID
            card: 名片内容

        Returns:
            APIResponse
        """
        return await self.client.set_group_card(group_id, user_id, card)

    # ======================== 好友管理 ========================

    async def get_friend_list(self) -> APIResponse:
        """获取好友列表

        Returns:
            APIResponse
        """
        return await self.client.get_friend_list()

    async def get_login_info(self) -> APIResponse:
        """获取登录信息

        Returns:
            APIResponse
        """
        return await self.client.get_login_info()

    async def get_stranger_info(self, user_id: int) -> APIResponse:
        """获取陌生人信息

        Args:
            user_id: 用户 ID

        Returns:
            APIResponse
        """
        return await self.client.get_stranger_info(user_id)

    # ======================== 请求处理 ========================

    async def set_friend_add_request(self, flag: str, approve: bool = True, remark: str = "") -> APIResponse:
        """处理好友请求

        Args:
            flag: 请求标识
            approve: 是否同意
            remark: 备注名

        Returns:
            APIResponse
        """
        return await self.client.set_friend_add_request(flag, approve, remark)

    async def set_group_add_request(self, flag: str, sub_type: str, approve: bool = True, reason: str = "") -> APIResponse:
        """处理群请求

        Args:
            flag: 请求标识
            sub_type: 请求子类型（add/invite）
            approve: 是否同意
            reason: 拒绝理由

        Returns:
            APIResponse
        """
        return await self.client.set_group_add_request(flag, sub_type, approve, reason)

    async def send_like(self, user_id: int, times: int = 1) -> APIResponse:
        """发送赞

        Args:
            user_id: 用户 ID
            times: 点赞次数

        Returns:
            APIResponse
        """
        return await self.client.send_like(user_id, times)

    async def get_version_info(self) -> APIResponse:
        """获取版本信息

        Returns:
            APIResponse
        """
        return await self.client.get_version_info()

    # ======================== 性能监控 ========================

    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计信息

        Returns:
            包含以下字段的字典:
            - total_messages: 总消息数
            - total_processing_time: 总处理时间（秒）
            - avg_latency: 平均延迟（秒）
            - reconnect_attempts: 重连尝试次数
            - is_connected: 是否已连接
            - queue_size: 消息队列当前大小
        """
        stats = self.client.get_performance_stats()
        # 添加队列大小信息
        if hasattr(self.client, "msg_queue") and self.client.msg_queue is not None:
            stats["queue_size"] = self.client.msg_queue.qsize()
        else:
            stats["queue_size"] = 0
        return stats

    def get_connection_status(self) -> Dict[str, Any]:
        """获取连接状态信息

        Returns:
            包含以下字段的字典:
            - connected: 是否已连接
            - ws_url: WebSocket 地址
            - reconnect_attempts: 重连尝试次数
        """
        return {
            "connected": self.client.connected,
            "ws_url": self.client.ws_url,
            "reconnect_attempts": self.client._reconnect_attempts,
        }
    