"""
事件类定义
定义各种机器人事件的数据结构，所有字段均为强类型声明
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Self

from .emoji_map import get_face_name

logger = logging.getLogger(__name__)

# ---- 类型别名 ----
MessageSegment = Dict[str, Any]
SenderInfo = Dict[str, Any]
EventData = Dict[str, Any]


@dataclass
class Message:
    """消息内容"""
    plain_text: str = ""
    raw_message: str = ""
    segments: List[MessageSegment] = field(default_factory=list)
    face_ids: List[int] = field(default_factory=list)        # 表情 ID 列表
    face_names: List[str] = field(default_factory=list)      # 表情名称列表
    has_dice: bool = False                                    # 是否含骰子
    has_rps: bool = False                                     # 是否含猜拳
    has_poke: bool = False                                    # 是否含戳一戳
    has_sticker: bool = False                                 # 是否含收藏表情包

    @classmethod
    def from_raw(cls, value: Any, raw_message: str = "") -> Self:
        if isinstance(value, list):
            text_parts: List[str] = []
            segments: List[MessageSegment] = []
            face_ids: List[int] = []
            face_names: List[str] = []
            has_sticker = False

            for item in value:
                if not isinstance(item, dict):
                    text_parts.append(str(item))
                    continue

                segments.append(item)
                seg_type = item.get("type", "")
                seg_data = item.get("data", {})

                if seg_type == "text":
                    text_parts.append(str(seg_data.get("text", "")))
                elif seg_type == "face":
                    face_id = int(seg_data.get("id", 0))
                    name = get_face_name(face_id)
                    face_ids.append(face_id)
                    face_names.append(name)
                    text_parts.append(f"[表情:{name}]")
                elif seg_type == "dice":
                    text_parts.append("[骰子]")
                elif seg_type == "rps":
                    text_parts.append("[猜拳]")
                elif seg_type == "poke":
                    text_parts.append("[戳一戳]")
                elif seg_type == "image":
                    sub_type = int(seg_data.get("sub_type", 0))
                    if sub_type == 1:
                        has_sticker = True
                        summary = seg_data.get("summary") or "表情包"
                        text_parts.append(f"[表情包:{summary}]")
                    else:
                        file_name = seg_data.get("file", "图片")
                        text_parts.append(f"[图片:{file_name}]")

            plain_text = "".join(text_parts)
            return cls(
                plain_text=plain_text,
                raw_message=raw_message or plain_text,
                segments=segments,
                face_ids=face_ids,
                face_names=face_names,
                has_dice="[骰子]" in plain_text,
                has_rps="[猜拳]" in plain_text,
                has_poke="[戳一戳]" in plain_text,
                has_sticker=has_sticker,
            )

        text = str(value or raw_message or "")
        return cls(plain_text=text, raw_message=raw_message or text)

    def get_plain_text(self) -> str:
        """获取纯文本消息"""
        return self.plain_text or self.raw_message


@dataclass
class BaseEvent:
    """基础事件类 —— 所有事件的公共字段"""
    time: int = 0
    self_id: int = 0
    post_type: str = ""

    @classmethod
    def from_dict(cls, data: EventData) -> Self:
        """从字典创建事件实例

        Args:
            data: 事件原始数据字典

        Returns:
            事件实例
        """
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class GroupMessageEvent(BaseEvent):
    """群消息事件"""
    message_type: str = "group"
    sub_type: str = ""
    message_id: int = 0
    group_id: int = 0
    user_id: int = 0
    user_name: str = ""
    message: Message = field(default_factory=Message)
    raw_message: str = ""
    font: int = 0
    sender: SenderInfo = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: EventData) -> Self:
        """从字典创建群消息事件实例

        Args:
            data: 事件原始数据字典

        Returns:
            GroupMessageEvent 实例
        """
        raw_message: str = str(data.get("raw_message", ""))
        msg = Message.from_raw(data.get("message", raw_message), raw_message)

        snd: SenderInfo = data.get("sender", {})
        uname: str = str(snd.get("nickname", "") or snd.get("card", ""))

        return cls(
            time=int(data.get("time", 0)),
            self_id=int(data.get("self_id", 0)),
            post_type=str(data.get("post_type", "message")),
            message_type=str(data.get("message_type", "group")),
            sub_type=str(data.get("sub_type", "")),
            message_id=int(data.get("message_id", 0)),
            group_id=int(data.get("group_id", 0)),
            user_id=int(data.get("user_id", 0)),
            user_name=uname,
            message=msg,
            raw_message=str(data.get("raw_message", "")),
            font=int(data.get("font", 0)),
            sender=snd,
        )


@dataclass
class PrivateMessageEvent(BaseEvent):
    """私聊消息事件"""
    message_type: str = "private"
    sub_type: str = ""
    message_id: int = 0
    user_id: int = 0
    user_name: str = ""
    message: Message = field(default_factory=Message)
    raw_message: str = ""
    font: int = 0

    @classmethod
    def from_dict(cls, data: EventData) -> Self:
        """从字典创建私聊消息事件实例

        Args:
            data: 事件原始数据字典

        Returns:
            PrivateMessageEvent 实例
        """
        raw_message: str = str(data.get("raw_message", ""))
        msg = Message.from_raw(data.get("message", raw_message), raw_message)

        snd: SenderInfo = data.get("sender", {})
        uname: str = str(
            data.get("user_name", "")
            or snd.get("nickname", "")
            or snd.get("card", "")
        )

        return cls(
            time=int(data.get("time", 0)),
            self_id=int(data.get("self_id", 0)),
            post_type=str(data.get("post_type", "message")),
            message_type=str(data.get("message_type", "private")),
            sub_type=str(data.get("sub_type", "")),
            message_id=int(data.get("message_id", 0)),
            user_id=int(data.get("user_id", 0)),
            user_name=str(data.get("user_name", "")),
            message=msg,
            raw_message=str(data.get("raw_message", "")),
            font=int(data.get("font", 0)),
        )


@dataclass
class NoticeEvent(BaseEvent):
    """通知事件基类"""
    notice_type: str = ""
    user_id: int = 0
    group_id: int = 0

    @classmethod
    def from_dict(cls, data: EventData) -> NoticeEvent:
        notice_type = str(data.get("notice_type", ""))
        raw_subtype = str(data.get("sub_type", ""))
        _map = {
            "group_increase": GroupIncreaseNotice,
            "group_decrease": GroupDecreaseNotice,
            "group_ban":      GroupBanNotice,
            "group_recall":   GroupRecallNotice,
            "friend_recall":  FriendRecallNotice,
        }
        if notice_type == "notify" and raw_subtype == "poke":
            target = PokeNotice
        else:
            target = _map.get(notice_type, NoticeEvent)
        return target._build(data)

    @classmethod
    def _build(cls, data: EventData) -> Self:
        return cls(
            time=int(data.get("time", 0)),
            self_id=int(data.get("self_id", 0)),
            post_type=str(data.get("post_type", "notice")),
            notice_type=str(data.get("notice_type", "")),
            user_id=int(data.get("user_id", 0)),
            group_id=int(data.get("group_id", 0)),
        )


@dataclass
class GroupIncreaseNotice(NoticeEvent):
    """群成员增加"""
    sub_type: str = ""
    operator_id: int = 0

    @classmethod
    def _build(cls, data: EventData) -> Self:
        return cls(
            time=int(data.get("time", 0)),
            self_id=int(data.get("self_id", 0)),
            post_type=str(data.get("post_type", "notice")),
            notice_type="group_increase",
            user_id=int(data.get("user_id", 0)),
            group_id=int(data.get("group_id", 0)),
            sub_type=str(data.get("sub_type", "")),
            operator_id=int(data.get("operator_id", 0)),
        )


@dataclass
class GroupDecreaseNotice(NoticeEvent):
    """群成员减少"""
    sub_type: str = ""
    operator_id: int = 0

    @classmethod
    def _build(cls, data: EventData) -> Self:
        return cls(
            time=int(data.get("time", 0)),
            self_id=int(data.get("self_id", 0)),
            post_type=str(data.get("post_type", "notice")),
            notice_type="group_decrease",
            user_id=int(data.get("user_id", 0)),
            group_id=int(data.get("group_id", 0)),
            sub_type=str(data.get("sub_type", "")),
            operator_id=int(data.get("operator_id", 0)),
        )


@dataclass
class GroupBanNotice(NoticeEvent):
    """群禁言"""
    sub_type: str = ""
    operator_id: int = 0
    duration: int = 0

    @classmethod
    def _build(cls, data: EventData) -> Self:
        return cls(
            time=int(data.get("time", 0)),
            self_id=int(data.get("self_id", 0)),
            post_type=str(data.get("post_type", "notice")),
            notice_type="group_ban",
            user_id=int(data.get("user_id", 0)),
            group_id=int(data.get("group_id", 0)),
            sub_type=str(data.get("sub_type", "")),
            operator_id=int(data.get("operator_id", 0)),
            duration=int(data.get("duration", 0)),
        )


@dataclass
class GroupRecallNotice(NoticeEvent):
    """群消息撤回"""
    operator_id: int = 0
    message_id: int = 0

    @classmethod
    def _build(cls, data: EventData) -> Self:
        return cls(
            time=int(data.get("time", 0)),
            self_id=int(data.get("self_id", 0)),
            post_type=str(data.get("post_type", "notice")),
            notice_type="group_recall",
            user_id=int(data.get("user_id", 0)),
            group_id=int(data.get("group_id", 0)),
            operator_id=int(data.get("operator_id", 0)),
            message_id=int(data.get("message_id", 0)),
        )


@dataclass
class FriendRecallNotice(NoticeEvent):
    """好友消息撤回"""
    message_id: int = 0

    @classmethod
    def _build(cls, data: EventData) -> Self:
        return cls(
            time=int(data.get("time", 0)),
            self_id=int(data.get("self_id", 0)),
            post_type=str(data.get("post_type", "notice")),
            notice_type="friend_recall",
            user_id=int(data.get("user_id", 0)),
            message_id=int(data.get("message_id", 0)),
        )


@dataclass
class PokeNotice(NoticeEvent):
    """戳一戳通知"""
    target_id: int = 0

    @classmethod
    def _build(cls, data: EventData) -> Self:
        return cls(
            time=int(data.get("time", 0)),
            self_id=int(data.get("self_id", 0)),
            post_type=str(data.get("post_type", "notice")),
            notice_type="notify",
            user_id=int(data.get("user_id", 0)),
            group_id=int(data.get("group_id", 0)),
            target_id=int(data.get("target_id", 0)),
        )


@dataclass
class RequestEvent(BaseEvent):
    """请求事件基类（好友申请、群邀请等）"""
    request_type: str = ""
    user_id: int = 0
    comment: str = ""
    flag: str = ""

    @classmethod
    def from_dict(cls, data: EventData) -> RequestEvent:
        request_type = str(data.get("request_type", ""))
        _map = {
            "friend": FriendRequestEvent,
            "group":  GroupRequestEvent,
        }
        target = _map.get(request_type, RequestEvent)
        return target._build(data)

    @classmethod
    def _build(cls, data: EventData) -> Self:
        return cls(
            time=int(data.get("time", 0)),
            self_id=int(data.get("self_id", 0)),
            post_type=str(data.get("post_type", "request")),
            request_type=str(data.get("request_type", "")),
            user_id=int(data.get("user_id", 0)),
            comment=str(data.get("comment", "")),
            flag=str(data.get("flag", "")),
        )


@dataclass
class FriendRequestEvent(RequestEvent):
    """好友申请"""

    @classmethod
    def _build(cls, data: EventData) -> Self:
        return cls(
            time=int(data.get("time", 0)),
            self_id=int(data.get("self_id", 0)),
            post_type=str(data.get("post_type", "request")),
            request_type="friend",
            user_id=int(data.get("user_id", 0)),
            comment=str(data.get("comment", "")),
            flag=str(data.get("flag", "")),
        )


@dataclass
class GroupRequestEvent(RequestEvent):
    """群邀请 / 加群申请"""
    group_id: int = 0
    sub_type: str = ""

    @classmethod
    def _build(cls, data: EventData) -> Self:
        return cls(
            time=int(data.get("time", 0)),
            self_id=int(data.get("self_id", 0)),
            post_type=str(data.get("post_type", "request")),
            request_type="group",
            user_id=int(data.get("user_id", 0)),
            group_id=int(data.get("group_id", 0)),
            sub_type=str(data.get("sub_type", "")),
            comment=str(data.get("comment", "")),
            flag=str(data.get("flag", "")),
        )
