"""
运行时上下文
集中管理启动期注入的运行参数，避免业务模块硬编码。
"""
from dataclasses import dataclass


@dataclass
class RuntimeContext:
    bot_uin: int = 0


runtime_context = RuntimeContext()
