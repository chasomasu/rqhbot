"""
日志配置模块 - 统一的日志系统
支持多级别、文件轮转、格式化输出
"""
import logging
import os
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime
from pathlib import Path


def setup_logger(
    name: str,
    log_dir: str = "logs",
    level: int = logging.INFO,
    when: str = 'MIDNIGHT',  # 每天午夜轮转
    interval: int = 1,
    backup_count: int = 7
) -> logging.Logger:
    """
    设置日志记录器
    
    Args:
        name: 日志记录器名称
        log_dir: 日志目录
        level: 日志级别
        when: 轮转时间点
        interval: 轮转间隔
        backup_count: 备份文件数量
    
    Returns:
        logging.Logger: 配置好的日志记录器
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    if logger.handlers:
        return logger
    
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)
    
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # joha的日志统一放自己目录，不占ncatbot的根目录logs
    try:
        log_file = log_path / f"{name}.log"
        file_handler = TimedRotatingFileHandler(
            log_file,
            when=when,
            interval=interval,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except (PermissionError, OSError):
        pass
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """获取日志记录器"""
    return setup_logger(name)


# 预定义的日志记录器 - 全部放自己目录，不碰根目录logs
JOHA_LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "storage", "johalog")

johalog_logger = setup_logger("johalog", log_dir=JOHA_LOG_DIR)
ai_logger = setup_logger("ai", log_dir=JOHA_LOG_DIR)
db_logger = setup_logger("db", log_dir=JOHA_LOG_DIR)
network_logger = setup_logger("network", log_dir=JOHA_LOG_DIR)


def log_message(
    logger: logging.Logger,
    level: str,
    message: str,
    **kwargs
) -> None:
    """
    记录消息日志
    
    Args:
        logger: 日志记录器
        level: 日志级别 (debug, info, warning, error, critical)
        message: 日志消息
        **kwargs: 额外的上下文信息
    """
    log_method = getattr(logger, level.lower(), logger.info)
    
    if kwargs:
        context = " | ".join(f"{k}={v}" for k, v in kwargs.items())
        log_method(f"{message} [{context}]")
    else:
        log_method(message)


# ==================== 统一终端输出 ====================

_terminal_logger = setup_logger("terminal", log_dir=JOHA_LOG_DIR)


def tprint(level: str, *args, **kwargs):
    """
    替代 print() — 同时输出到终端和日志文件
    
    level: debug / info / warning / error
    """
    msg = " ".join(str(a) for a in args)
    log_method = getattr(_terminal_logger, level, _terminal_logger.info)
    if kwargs:
        ctx = " | ".join(f"{k}={v}" for k, v in kwargs.items())
        log_method(f"{msg}  [{ctx}]")
    else:
        log_method(msg)