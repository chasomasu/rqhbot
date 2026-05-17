from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable

from .api import get_pr
from .agent_loop import run_agent_loop
from .llm import LLMClient
from .store import JsonFileStore

logger = logging.getLogger(__name__)


async def handle_gh_command(
    command_args: str,
    config: dict,
    llm_client: LLMClient,
    store: JsonFileStore,
    admin_id: str = "",
    notify: Callable[[str], None] | None = None,
) -> str:
    """处理 /gh 指令的统一入口。

    指令格式:
        /gh <task_id> auto                  — 启动自动修复
        /gh <task_id> status                — 查询任务状态
        /gh <task_id> abort                 — 中止任务
        /gh review <pr_number> [quick|deep] — 手动触发 PR 审阅（单仓库）
        /gh review <repo_index> <pr_number> [quick|deep] — 手动触发 PR 审阅（多仓库）
    """
    parts = command_args.strip().split()
    if not parts:
        return "用法: /gh <task_id> auto|status|abort 或 /gh review [<repo_index>] <pr_number> [quick|deep]"

    # ── /gh review [<repo_index>] <pr_number> [mode] ──
    if parts[0] == "review":
        return await _handle_review_command(parts, config, llm_client, admin_id, notify)

    task_id = parts[0]
    action = parts[1] if len(parts) > 1 else "auto"

    if action == "auto":
        return await _handle_auto_command(task_id, config, llm_client, store, notify)
    elif action == "status":
        return await _handle_status_command(task_id, store)
    elif action == "abort":
        return await _handle_abort_command(task_id, store)
    else:
        return f"未知操作: {action}"


async def _handle_auto_command(
    task_id: str,
    config: dict,
    llm_client: LLMClient,
    store: JsonFileStore,
    notify: Callable[[str], None] | None = None,
) -> str:
    """启动自动修复。数据从 tracker 中读取。"""
    from .tracker import _PREFIX

    raw = store.get(f"{_PREFIX}{task_id}")
    if raw is None:
        raw = store.get(f"task_{task_id}")
    if raw is None:
        return f"未找到任务 {task_id}"

    state_dict = raw if isinstance(raw, dict) else {}
    task_data = {
        "task_id": task_id,
        "repo": state_dict.get("repo", ""),
        "issue_number": state_dict.get("issue_number", 0),
        "issue_title": state_dict.get("title", ""),
        "issue_body": state_dict.get("body", ""),
        "labels": state_dict.get("labels", []),
        "status": "APPROVED",
    }

    state_dict["status"] = "FIXING"
    store.set(f"{_PREFIX}{task_id}", state_dict)

    asyncio.create_task(
        run_agent_loop(
            task_data=task_data,
            config=config,
            llm_client=llm_client,
        )
    )
    return f"任务已启动：Issue #{task_data.get('issue_number', '?')}"


async def _handle_status_command(task_id: str, store: JsonFileStore) -> str:
    """查询任务状态（优先从 tracker 读取）。"""
    from .tracker import _PREFIX

    raw = store.get(f"{_PREFIX}{task_id}")
    if raw is None:
        raw = store.get(f"task_{task_id}")
    if raw is None:
        return f"未找到任务 {task_id}"

    state = raw if isinstance(raw, dict) else {"data": str(raw)}
    status = state.get("status", "UNKNOWN")
    status_desc = {
        "GATHERING_INFO": "后台收集信息中",
        "AWAITING_RESPONSE": f"等待用户回复（已追问 {state.get('questions_asked', 0)} 次）",
        "READY": "信息就绪，等待修复指令",
        "APPROVED": "已批准，等待执行",
        "FIXING": "修复中",
        "DONE": "已完成",
        "CLOSED": "已关闭",
        "PENDING_APPROVAL": "待审批",
        "ABORTED": "已中止",
    }
    return (
        f"任务 {task_id} 状态:\n"
        f"Issue: #{state.get('issue_number', '?')} - {state.get('title', '')}\n"
        f"状态: {status_desc.get(status, status)}\n"
        f"仓库: {state.get('repo', 'N/A')}\n"
        f"标签: {' '.join(state.get('labels', [])) or '无'}\n"
        f"理解: {state.get('gathered_summary', '—') or '—'}"
    )


