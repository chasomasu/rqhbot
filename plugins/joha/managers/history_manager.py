"""
历史记录管理器 - JSON 存储版（重构版）
支持按用户QQ区分，内部按群隔离的消息存储
集成实时过滤机制，确保历史记录质量
"""
import json
import logging
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from collections import Counter
from joha.config.infrastructure.cache import LRUCache
from joha.core.utils import post_processor

logger = logging.getLogger(__name__)

MAX_HISTORY_LENGTH = 2000
CACHE_TTL = 300
# 使用标准 history 目录
STORAGE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "storage", "history")


class HistoryManager:

    def __init__(self, history_dir: str = ""):
        self.history_dir = history_dir or STORAGE_DIR
        self._cache: LRUCache = LRUCache(capacity=50)
        os.makedirs(self.history_dir, exist_ok=True)

    def _path(self, userid: str) -> str:
        """生成用户历史文件路径，使用新格式 user_{qq号}.json"""
        safe_userid = str(userid).replace("/", "_").replace("\\", "_")
        return os.path.join(self.history_dir, f"user_{safe_userid}.json")

    def _read_all(self, userid: str) -> Dict[str, List[Dict[str, Any]]]:
        """读取用户所有历史记录，返回按群组隔离的结构"""
        path = self._path(userid)
        if not os.path.exists(path):
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # 新格式：{"group_id": [messages], ...}
            if isinstance(data, dict):
                return data
            # 兼容旧格式：如果是列表，则转换为新格式
            elif isinstance(data, list):
                grouped_data = {}
                for record in data:
                    group_id = str(record.get("group_id", "global"))
                    if group_id not in grouped_data:
                        grouped_data[group_id] = []
                    grouped_data[group_id].append(record)
                return grouped_data
            else:
                return {}
        except Exception as e:
            logger.error(f"读取历史记录失败 {userid}: {e}")
            return {}

    def _write_all(self, userid: str, history: Dict[str, List[Dict[str, Any]]]) -> bool:
        """保存用户所有历史记录，按群组隔离的结构"""
        path = self._path(userid)
        try:
            # 限制每个群组的记录数量
            limited_history = {}
            for group_id, records in history.items():
                limited_history[group_id] = records[-MAX_HISTORY_LENGTH:]
            
            with open(path, "w", encoding="utf-8") as f:
                json.dump(limited_history, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"保存历史记录失败 {userid}: {e}")
            return False

    def load_history(self, userid: str, group_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """加载指定用户和群组的历史记录"""
        userid_str = str(userid)
        cache_key = f"history_{userid_str}_{group_id if group_id else 'all'}"

        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        all_history = self._read_all(userid_str)
        
        if group_id is not None:
            gid = str(group_id)
            history = all_history.get(gid, [])
        else:
            # 如果未指定群组，合并所有群组的记录并按时间排序
            history = []
            for records in all_history.values():
                history.extend(records)
            # 按时间戳排序
            history.sort(key=lambda x: x.get("timestamp", ""))
        
        self._cache.set(cache_key, history, ttl=CACHE_TTL)
        return history

    def save_history(self, userid: str, history: Dict[str, List[Dict[str, Any]]]) -> bool:
        """保存用户所有历史记录（按群组隔离的结构）"""
        userid_str = str(userid)
        ok = self._write_all(userid_str, history)
        self._cache.clear()
        return ok

    def add_message(self, userid: str, message: str, response: Optional[str] = None,
                    group_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """添加消息到历史记录，自动按群组隔离
        
        支持合并消息：如果message包含多条消息（用\n分隔），会分别存储
        自动应用后处理过滤，确保回复质量
        """
        userid_str = str(userid)
        all_history = self._read_all(userid_str)
        
        # 确定群组ID，默认为"global"
        gid = str(group_id) if group_id else "global"
        
        # 初始化该群组的记录列表（如果不存在）
        if gid not in all_history:
            all_history[gid] = []
        
        # 对response应用后处理过滤
        filtered_response = None
        if response:
            filtered_response = post_processor.process(response)
            # 记录过滤情况
            if filtered_response != response:
                logger.debug(f"历史记录过滤 | 原: {response[:50]} | 新: {filtered_response[:50]}")
        
        # 检查是否为合并消息（包含换行符的多条消息）
        messages = message.split('\n') if '\n' in message else [message]
        
        # 为每条消息创建记录
        for msg in messages:
            if msg.strip():  # 跳过空消息
                all_history[gid].append({
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "group_id": gid,
                    "message": msg.strip(),
                    "response": filtered_response or "",
                })
        
        self._write_all(userid_str, all_history)
        self._cache.clear()
        return self.load_history(userid_str, group_id=group_id)

    def find_similar_response(self, userid: str, current_message: str,
                              min_similarity: float = 0.3, group_id: Optional[str] = None) -> Optional[str]:
        history = self.load_history(userid, group_id=group_id)
        if not history:
            return None

        current_words = set(current_message.lower().split())
        best_match = None
        max_similarity = min_similarity

        for record in history:
            if record.get("response") and record.get("message"):
                hist_words = set(record["message"].lower().split())
                union_words = current_words | hist_words
                if not union_words:
                    continue
                similarity = len(current_words & hist_words) / len(union_words)
                if similarity > max_similarity:
                    max_similarity = similarity
                    best_match = record["response"]

        return best_match

    def clear_history(self, userid: str, group_id: Optional[str] = None) -> bool:
        """清空用户历史记录，可选择清空特定群组"""
        userid_str = str(userid)
        try:
            if group_id is not None:
                # 只清空特定群组的记录
                all_history = self._read_all(userid_str)
                gid = str(group_id)
                if gid in all_history:
                    del all_history[gid]
                self._write_all(userid_str, all_history)
                logger.info(f"已清空用户 {userid_str} 在群组 {gid} 的历史记录")
            else:
                # 清空所有记录
                path = self._path(userid_str)
                if os.path.exists(path):
                    os.remove(path)
                logger.info(f"已清空用户 {userid_str} 的所有历史记录")
            
            self._cache.clear()
            return True
        except Exception as e:
            logger.error(f"清空历史记录失败 {userid_str}: {e}")
            return False

    def get_recent_history(self, userid: str, limit: int = 10,
                           group_id: Optional[str] = None) -> List[Dict[str, Any]]:
        history = self.load_history(userid, group_id=group_id)
        return history[-limit:]

    def has_history(self, userid: str) -> bool:
        return len(self._read_all(str(userid))) > 0

    def cleanup_old_entries(self, userid: str, max_age_days: int = 7) -> int:
        """清理过期的历史记录"""
        userid_str = str(userid)
        cutoff = datetime.now() - timedelta(days=max_age_days)
        all_history = self._read_all(userid_str)
        total_removed = 0
        
        for group_id, records in all_history.items():
            kept = []
            removed = 0
            for record in records:
                ts = record.get("timestamp", "")
                try:
                    dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
                except Exception:
                    kept.append(record)
                    continue
                if dt < cutoff:
                    removed += 1
                else:
                    kept.append(record)
            
            if removed > 0:
                all_history[group_id] = kept
                total_removed += removed
                logger.info(f"清理用户 {userid_str} 在群组 {group_id} 的 {removed} 条旧记录")
        
        if total_removed > 0:
            self._write_all(userid_str, all_history)
            self._cache.clear()
            logger.info(f"总共清理用户 {userid_str} 的 {total_removed} 条旧记录")
        
        return total_removed

    def get_storage_stats(self) -> Dict[str, Any]:
        """获取存储统计信息"""
        stats = {
            "user_count": 0,
            "record_count": 0,
            "response_count": 0,
            "group_count": 0,
            "top_groups": [],
            "storage_size_kb": 0.0,
        }
        try:
            group_counter = Counter()
            for name in os.listdir(self.history_dir):
                if not name.endswith(".json"):
                    continue
                stats["user_count"] += 1
                path = os.path.join(self.history_dir, name)
                stats["storage_size_kb"] += os.path.getsize(path) / 1024
                with open(path, "r", encoding="utf-8") as f:
                    records_dict = json.load(f)
                if not isinstance(records_dict, dict):
                    continue
                for group_id, records in records_dict.items():
                    if not isinstance(records, list):
                        continue
                    stats["record_count"] += len(records)
                    stats["response_count"] += sum(1 for r in records if r.get("response"))
                    if group_id != "global":
                        group_counter[group_id] += len(records)
            stats["storage_size_kb"] = round(stats["storage_size_kb"], 1)
            stats["group_count"] = len(group_counter)
            stats["top_groups"] = group_counter.most_common(3)
            return stats
        except Exception as e:
            logger.error(f"获取历史统计失败: {e}")
            return stats


history_manager = HistoryManager()


def load_history(userid: str, group_id: Optional[str] = None) -> List[Dict[str, Any]]:
    return history_manager.load_history(userid, group_id=group_id)


def save_history(userid: str, history: Dict[str, List[Dict[str, Any]]]) -> bool:
    return history_manager.save_history(userid, history)


def add_message_to_history(userid: str, message: str, response: Optional[str] = None,
                          group_id: Optional[str] = None) -> List[Dict[str, Any]]:
    return history_manager.add_message(userid, message, response, group_id=group_id)


def find_similar_response(userid: str, current_message: str, min_similarity: float = 0.3) -> Optional[str]:
    return history_manager.find_similar_response(userid, current_message, min_similarity)
