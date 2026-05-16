"""
配置管理器 - 统一管理所有配置
支持环境变量和配置文件
"""
import os
import json
import threading
from typing import Dict, Any, Optional, List
from pathlib import Path
from joha.config.infrastructure.logger import tprint


class ConfigManager:
    """配置管理器（线程安全）"""

    def __init__(self, config_path: str = None):
        self.config_path = Path(config_path) if config_path else Path(__file__).parent / "config.json"
        self._config: Dict[str, Any] = {}
        self._config_lock = threading.RLock()
        self.load()

    # ==================== 基础操作 ====================

    def load(self) -> None:
        """加载配置文件"""
        with self._config_lock:
            if self.config_path.exists():
                try:
                    with open(self.config_path, 'r', encoding='utf-8') as f:
                        self._config = json.load(f)
                except json.JSONDecodeError as e:
                    tprint("warning", f"警告: 配置文件格式错误: {e}")
                    self._config = {}
            else:
                self._config = {}
            self._load_env_overrides()

    def _load_env_overrides(self) -> None:
        """从环境变量加载配置覆盖"""
        # 注意：现在所有 LLM 配置都在 providers 数组中管理
        # 环境变量覆盖功能暂时保留，但不再使用 llm.api_key 等顶层配置
        pass

    def _get_nested_value(self, path: str) -> Any:
        """获取嵌套配置值"""
        keys = path.split('.')
        value = self._config
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None
        return value

    def _set_nested_value(self, path: str, value: Any) -> None:
        """设置嵌套配置值"""
        keys = path.split('.')
        config = self._config
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        config[keys[-1]] = value

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值（支持点号路径）"""
        with self._config_lock:
            result = self._get_nested_value(key)
            return result if result is not None else default

    def set(self, key: str, value: Any) -> None:
        """设置配置值（支持点号路径）"""
        with self._config_lock:
            self._set_nested_value(key, value)

    def save(self) -> None:
        """保存配置文件"""
        with self._config_lock:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, ensure_ascii=False, indent=2)

    def get_nested(self, *keys, default=None):
        """获取多层嵌套配置（变参版本）"""
        with self._config_lock:
            value = self._config
            for key in keys:
                if isinstance(value, dict) and key in value:
                    value = value[key]
                else:
                    return default
            return value

    def set_nested(self, *keys, value):
        """设置多层嵌套配置并保存（变参版本）"""
        with self._config_lock:
            full_path = '.'.join(keys)
            self._set_nested_value(full_path, value)
            self.save()

    # ==================== LLM配置属性 ====================

    @property
    def llm_api_key(self) -> str:
        """获取当前激活 provider 的 API Key"""
        provider = self.get_active_provider()
        if provider:
            return provider.get('api_key', '')
        # 如果没有激活的 provider，返回空字符串
        return ''

    @property
    def llm_base_url(self) -> str:
        """获取当前激活 provider 的 Base URL"""
        provider = self.get_active_provider()
        if provider:
            return provider.get('base_url', '')
        # 如果没有激活的 provider，返回空字符串
        return ''

    @property
    def llm_model(self) -> str:
        """获取当前激活 provider 的 Model"""
        provider = self.get_active_provider()
        if provider:
            return provider.get('model', '')
        # 如果没有激活的 provider，返回空字符串
        return ''

    @property
    def admins(self) -> list:
        return self.get('admin.admins', [])



    # ==================== 多 Provider 管理 ====================

    def get_llm_providers(self) -> List[Dict]:
        """获取所有 LLM Provider 配置列表"""
        return self.get('llm.providers', [])

    def get_active_provider_name(self) -> str:
        """获取当前激活的 Provider 名称"""
        return self.get('llm.active_provider', '')

    def get_active_provider(self) -> Optional[Dict]:
        """获取当前激活的完整 Provider 配置"""
        name = self.get_active_provider_name()
        if not name:
            return None
        providers = self.get_llm_providers()
        for p in providers:
            if p.get('name') == name:
                return p
        return None

    def switch_provider(self, name: str) -> bool:
        """切换 LLM Provider

        Args:
            name: Provider 名称

        Returns:
            是否切换成功
        """
        with self._config_lock:
            providers = self.get_llm_providers()
            target = None
            for p in providers:
                if p.get('name') == name:
                    target = p
                    break
            if not target:
                return False

            # 只更新 active_provider，其他配置从 providers 数组中动态获取
            self._set_nested_value('llm.active_provider', name)
            self.save()
            return True

    def format_providers_list(self) -> str:
        """格式化输出所有 Provider 列表"""
        active = self.get_active_provider_name()
        providers = self.get_llm_providers()
        if not providers:
            return "暂无配置的 Provider"

        lines = []
        for p in providers:
            marker = "✅ " if p.get('name') == active else "   "
            label = p.get('label', p['name'])
            model = p.get('model', '')
            lines.append(f"{marker}{p['name']} - {label} ({model})")
        return "\n".join(lines)

    def get_available_models(self, role: str = "chat") -> List[Dict]:
        """获取指定角色的可用模型列表
        
        Args:
            role: 角色类型 (chat 或 classifier)
            
        Returns:
            模型列表，每个元素包含 name, label, model 等信息
        """
        providers = self.get_llm_providers()
        models = []
        for p in providers:
            if p.get('role') == role:
                models.append({
                    'name': p.get('name'),
                    'label': p.get('label', p.get('name')),
                    'model': p.get('model'),
                    'base_url': p.get('base_url'),
                    'default': p.get('default', False)
                })
        return models

    def get_model_names(self, role: str = "chat") -> List[str]:
        """获取指定角色的模型名称列表
        
        Args:
            role: 角色类型 (chat 或 classifier)
            
        Returns:
            模型名称列表
        """
        models = self.get_available_models(role)
        return [m['name'] for m in models]


    # ==================== Provider 相关方法 ====================

    def get_providers(self) -> List[Dict]:
        """获取所有 providers（从 llm.providers 读取）"""
        with self._config_lock:
            return self.get('llm.providers', [])

    def get_provider_by_role(self, role: str, default: bool = None) -> Optional[Dict]:
        """根据角色获取 provider"""
        with self._config_lock:
            providers = self.get_providers()
            for provider in providers:
                if provider.get("role") == role:
                    if default is None or provider.get("default") == default:
                        return provider
            return None


# 全局配置实例
config = ConfigManager()
