"""
热重载插件管理器
支持插件热重载 —— 停止旧插件（取消事件订阅、清理资源）→ 重新导入 Python 模块 → 加载并启动新插件

与 PluginBase 的生命周期 (on_load / on_unload) 无缝配合：
  - on_load()    订阅事件到 EventBus，创建后台任务
  - on_unload()  取消所有事件订阅，取消所有后台任务
"""

from __future__ import annotations

import importlib
import importlib.util
import json
import logging
import sys
import types
from pathlib import Path
from typing import Any, Dict, List, Optional

from .plugin_base import PluginBase

logger = logging.getLogger("HotReloadPluginManager")


class HotReloadPluginManager:
    """热重载插件管理器

    管理所有插件的模块导入、实例生命周期和热重载。
    不持有 BotClient 引用，只依赖 IClient 和 EventBus。

    Attributes:
        plugin_dir: 插件根目录
        plugins:    已加载的插件实例 (name -> instance)
        plugin_modules: 已加载的插件 Python 模块 (name -> module)
    """

    def __init__(self, plugin_dir: str = "plugins") -> None:
        self.plugin_dir: Path = Path(plugin_dir)
        self.plugins: Dict[str, PluginBase] = {}
        self.plugin_modules: Dict[str, object] = {}

        # 将插件根目录的父目录（项目根目录）加入 sys.path，
        # 使 plugins.xxx 形式的包导入能正常工作
        root_dir = str(self.plugin_dir.parent)
        if root_dir not in sys.path:
            sys.path.insert(0, root_dir)

        # 预注册 plugins 命名空间包（即使目录下没有 __init__.py）
        if "plugins" not in sys.modules:
            plugins_pkg = types.ModuleType("plugins")
            plugins_pkg.__path__ = [str(self.plugin_dir)]
            plugins_pkg.__package__ = ""
            sys.modules["plugins"] = plugins_pkg

        # 插件配置缓存
        self._plugin_configs: Dict[str, Dict[str, Any]] = {}

    def _load_plugin_config(self, plugin_name: str) -> Dict[str, Any]:
        """加载插件配置 (plugin.json)

        Args:
            plugin_name: 插件名称

        Returns:
            插件配置字典，如果不存在或加载失败则返回默认配置
        """
        config_path = self.plugin_dir / plugin_name / "plugin.json"
        default_config = {
            "name": plugin_name,
            "version": "1.0.0",
            "description": "",
            "author": "Unknown",
            "enabled": True,
            "priority": 100,
            "dependencies": [],
            "python_requires": ">=3.8",
        }

        if not config_path.exists():
            return default_config

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            # 合并默认值
            for key, value in default_config.items():
                if key not in config:
                    config[key] = value
            self._plugin_configs[plugin_name] = config
            return config
        except Exception as e:
            logger.warning(f"加载插件配置 {plugin_name} 失败: {e}，使用默认配置")
            return default_config

    def _check_dependencies(self, plugin_name: str, dependencies: List[str]) -> bool:
        """检查插件依赖是否满足

        Args:
            plugin_name: 插件名称
            dependencies: 依赖列表

        Returns:
            是否所有依赖都满足
        """
        if not dependencies:
            return True

        missing = []
        for dep in dependencies:
            # 简单检查：尝试导入包名
            pkg_name = dep.split(">=")[0].split("<=")[0].split("==")[0].split("[")[0].strip()
            try:
                importlib.import_module(pkg_name)
            except ImportError:
                missing.append(dep)

        if missing:
            logger.error(f"插件 {plugin_name} 缺少依赖: {', '.join(missing)}")
            return False

        return True

    # ==================== 加载 / 重载 / 卸载 ====================

    async def load_plugin(
        self, plugin_name: str, api: Any, event_bus: Any
    ) -> bool:
        """加载（或重载）一个插件

        流程：
        1. 如果已加载，先卸载旧版
        2. 检查 plugin.json 配置（enabled、dependencies）
        3. 使用 importlib.reload() 重新导入 Python 模块
        4. 查找 PluginBase 子类并实例化
        5. 调用 instance.on_load() 完成事件订阅和初始化

        插件以完整包形式加载（如 plugins.yiyichat.main），
        预注册包到 sys.modules 避免 __init__.py 中的循环导入。

        Args:
            plugin_name: 插件名称（对应 plugins/<plugin_name>/ 目录）
            api:         IClient 实例
            event_bus:   EventBus 实例

        Returns:
            是否成功
        """
        # 如果已经加载，先卸载旧版（取消订阅 + 取消任务）
        if plugin_name in self.plugins:
            await self.unload_plugin(plugin_name)

        # 加载插件配置
        config = self._load_plugin_config(plugin_name)

        # 检查是否启用
        if not config.get("enabled", True):
            logger.info(f"插件 {plugin_name} 已禁用，跳过加载")
            return False

        # 检查依赖
        dependencies = config.get("dependencies", [])
        if not self._check_dependencies(plugin_name, dependencies):
            return False

        main_file = self.plugin_dir / plugin_name / "main.py"
        if not main_file.exists():
            logger.error(f"插件 {plugin_name} 入口不存在: {main_file}")
            return False

        try:
            pkg_name = f"plugins.{plugin_name}"
            module_name = f"{pkg_name}.main"

            # 预注册插件包，避免 __init__.py 中 from .main import XXX 导致的循环导入
            if pkg_name not in sys.modules:
                plugin_pkg = types.ModuleType(pkg_name)
                plugin_pkg.__path__ = [str(self.plugin_dir / plugin_name)]
                plugin_pkg.__package__ = "plugins"
                sys.modules[pkg_name] = plugin_pkg

            # 清理旧子模块缓存（包路径 + 旧扁平名兼容）
            self._clean_submodules(plugin_name)

            if module_name in sys.modules:
                # 已缓存 → 使用 importlib.reload() 重新执行模块代码
                module = importlib.reload(sys.modules[module_name])
            else:
                # 首次导入 → 从文件位置加载
                spec = importlib.util.spec_from_file_location(
                    module_name, main_file
                )
                if spec is None or spec.loader is None:
                    logger.error(f"无法加载插件模块: {main_file}")
                    return False
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)

            # 查找继承 PluginBase 的类（跳过基类本身）
            plugin_class: Optional[type] = None
            for attr_name in dir(module):
                attr: Any = getattr(module, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, PluginBase)
                    and attr is not PluginBase
                ):
                    plugin_class = attr
                    break

            if plugin_class is None:
                logger.error(f"插件 {plugin_name} 中未找到 PluginBase 子类")
                return False

            # 实例化并加载
            instance: PluginBase = plugin_class()
            await instance.on_load(api, event_bus, self.plugin_dir / plugin_name)

            self.plugins[plugin_name] = instance
            self.plugin_modules[plugin_name] = module

            logger.info(
                f"插件 {plugin_name} (v{instance.version}) 加载成功"
            )
            return True

        except Exception as e:
            logger.error(
                f"加载插件 {plugin_name} 失败: {e}", exc_info=True
            )
            return False

    async def unload_plugin(self, plugin_name: str) -> None:
        """卸载插件

        调用 PluginBase.on_unload() 清理事件订阅和后台任务，
        然后从内部记录中移除。

        Args:
            plugin_name: 插件名称
        """
        if plugin_name not in self.plugins:
            return

        instance = self.plugins[plugin_name]
        await instance.on_unload()

        del self.plugins[plugin_name]
        if plugin_name in self.plugin_modules:
            del self.plugin_modules[plugin_name]

        logger.info(f"插件 {plugin_name} 已卸载")

    async def reload_plugin(
        self, plugin_name: str, api: Any, event_bus: Any
    ) -> bool:
        """热重载指定插件

        封装了 unload + load 操作，是触发热重载的便捷入口。

        Args:
            plugin_name: 插件名称
            api:         IClient 实例
            event_bus:   EventBus 实例

        Returns:
            是否成功
        """
        logger.info(f"正在热重载插件: {plugin_name}")
        success = await self.load_plugin(plugin_name, api, event_bus)
        if success:
            logger.info(f"插件 {plugin_name} 热重载完成")
        else:
            logger.error(f"插件 {plugin_name} 热重载失败")
        return success

    # ==================== 批量操作 ====================

    async def load_all_plugins(self, api: Any, event_bus: Any) -> List[str]:
        """从插件目录加载所有插件

        扫描 self.plugin_dir 下每个子目录中的 main.py，
        依次调用 load_plugin() 进行加载。

        Args:
            api:        IClient 实例
            event_bus:  EventBus 实例

        Returns:
            成功加载的插件名称列表
        """
        loaded_names: List[str] = []
        if not self.plugin_dir.exists():
            logger.warning(f"插件目录不存在: {self.plugin_dir}")
            return loaded_names

        for entry in sorted(self.plugin_dir.iterdir()):
            if not entry.is_dir():
                continue
            main_file = entry / "main.py"
            if not main_file.exists():
                continue
            plugin_name = entry.name
            success = await self.load_plugin(plugin_name, api, event_bus)
            if success:
                loaded_names.append(plugin_name)

        return loaded_names

    async def unload_all_plugins(self) -> None:
        """卸载所有已加载的插件"""
        for plugin_name in list(self.plugins.keys()):
            await self.unload_plugin(plugin_name)

    # ==================== 查询 ====================

    def get_plugin(self, name: str) -> Optional[PluginBase]:
        """获取已加载的插件实例

        Args:
            name: 插件名称

        Returns:
            插件实例，未加载则返回 None
        """
        return self.plugins.get(name)

    def get_all_plugins(self) -> Dict[str, PluginBase]:
        """获取所有已加载的插件实例

        Returns:
            name -> instance 字典副本
        """
        return self.plugins.copy()

    # ==================== 内部工具 ====================

    @staticmethod
    def _clean_submodules(plugin_name: str) -> None:
        """清理指定插件的子模块 sys.modules 缓存

        例如插件名为 "abc"，则会删除 sys.modules 中所有
        以 "plugins.abc." 或旧扁平名 "rqhbot_plugin_abc_" 开头的模块，
        确保重载时子模块也被重新导入。

        Args:
            plugin_name: 插件名称
        """
        prefixes = (
            f"plugins.{plugin_name}.",
            f"rqhbot_plugin_{plugin_name}_",
        )
        to_delete = [
            mod_name
            for mod_name in sys.modules
            if any(mod_name.startswith(p) for p in prefixes)
        ]
        for mod_name in to_delete:
            del sys.modules[mod_name]
