"""
冷却管理器 v2.0 - JSON 持久化版
更平滑的冷却曲线，支持按群独立冷却和用户级别冷却
重启后恢复冷却状态
"""
import time
import math
import json
import os
from typing import Dict
from joha.config.infrastructure.logger import tprint

COOLDOWN_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "storage", "cooldown.json")


class CooldownManager:

    def __init__(self):
        self.last_reply_ts: Dict[str, float] = {}
        self.reply_count: Dict[str, int] = {}
        self.user_last_reply: Dict[str, float] = {}
        self._load_from_file()

    def _load_from_file(self):
        """从文件加载冷却数据"""
        try:
            if os.path.exists(COOLDOWN_FILE):
                with open(COOLDOWN_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                # 加载群组冷却数据
                for group_id, group_data in data.get("groups", {}).items():
                    self.last_reply_ts[group_id] = group_data.get("last_reply_ts", 0)
                    self.reply_count[group_id] = group_data.get("reply_count", 0)
                
                # 加载用户冷却数据
                for user_id, user_data in data.get("users", {}).items():
                    self.user_last_reply[user_id] = user_data.get("last_reply_ts", 0)
                
                total_records = len(self.last_reply_ts) + len(self.user_last_reply)
                if total_records > 0:
                    tprint("info", f"[Cooldown] 已恢复 {total_records} 条冷却记录")
        except Exception as e:
            tprint("error", f"[Cooldown] 加载冷却数据失败: {e}")
    
    def _save_to_file(self):
        """保存冷却数据到文件"""
        try:
            storage_dir = os.path.dirname(COOLDOWN_FILE)
            os.makedirs(storage_dir, exist_ok=True)
            
            data = {
                "groups": {},
                "users": {}
            }
            
            # 保存群组冷却数据
            for group_id in self.last_reply_ts:
                data["groups"][group_id] = {
                    "last_reply_ts": self.last_reply_ts[group_id],
                    "reply_count": self.reply_count.get(group_id, 0)
                }
            
            # 保存用户冷却数据
            for user_id in self.user_last_reply:
                data["users"][user_id] = {
                    "last_reply_ts": self.user_last_reply[user_id]
                }
            
            with open(COOLDOWN_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            tprint("error", f"[Cooldown] 保存冷却数据失败: {e}")

    def get_cooldown_penalty(self, group_id: str, user_id: str = "") -> float:
        penalty = 0.0
        now = time.time()

        group_elapsed = now - self.last_reply_ts.get(group_id, 0)
        if group_elapsed < 2:
            penalty -= 2.0
        elif group_elapsed < 5:
            penalty -= 1.5
        elif group_elapsed < 15:
            penalty -= 1.0 * math.exp(-(group_elapsed - 5) / 6)
        elif group_elapsed < 60:
            penalty -= 0.3 * math.exp(-(group_elapsed - 15) / 20)

        if user_id:
            user_elapsed = now - self.user_last_reply.get(user_id, 0)
            if user_elapsed < 3:
                penalty -= 1.0
            elif user_elapsed < 10:
                penalty -= 0.5 * math.exp(-(user_elapsed - 3) / 4)

        return penalty

    def record_reply(self, group_id: str, user_id: str = ""):
        now = time.time()
        self.last_reply_ts[group_id] = now
        self.reply_count[group_id] = self.reply_count.get(group_id, 0) + 1
        if user_id:
            self.user_last_reply[user_id] = now
        self._save_to_file()  # 保存到文件

    def can_reply(self, group_id: str, user_id: str = "", min_interval: float = 2.0) -> bool:
        now = time.time()
        if now - self.last_reply_ts.get(group_id, 0) < min_interval:
            return False
        if user_id and now - self.user_last_reply.get(user_id, 0) < min_interval:
            return False
        return True

    def get_group_stats(self, group_id: str) -> Dict:
        return {
            "last_reply_seconds_ago": time.time() - self.last_reply_ts.get(group_id, 0),
            "total_replies": self.reply_count.get(group_id, 0),
        }


cooldown_manager = CooldownManager()
