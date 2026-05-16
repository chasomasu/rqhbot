# 数据管理模块 - 用户数据和状态管理
from .history_manager import history_manager, load_history
from .user_profile import user_profile_manager, UserProfile
from .style_learner import style_learner
from .personas import persona_manager, get_persona, list_personas, update_traits, get_traits, apply_preset
from .admin import admin_manager

__all__ = [
    'history_manager', 'load_history', 
    'user_profile_manager', 'UserProfile',
    'style_learner', 
    'persona_manager', 'get_persona', 'list_personas', 'update_traits', 'get_traits', 'apply_preset',
    'admin_manager'
]