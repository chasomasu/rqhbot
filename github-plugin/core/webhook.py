from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable

from .closer import try_close_garbage_issue, try_close_garbage_pr
from .labeler import apply_labels_to_issue, auto_label_issue
from .llm import LLMClient
from .review import auto_review_pr, has_existing_review

logger = logging.getLogger(__name__)

_tracker: Any = None


def set_tracker(tracker: Any) -> None:
    global _tracker
    _tracker = tracker


async def handle_issue_opened(
    body: dict[str, Any],
    config: dict[str, Any],
    llm_client: LLMClient,
    store: Any,
    *,
    notify: Callable[[str], None] | None = None,
) -> None:
    """处理 Issue 被打开事件。"""
    issue = body.get("issue", {})
    repo_full = body.get("repository", {}).get("full_name", "")
    issue_number = issue.get("number", 0)
    logger.info("收到新 Issue #%d（仓库 %s）", issue_number, repo_full)

    # 垃圾检测
    closed = False
    if config.get("auto_close_garbage", True):
        closed = await try_close_garbage_issue(issue, repo_full, llm_client, config)
        if closed:
            logger.info("Issue #%d 被判定为垃圾，已自动关闭", issue_number)

    # 自动标签
    labels: list[str] = []
    if not closed and config.get("auto_label", True):
        try:
            labels = await auto_label_issue(issue, repo_full, config, llm_client)
            await apply_labels_to_issue(repo_full, issue_number, labels, config)
            logger.info("Issue #%d 自动标签: %s", issue_number, labels)
        except Exception as exc:
            logger.error("Issue #%d 自动标签失败: %s", issue_number, exc)

    # 智能回复
    if not closed and config.get("auto_comment", True):
        from .commenter import generate_issue_comment, post_comment
        try:
            comment = await generate_issue_comment(issue, labels, repo_full, llm_client, config)
            await post_comment(repo_full, issue_number, comment, config)
        except Exception as exc:
            logger.error("Issue #%d 智能回复失败: %s", issue_number, exc)

    # 入队跟踪器
    if not closed and _tracker is not None:
        await _tracker.enqueue(issue, repo_full, labels, config)

    # 通知管理员
    if not closed and notify:
        title = issue.get("title", "无标题")
        label_str = " ".join(f"[{l}]" for l in labels) if labels else "（未自动标签）"
        notify(
            f"新 Issue #{issue_number}: {title}\n"
            f"标签: {label_str}\n"
            f"仓库: {repo_full}"
        )


async def handle_pr_event(
    body: dict[str, Any],
    config: dict[str, Any],
    llm_client: LLMClient,
    *,
    notify: Callable[[str], None] | None = None,
) -> None:
    """处理 PR 事件（opened 或 synchronize）。"""
    pr = body.get("pull_request", {})
    repo_full = body.get("repository", {}).get("full_name", "")
    pr_number = pr.get("number", 0)
    action = body.get("action", "")
    logger.info("收到 PR #%d %s（仓库 %s）", pr_number, action, repo_full)

    # 垃圾检测
    if config.get("auto_close_garbage", True):
        closed = await try_close_garbage_pr(pr, repo_full, llm_client, config)
        if closed:
            logger.info("PR #%d 被判定为垃圾，已自动关闭", pr_number)
            return

    # 重复检查
    if action == "synchronize":
        already = await has_existing_review(repo_full, pr_number, config)
        if already:
            logger.info("PR #%d 已有审阅，跳过（synchronize）", pr_number)
            return

    # 自动审阅
    if config.get("auto_review", True):
        try:
            result = await auto_review_pr(
                pr, repo_full, llm_client, config,
                config.get("review_mode", "quick"),
            )
            if "error" in result:
                logger.error("PR #%d 自动审阅失败: %s", pr_number, result["error"])
                return
            logger.info("PR #%d 自动审阅完成: verdict=%s", pr_number, result.get("verdict", "?"))

            if notify:
                notify(
                    f"PR #{pr_number} 自动审阅完成"
                    f"\n仓库: {repo_full}"
                    f"\n结论: {result.get('verdict', 'N/A')}（{result.get('issues_count', 0)} 个问题）"
                    f"\n摘要: {result.get('summary', '')}"
                )
        except Exception as exc:
            logger.error("PR #%d 自动审阅异常: %s", pr_number, exc, exc_info=True)
