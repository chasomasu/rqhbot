"""独立入口 —— 替换原 SiriusChat 插件框架。

支持三种运行模式：
    python cli.py cli <command>      — 单次执行命令
    python cli.py poll               — 轮询守护模式
    python cli.py serve              — Webhook 服务器模式
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import signal
import sys
from pathlib import Path
from typing import Any

# 确保可以直接运行
_project_root = str(Path(__file__).resolve().parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from core.commands import handle_gh_command
from core.config import GithubAgentConfig
from core.llm import LLMClient
from core.store import JsonFileStore

logger = logging.getLogger(__name__)

_DEFAULT_CONFIG_PATH = "config.json"
_DEFAULT_STORE_PATH = "data/store.json"


# ═══════════════════════════════════════════════════════════════════════
# 配置加载
# ═══════════════════════════════════════════════════════════════════════


def load_config(path: str = _DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    """从 JSON 文件加载配置，若不存在则使用空默认值。"""
    cfg_path = Path(path)
    if cfg_path.exists():
        try:
            raw = json.loads(cfg_path.read_text(encoding="utf-8"))
            logger.info("已加载配置: %s", path)
            return raw
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("加载配置失败 %s: %s", path, exc)
    else:
        logger.warning("配置文件不存在: %s，使用默认配置", path)
    return {}


# ═══════════════════════════════════════════════════════════════════════
# 通知回调
# ═══════════════════════════════════════════════════════════════════════


def _default_notify(msg: str) -> None:
    """默认通知回调：输出到 INFO 日志。"""
    logger.info("[NOTIFY] %s", msg)


# ═══════════════════════════════════════════════════════════════════════
# CLI 模式
# ═══════════════════════════════════════════════════════════════════════


async def run_cli(args: argparse.Namespace, config: dict, store: JsonFileStore, llm: LLMClient) -> None:
    """单次执行 CLI 命令。"""
    command_str = " ".join(args.command) if args.command else ""
    if not command_str:
        print("用法: python -m gh_agent cli <command>")
        print("命令示例: status <task_id>")
        print("         review <pr_number> [quick|deep]")
        print("         <task_id> auto")
        return

    parts = command_str.split()
    admin_id = config.get("admin_user_id", "")

    # 判断是否为 /gh review 命令
    if parts[0] == "review":
        result = await handle_gh_command(
            command_args=command_str,
            config=config,
            llm_client=llm,
            store=store,
            admin_id=admin_id,
            notify=_default_notify,
        )
    else:
        # <task_id> auto|status|abort
        task_id = parts[0]
        action = parts[1] if len(parts) > 1 else "status"
        result = await handle_gh_command(
            command_args=f"{task_id} {action}",
            config=config,
            llm_client=llm,
            store=store,
            admin_id=admin_id,
            notify=_default_notify,
        )

    print(result)


# ═══════════════════════════════════════════════════════════════════════
# Poll 轮询模式
# ═══════════════════════════════════════════════════════════════════════


async def run_poll(config: dict, store: JsonFileStore, llm: LLMClient) -> None:
    """启动轮询守护模式。"""
    from core.poller import start_polling_loop

    on_stop = asyncio.Event()

    def _signal_handler() -> None:
        logger.info("收到停止信号，正在退出...")
        on_stop.set()

    # 注册信号处理
    try:
        loop = asyncio.get_running_loop()
        if sys.platform != "win32":
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, _signal_handler)
        else:
            # Windows: 通过 KeyboardInterrupt 处理
            pass
    except NotImplementedError:
        pass

    logger.info("启动轮询模式...")
    poll_task = await start_polling_loop(
        config=config,
        llm_client=llm,
        store=store,
        notify=_default_notify,
        on_stop=on_stop,
    )

    try:
        await on_stop.wait()
    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("轮询任务被中断")
    finally:
        on_stop.set()
        poll_task.cancel()
        try:
            await poll_task
        except (asyncio.CancelledError, Exception):
            pass
        logger.info("轮询模式已退出")


# ═══════════════════════════════════════════════════════════════════════
# Serve Webhook 模式
# ═══════════════════════════════════════════════════════════════════════


async def run_serve(config: dict, store: JsonFileStore, llm: LLMClient) -> None:
    """启动 Webhook HTTP 服务器模式。"""
    import hashlib
    import hmac
    from http import HTTPStatus
    from http.server import HTTPServer, BaseHTTPRequestHandler

    host = config.get("webhook_host", "0.0.0.0")
    port = int(config.get("webhook_port", 8080))
    webhook_secret = config.get("webhook_secret", "").encode() if config.get("webhook_secret") else None

    from core.webhook import handle_issue_opened, handle_pr_event

    async def _process_webhook(body: dict, event_type: str) -> None:
        """异步处理 webhook 事件，不阻塞 HTTP 响应。"""
        try:
            if event_type == "issues" and body.get("action") == "opened":
                await handle_issue_opened(
                    body, config, llm, store, notify=_default_notify,
                )
            elif event_type == "pull_request" and body.get("action") in ("opened", "synchronize"):
                await handle_pr_event(
                    body, config, llm, notify=_default_notify,
                )
            else:
                logger.debug("跳过未处理的事件类型: %s / %s", event_type, body.get("action"))
        except Exception as exc:
            logger.error("处理 webhook 事件异常: %s", exc, exc_info=True)

    class _WebhookHandler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            content_length = int(self.headers.get("Content-Length", 0))
            body_bytes = self.rfile.read(content_length)
            event_type = self.headers.get("X-GitHub-Event", "")
            delivery_id = self.headers.get("X-GitHub-Delivery", "")

            # 校验签名
            if webhook_secret:
                sig_header = self.headers.get("X-Hub-Signature-256", "")
                expected = "sha256=" + hmac.new(webhook_secret, body_bytes, hashlib.sha256).hexdigest()
                if not hmac.compare_digest(sig_header, expected):
                    logger.warning("Webhook 签名校验失败: delivery=%s", delivery_id)
                    self.send_response(HTTPStatus.UNAUTHORIZED)
                    self.end_headers()
                    return

            try:
                body = json.loads(body_bytes)
            except json.JSONDecodeError:
                logger.warning("Webhook JSON 解析失败: delivery=%s", delivery_id)
                self.send_response(HTTPStatus.BAD_REQUEST)
                self.end_headers()
                return

            # 异步处理事件（在新的事件循环中）
            asyncio.run_coroutine_threadsafe(
                _process_webhook(body, event_type),
                asyncio.get_event_loop(),
            )

            self.send_response(HTTPStatus.OK)
            self.end_headers()
            self.wfile.write(b"OK")

        def log_message(self, format: str, *args: Any) -> None:
            logger.debug("HTTP: " + format, *args)

    server = HTTPServer((host, port), _WebhookHandler)
    logger.info("Webhook 服务器已启动: http://%s:%s", host, port)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Webhook 服务器已停止")
    finally:
        server.server_close()


# ═══════════════════════════════════════════════════════════════════════
# 入口
# ═══════════════════════════════════════════════════════════════════════


def main() -> None:
    parser = argparse.ArgumentParser(description="GitHub Coding Agent - 独立版")
    parser.add_argument(
        "mode", choices=["cli", "poll", "serve"],
        help="运行模式: cli(单次命令) / poll(轮询守护) / serve(Webhook服务器)",
    )
    parser.add_argument(
        "command", nargs=argparse.REMAINDER,
        help="CLI 模式的命令参数，如: status <task_id>",
    )
    parser.add_argument(
        "--config", "-c", default=_DEFAULT_CONFIG_PATH,
        help=f"配置文件路径 (默认: {_DEFAULT_CONFIG_PATH})",
    )
    parser.add_argument(
        "--store", "-s", default=_DEFAULT_STORE_PATH,
        help=f"数据存储路径 (默认: {_DEFAULT_STORE_PATH})",
    )
    parser.add_argument(
        "--log-level", default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="日志级别 (默认: INFO)",
    )

    args = parser.parse_args()

    # 配置日志
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    # 加载配置
    config = load_config(args.config)

    # 初始化基础设施
    store = JsonFileStore(args.store)
    llm = LLMClient.from_config(config)

    # 根据模式启动
    if args.mode == "cli":
        asyncio.run(run_cli(args, config, store, llm))
    elif args.mode == "poll":
        try:
            asyncio.run(run_poll(config, store, llm))
        except KeyboardInterrupt:
            logger.info("用户中断")
    elif args.mode == "serve":
        try:
            asyncio.run(run_serve(config, store, llm))
        except KeyboardInterrupt:
            logger.info("用户中断")


if __name__ == "__main__":
    main()
