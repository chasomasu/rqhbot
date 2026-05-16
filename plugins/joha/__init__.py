"""
Joha - 智能聊天机器人框架 v1.0.0

模块化架构：
  core/        — 编排入口（服务、消息处理、命令处理、运行时上下文）
  ai/          — AI 驱动（客户端、生成器、Provider、Bot、分类器）
  decision/    — 决策大脑（回复概率、冷却、群状态、知识库、工具调用）
  managers/    — 数据管理（历史、画像、风格、人设、权限）
  config/      — 基础设施（配置、日志、缓存）
"""

from .core import (
    message_service,
    message_handler,
    command_handler,
)

from .ai import (
    generator,
)

from .managers import (
    persona_manager,
    history_manager,
    style_learner,
    user_profile_manager,
)

from .config import (
    config,
    johalog_logger,
    ai_logger,
    group_mode_config,
)

from .decision import (
    cooldown_manager,
)

# 版本信息
__version__ = "1.0.0"
__author__ = "Joha Team"

# 导出主要类和函数
__all__ = [
    'message_service',
    'message_handler',
    'command_handler',
    'generator',
    'persona_manager',
    'history_manager',
    'style_learner',
    'user_profile_manager',
    'group_mode_config',
    'cooldown_manager',
    'config',
    'johalog_logger',
    'ai_logger',
]
