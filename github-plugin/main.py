"""
GitHub 插件 —— rqhbot 标准插件入口

通过 /gh 指令在 QQ 中管理 GitHub Issues/PRs，支持自动审阅、标签、轮询检测。
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path
from typing import Any

# 将插件目录加入 sys.path，使 core.xxx 导入能正常工作
_PLUGIN_DIR = str(Path(__file__).resolve().parent)
if _PLUGIN_DIR not in sys.path:
    sys.path.insert(0, _PLUGIN_DIR)

from sdk.pluginsystem import PluginBase, filter_registry
from sdk.core.events import GroupMessageEvent, PrivateMessageEvent

logger = logging.getLogger(__name__)


class GithubPlugin(PluginBase):
    """GitHub Issue/PR 自动化管理插件"""

    def __init__(self) -> None:
        super().__init__()
        self.name = "GithubPlugin"
        self.version = "3.5.0"
        self.description = "GitHub Issue/PR 自动化管理，支持自动审阅、标签、评论、关闭垃圾 Issue/PR"
        self.author = "rqhbot"

        self._config: dict[str, Any] = {}
        self._store: Any = None
        self._llm: Any = None
        self._admin_id: str = ""
        self._poll_task: asyncio.Task[Any] | None = None

    async def on_load(self, api: Any, event_bus: Any, plugin_dir: Path | None = None) -> None:
        """加载插件配置、初始化存储和 LLM"""
        await super().on_load(api, event_bus, plugin_dir)

        # 加载配置
        self._config = await self.load_config("config.json")
        self._admin_id = self._config.get("admin_user_id", "")

        # 初始化键值存储
        from core.store import JsonFileStore

        pdir = self._resolve_plugin_dir()
        store_path = str(pdir / "data" / "store.json")
        self._store = JsonFileStore(store_path)

        # 初始化 LLM 客户端
        from core.llm import LLMClient

        self._llm = LLMClient.from_config(self._config)

        logger.info(
            "[%s] 配置加载完成，管理员: %s",
            self.name,
            self._admin_id or "未设置",
        )

        # 自动启动轮询（如果配置了 poll_interval_seconds > 0）
        if int(self._config.get("poll_interval_seconds", 0)) > 0:
            self._start_polling()

    async def on_unload(self) -> None:
        """卸载时停止轮询"""
        self._stop_polling()
        await super().on_unload()

    def _notify(self, msg: str) -> None:
        """通知回调：输出到 INFO 日志"""
        logger.info("[NOTIFY] %s", msg)

    # ── 轮询管理 ──

    def _start_polling(self) -> None:
        if self._poll_task is not None and not self._poll_task.done():
            return

        async def _poll_loop() -> None:
            from core.poller import start_polling_loop

            try:
                on_stop = asyncio.Event()
                poll_task = await start_polling_loop(
                    config=self._config,
                    llm_client=self._llm,
                    store=self._store,
                    notify=self._notify,
                    on_stop=on_stop,
                )
                await on_stop.wait()
            except asyncio.CancelledError:
                logger.info("轮询任务已取消")
            except Exception as e:
                logger.error("轮询异常: %s", e, exc_info=True)

        self._poll_task = self.create_task(_poll_loop())
        logger.info("GitHub 事件轮询已启动")

    def _stop_polling(self) -> None:
        if self._poll_task and not self._poll_task.done():
            self._poll_task.cancel()
            logger.info("GitHub 事件轮询已停止")

    # ── 消息发送 ──

    async def _send_reply(self, event: Any, text: str) -> None:
        if self.api is None:
            return
        group_id = getattr(event, "group_id", None)
        if group_id is not None:
            await self.api.send_group_message(int(group_id), text)
        else:
            user_id = getattr(event, "user_id", 0)
            await self.api.send_private_message(int(user_id), text)

    # ── 消息处理器 ──

    @filter_registry.group_filter(prefix="/gh")
    async def on_group_gh_command(self, event: GroupMessageEvent) -> None:
        """群聊 /gh 指令"""
        await self._handle_gh_command(event)

    @filter_registry.private_filter(prefix="/gh")
    async def on_private_gh_command(self, event: PrivateMessageEvent) -> None:
        """私聊 /gh 指令"""
        await self._handle_gh_command(event)

    async def _handle_gh_command(self, event: Any) -> None:
        text: str = event.message.plain_text.strip()

        # 权限检查
        user_id = str(event.user_id)
        if self._admin_id and user_id != self._admin_id:
            await self._send_reply(event, "你没有权限使用此命令")
            return

        command_args = text[len("/gh"):].strip()
        if not command_args:
            await self._send_reply(
                event,
                "用法: /gh <task_id> auto|status|abort\n"
                "      /gh review <pr_number> [quick|deep]",
            )
            return

        from core.commands import handle_gh_command

        result = await handle_gh_command(
            command_args=command_args,
            config=self._config,
            llm_client=self._llm,
            store=self._store,
            admin_id=self._admin_id,
            notify=self._notify,
        )
        await self._send_reply(event, result)
