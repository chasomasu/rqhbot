# 消息处理器模块
from .message_handler import message_handler, MessageHandler
from .commands import command_handler, normalize_fallback_command
from .service import message_service, MessageService

__all__ = [
    'message_handler',
    'MessageHandler',
    'command_handler',
    'normalize_fallback_command',
    'message_service',
    'MessageService',
]
