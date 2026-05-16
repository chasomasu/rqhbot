"""
Provider 抽象层
统一管理所有 AI Provider（OpenAI 兼容），按 role 区分用途（classifier / chat）
"""
import threading
from typing import Optional, List, Dict
from joha.config.infrastructure.logger import tprint


class Provider:
    """单个 AI Provider"""

    def __init__(self, name: str, role: str, api_key: str, base_url: str, model: str):
        self.name = name
        self.role = role
        self.api_key = api_key
        self.base_url = base_url.rstrip("/") if base_url else ""
        self.model = model

    def __repr__(self):
        return f"Provider(name={self.name}, role={self.role}, model={self.model})"


class ProviderManager:
    """Provider 管理器（单例）"""

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
        self._lock = threading.RLock()
        self._providers: Dict[str, Provider] = {}
        self._default_for_role: Dict[str, str] = {}
        self._load()

    def _load(self):
        from joha.config.managers.config_manager import config as config_manager

        # 从 llm.providers 获取配置
        providers_cfg: List[Dict] = config_manager.get("llm.providers", [])
            
        for p in providers_cfg:
            name = p.get("name", "")
            role = p.get("role", "chat")
            api_key = p.get("api_key", "")
            base_url = p.get("base_url", "")
            model = p.get("model", "")
            disabled = p.get("disabled", False)

            if not name or not api_key:
                continue
            
            # 跳过禁用的提供商
            if disabled:
                tprint("warning", f"[ProviderManager] 跳过禁用的提供商: {name} (原因: {p.get('disabled_reason', '未说明')})")
                continue

            self._providers[name] = Provider(name, role, api_key, base_url, model)

            if p.get("default", False):
                self._default_for_role[role] = name

    def reload(self):
        with self._lock:
            self._providers.clear()
            self._default_for_role.clear()
            self._load()

    def get(self, name: str) -> Optional[Provider]:
        return self._providers.get(name)

    def get_default(self, role: str) -> Optional[Provider]:
        name = self._default_for_role.get(role)
        if name:
            return self._providers.get(name)
        for p in self._providers.values():
            if p.role == role:
                return p
        return None

    def list_by_role(self, role: str) -> List[Provider]:
        return [p for p in self._providers.values() if p.role == role]

    def list_all(self) -> List[Provider]:
        return list(self._providers.values())

    def add_or_update(self, name: str, role: str, api_key: str, base_url: str, model: str, default: bool = False):
        from joha.config.managers.config_manager import config as config_manager

        # 从 llm.providers 获取配置
        providers_cfg: List[Dict] = config_manager.get("llm.providers", [])
            
        found = False
        for p in providers_cfg:
            if p.get("name") == name:
                p.update({"role": role, "api_key": api_key, "base_url": base_url, "model": model, "default": default})
                found = True
                break
        if not found:
            providers_cfg.append({"name": name, "role": role, "api_key": api_key, "base_url": base_url, "model": model, "default": default})

        if default:
            for p in providers_cfg:
                if p.get("name") != name and p.get("role") == role:
                    p["default"] = False

        config_manager.set("llm.providers", providers_cfg)
        config_manager.save()
        self.reload()

    def remove(self, name: str):
        from joha.config.managers.config_manager import config as config_manager

        # 从 llm.providers 获取配置
        providers_cfg: List[Dict] = config_manager.get("llm.providers", [])
            
        providers_cfg = [p for p in providers_cfg if p.get("name") != name]
        
        config_manager.set("llm.providers", providers_cfg)
        config_manager.save()
        self.reload()


provider_manager = ProviderManager()