async def _handle_abort_command(task_id: str, store: JsonFileStore) -> str:
    """中止任务。"""
    from .tracker import _PREFIX

    raw = store.get(f"{_PREFIX}{task_id}")
    if raw is None:
        raw = store.get(f"task_{task_id}")
    if raw is None:
        return f"未找到任务 {task_id}"
    state = raw if isinstance(raw, dict) else {"data": str(raw)}
    state["status"] = "ABORTED"
    store.set(f"{_PREFIX}{task_id}", state)
    return f"任务 {task_id} 已中止"


async def _handle_review_command(
    parts: list[str],
    config: dict,
    llm_client: LLMClient,
    admin_id: str = "",
    notify: Callable[[str], None] | None = None,
) -> str:
    """处理 /gh review 指令，支持多仓库。

    用法：
        /gh review <pr_number> [quick|deep]           — 单仓库，自动选择
        /gh review <repo_index> <pr_number> [quick|deep] — 多仓库，指定索引
    """
    repos = config.get("repos", [])
    if not repos:
        return "未绑定仓库，请检查配置"

    if len(parts) < 2:
        return "用法: /gh review [<repo_index>] <pr_number> [quick|deep]"

    repo: str
    pr_number: int
    try:
        first_num = int(parts[1])
    except ValueError:
        return f"无效的 PR 编号或仓库索引: {parts[1]}"

    if len(parts) >= 3:
        try:
            third_num = int(parts[2])
        except ValueError:
            repo = _resolve_repo(repos, None)
            pr_number = first_num
        else:
            repo = _resolve_repo(repos, first_num)
            pr_number = third_num
    elif len(repos) == 1:
        repo = repos[0]
        pr_number = first_num
    else:
        return (
            f"检测到 {len(repos)} 个绑定仓库，请指定索引:\n"
            + "\n".join(f"  [{i}] {r}" for i, r in enumerate(repos))
            + f"\n\n用法: /gh review <索引> <pr_number> [quick|deep]"
        )

    if not repo:
        return "无法确定仓库，请检查绑定配置"

    mode = "quick"
    if len(parts) >= 3:
        candidate = parts[-1]
        if candidate in ("quick", "deep"):
            mode = candidate

    pr_data = await get_pr(repo, pr_number, config)
    if pr_data is None:
        return f"未找到 PR #{pr_number}（仓库 {repo}）"

    from .review import auto_review_pr

    async def _run_review():
        try:
            result = await auto_review_pr(pr_data, repo, llm_client, config, mode)
            if "error" in result:
                logger.error("PR #%d 审阅失败: %s", pr_number, result["error"])
                return
            if admin_id and notify:
                pr_url = pr_data.get("html_url", "")
                notify(
                    f"PR #{pr_number} 自动审阅完成（{mode}模式）\n"
                    f"仓库: {repo}\n"
                    f"结论: {result.get('verdict', 'N/A')}（{result.get('issues_count', 0)} 个问题）\n"
                    f"摘要: {result.get('summary', '')}\n"
                    f"链接: {pr_url}"
                )
        except Exception as exc:
            logger.error("PR 审阅异常: %s", exc)

    asyncio.create_task(_run_review())
    return f"已启动 {mode} 模式审阅 PR #{pr_number}（仓库 {repo}）"


def _resolve_repo(repos: list[str], index: int | None) -> str:
    """根据索引解析仓库，None 时自动选唯一的。"""
    if index is not None and 0 <= index < len(repos):
        return repos[index]
    if len(repos) == 1:
        return repos[0]
    return ""
