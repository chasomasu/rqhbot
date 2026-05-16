"""
群组模式配置管理器 - JSON 持久化存储群组模式设置
"""
import json
import os
from typing import Dict, Optional
from joha.config.infrastructure.logger import johalog_logger

GROUP_MODES_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "storage", "group_modes.json")


class GroupModeConfig:
    """群组模式配置管理器"""

    def __init__(self, config_path: Optional[str] = None):
        self._modes: Dict[str, str] = {}
        self.load()

    def load(self) -> None:
        """从磁盘加载群组模式配置"""
        try:
            if os.path.exists(GROUP_MODES_FILE):
                with open(GROUP_MODES_FILE, "r", encoding="utf-8") as f:
                    self._modes = json.load(f)
            else:
                self._modes = {}
            johalog_logger.info(f"已加载 {len(self._modes)} 个群组模式配置")
        except Exception as e:
            johalog_logger.error(f"加载群组模式配置失败: {e}")
            self._modes = {}

    def save(self) -> None:
        """保存群组模式配置到磁盘"""
        try:
            storage_dir = os.path.dirname(GROUP_MODES_FILE)
            os.makedirs(storage_dir, exist_ok=True)
            with open(GROUP_MODES_FILE, "w", encoding="utf-8") as f:
                json.dump(self._modes, f, ensure_ascii=False, indent=2)
        except Exception as e:
            johalog_logger.error(f"保存群组模式配置失败: {e}")

    def get_mode(self, group_id: str, default: str = "passive") -> str:
        return self._modes.get(group_id, default)

    def set_mode(self, group_id: str, mode: str) -> None:
        if mode not in ["active", "passive"]:
            raise ValueError(f"无效的模式: {mode}，必须是 'active' 或 'passive'")

        self._modes[group_id] = mode
        self.save()  # 立即保存到磁盘
        johalog_logger.info(f"群组 {group_id} 模式已设置为: {mode}")

    def remove_mode(self, group_id: str) -> bool:
        if group_id in self._modes:
            del self._modes[group_id]
            self.save()  # 立即保存到磁盘
            johalog_logger.info(f"已删除群组 {group_id} 的模式设置")
            return True
        return False

    def has_mode(self, group_id: str) -> bool:
        return group_id in self._modes

    def get_all_modes(self) -> Dict[str, str]:
        return self._modes.copy()

    def clear_all(self) -> None:
        self._modes.clear()
        self.save()  # 保存到磁盘
        johalog_logger.info("已清空所有群组模式设置")


group_mode_config = GroupModeConfig()
