"""
回复决策配置加载器
将 reply_decision 的魔法数字集中到 config.json，支持热读取
"""
from typing import Dict, List, Any
from dataclasses import dataclass, field
from joha.config.managers.config_manager import config as config_manager


def _get_section() -> Dict[str, Any]:
    return config_manager.get("reply_decision", {})


@dataclass(frozen=True)
class ReplyConfig:
    """回复决策配置（每次调用懒加载最新值）"""

    @property
    def bot_nicknames(self) -> set:
        return set(config_manager.get("reply_decision.bot_nicknames", ["bot", "机器人"]))

    @property
    def feedback_weights(self) -> Dict[str, float]:
        return config_manager.get("reply_decision.feedback_weights", {})

    @property
    def thresholds(self) -> Dict[str, float]:
        return config_manager.get("reply_decision.thresholds", {})

    @property
    def blend(self) -> Dict[str, float]:
        return config_manager.get("reply_decision.blend", {})

    @property
    def ai_intent_trigger(self) -> Dict[str, Any]:
        return config_manager.get("reply_decision.ai_intent_trigger", {})

    @property
    def group_dynamic(self) -> Dict[str, float]:
        return config_manager.get("reply_decision.group_dynamic", {})

    @property
    def length_bonuses(self) -> Dict[str, float]:
        return config_manager.get("reply_decision.length_bonuses", {})

    @property
    def spam_detection(self) -> Dict[str, float]:
        return config_manager.get("reply_decision.spam_detection", {})

    @property
    def intent_feedback_mapping(self) -> Dict[str, str]:
        return config_manager.get("reply_decision.intent_feedback_mapping", {})

    @property
    def threshold_adjustments(self) -> Dict[str, float]:
        return config_manager.get("reply_decision.threshold_adjustments", {})

    def __getattr__(self, name):
        return config_manager.get(f"reply_decision.{name}")


reply_cfg = ReplyConfig()
