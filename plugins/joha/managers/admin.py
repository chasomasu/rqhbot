"""
统一的管理员管理系统
"""
import json
import threading
from typing import List
from joha.config.managers.config_manager import config
from joha.config.infrastructure.logger import tprint


class AdminManager:
    """统一的管理员管理器（单例）"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.config_path = config.config_path
        self._config_lock = threading.RLock()
        self._sync_admins()
    
    def _read_admins(self) -> List[str]:
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                admins = data.get('admin', {}).get('admins', [])
                if isinstance(admins, list):
                    return [str(admin) for admin in admins]
        except Exception as e:
            tprint("warning", f"[AdminManager] 实时读取管理员配置失败: {e}")
        admins = config.get('admin.admins', [])
        return [str(admin) for admin in admins] if isinstance(admins, list) else []

    def _sync_admins(self):
        """初始化管理员列表"""
        with self._config_lock:
            # 确保 admin.admins 配置存在
            admins = config.get('admin.admins', [])
            if not isinstance(admins, list):
                config.set('admin.admins', [])
                config.save()
    
    def is_admin(self, user_id: int) -> bool:
        """检查用户是否为管理员"""
        with self._config_lock:
            admins = set(self._read_admins())
            return str(user_id) in admins
    
    def get_admins(self) -> List[str]:
        """获取所有管理员列表"""
        with self._config_lock:
            return self._read_admins()
    
    def add_admin(self, user_id: int) -> bool:
        """添加管理员"""
        with self._config_lock:
            str_id = str(user_id)
            admins = set(self._read_admins())
            
            if str_id in admins:
                return False
            
            admins.add(str_id)
            admins_list = list(admins)
            
            config.load()
            config.set('admin.admins', admins_list)
            config.save()
            
            tprint("info", f"[AdminManager] 已添加管理员: {user_id}")
            return True
    
    def remove_admin(self, user_id: int) -> bool:
        """移除管理员"""
        with self._config_lock:
            str_id = str(user_id)
            admins = set(self._read_admins())
            config.load()
            target_users = set(config.get('admin.target_users', []))
            
            # 不能删除 target_users 中的用户
            if str_id in target_users:
                tprint("warning", f"[AdminManager] 无法删除 target_user: {user_id}")
                return False
            
            if str_id not in admins:
                return False
            
            admins.remove(str_id)
            admins_list = list(admins)
            
            config.set('admin.admins', admins_list)
            config.save()
            
            tprint("info", f"[AdminManager] 已移除管理员: {user_id}")
            return True
    
    def get_admin_count(self) -> int:
        """获取管理员数量"""
        return len(self.get_admins())
    
    def is_target_user(self, user_id: int) -> bool:
        """检查是否为目标用户（不可删除的管理员）"""
        with self._config_lock:
            target_users = set(config.get('admin.target_users', []))
            return str(user_id) in target_users


# 全局管理员管理器实例
admin_manager = AdminManager()


# 兼容旧接口
def is_admin(user_id: int) -> bool:
    """检查是否为管理员（兼容旧接口）"""
    return admin_manager.is_admin(user_id)


def add_admin(user_id: int) -> bool:
    """添加管理员（兼容旧接口）"""
    return admin_manager.add_admin(user_id)


def remove_admin(user_id: int) -> bool:
    """移除管理员（兼容旧接口）"""
    return admin_manager.remove_admin(user_id)


def get_admin_list() -> List[str]:
    """获取管理员列表（兼容旧接口）"""
    return admin_manager.get_admins()
