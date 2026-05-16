"""
RqhBot SDK —— 核心模块
提供客户端连接、API 调用、事件模型等基础能力
"""

from __future__ import annotations

from .api import BotAPI
from .client import MessageSegment, NapCatClient
from .event_bus import EventBus
from .emoji_map import FACE_NAMES, get_face_name
from .events import (
    BaseEvent,
    FriendRecallNotice,
    FriendRequestEvent,
    GroupBanNotice,
    GroupDecreaseNotice,
    GroupIncreaseNotice,
    GroupMessageEvent,
    GroupRecallNotice,
    GroupRequestEvent,
    Message,
    NoticeEvent,
    PokeNotice,
    PrivateMessageEvent,
    RequestEvent,
)

__all__: list[str] = [
    "MessageSegment",
    "NapCatClient",
    "BotAPI",
    "EventBus",
    "BaseEvent",
    "Message",
    "GroupMessageEvent",
    "PrivateMessageEvent",
    "NoticeEvent",
    "GroupIncreaseNotice",
    "GroupDecreaseNotice",
    "GroupBanNotice",
    "GroupRecallNotice",
    "FriendRecallNotice",
    "PokeNotice",
    "RequestEvent",
    "FriendRequestEvent",
    "GroupRequestEvent",
    "FACE_NAMES",
    "get_face_name",
]
