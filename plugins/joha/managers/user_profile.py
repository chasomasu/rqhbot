import time
import json
import os
from dataclasses import dataclass, asdict
from typing import Dict, Optional
from joha.config.infrastructure.logger import johalog_logger

PROFILES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "storage")
PROFILES_FILE = os.path.join(PROFILES_DIR, "user_profiles.json")


@dataclass
class UserProfile:
    user_id: str
    total_interactions: int = 0
    positive_feedbacks: int = 0
    last_interaction_ts: float = 0.0
    is_blocked: bool = False
    is_vip: bool = False

    def score(self) -> float:
        if self.is_blocked:
            return -5.0
        if self.is_vip:
            return 1.5

        score = 0.0

        if self.total_interactions > 0:
            quality = self.positive_feedbacks / self.total_interactions
            score += (quality - 0.5) * 1.0
        else:
            score += 0.3

        gap = time.time() - self.last_interaction_ts
        if gap < 10:
            score -= 1.5
        elif gap < 60:
            score -= 0.5

        return score

    def to_dict(self) -> Dict:
        """转换为字典用于JSON序列化"""
        return {
            "user_id": self.user_id,
            "total_interactions": self.total_interactions,
            "positive_feedbacks": self.positive_feedbacks,
            "last_interaction_ts": self.last_interaction_ts,
            "is_blocked": self.is_blocked,
            "is_vip": self.is_vip,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "UserProfile":
        """从字典创建UserProfile"""
        return cls(
            user_id=data.get("user_id", ""),
            total_interactions=data.get("total_interactions", 0),
            positive_feedbacks=data.get("positive_feedbacks", 0),
            last_interaction_ts=data.get("last_interaction_ts", 0.0),
            is_blocked=bool(data.get("is_blocked", False)),
            is_vip=bool(data.get("is_vip", False)),
        )


class UserProfileManager:

    def __init__(self):
        self._cache: Dict[str, UserProfile] = {}
        self._dirty: set = set()
        self._load_from_disk()
    
    def _load_from_disk(self):
        """从磁盘加载用户画像数据"""
        try:
            if os.path.exists(PROFILES_FILE):
                with open(PROFILES_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                for user_id, profile_data in data.items():
                    self._cache[user_id] = UserProfile.from_dict(profile_data)
                
                johalog_logger.info(f"已加载 {len(self._cache)} 个用户画像")
        except Exception as e:
            johalog_logger.error(f"加载用户画像失败: {e}")
    
    def _save_to_disk(self):
        """保存所有用户画像到磁盘"""
        try:
            data = {}
            for user_id, profile in self._cache.items():
                data[user_id] = profile.to_dict()
            
            os.makedirs(PROFILES_DIR, exist_ok=True)
            with open(PROFILES_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            self._dirty.clear()
        except Exception as e:
            johalog_logger.error(f"保存用户画像失败: {e}")
    
    def _mark_dirty(self, user_id: str):
        """标记用户画像为待保存"""
        self._dirty.add(user_id)

    def get(self, user_id: str) -> UserProfile:
        if user_id in self._cache:
            return self._cache[user_id]
        
        # 如果缓存中没有，创建新的默认画像
        profile = UserProfile(user_id=user_id)
        self._cache[user_id] = profile
        self._mark_dirty(user_id)
        return profile

    def record_interaction(self, user_id: str, positive: bool = False):
        p = self.get(user_id)
        p.total_interactions += 1
        p.last_interaction_ts = time.time()
        if positive:
            p.positive_feedbacks += 1
        self._mark_dirty(user_id)

    def set_blocked(self, user_id: str, blocked: bool):
        self.get(user_id).is_blocked = blocked
        self._mark_dirty(user_id)

    def set_vip(self, user_id: str, vip: bool):
        self.get(user_id).is_vip = vip
        self._mark_dirty(user_id)
    
    def save_all(self):
        """保存所有待保存的用户画像"""
        if self._dirty:
            self._save_to_disk()


user_profile_manager = UserProfileManager()
