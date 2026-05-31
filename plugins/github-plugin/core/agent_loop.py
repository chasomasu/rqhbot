from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any

from .api import create_pr, fork_repo, sync_fork, get_default_branch
from .llm import LLMClient
from .skills import (
    ToolRegistry,
    build_default_registry,
    set_workspace_root,
)
from .stream_writer import StreamWriter

logger = logging.getLogger(__name__)

_VIEWER_SCRIPT = "console_viewer.py"


async def run_agent_loop(
    task_data: dict[str, Any],
    config: dict[str, Any],
    llm_client: LLMClient,
    tool_registry: ToolRegistry | None = None,
) -> dict[str, Any]:
    """Agent 主循环：分析 Issue → 收集信息 → 修改代码 → 测试 → PR。

    Args:
        task_data: {task_id, repo, issue_number, issue_title, issue_body, labels, status}
        config: 插件全局配置
        engine_proxy: LLM 引擎代理
        tool_registry: 注入自定义工具（默认 build_default_registry）

    Returns:
        {"success": bool, "pr_url": str, "summary": str}
    """
    repo = task_data.get("repo", "")
    issue_number = task_data.get("issue_number", 0)
    issue_title = task_data.get("issue_title", "")
    issue_body = task_data.get("issue_body", "")
    task_id = task_data.get("task_id", "unknown")

    workspace_dir = Path(config.get("workspace_dir", "data/github_workspace"))
    task_ws = workspace_dir / task_id
    event_stream = StreamWriter(task_ws / "_events.jsonl")

    if tool_registry is None:
        tool_registry = build_default_registry()
    set_workspace_root(task_ws)

    event_stream.write("phase", "PREPARATION", f"仓库 {repo} Issue #{issue_number}")
    event_stream.write("think", f"开始处理 Issue: {issue_title}")

    logger.info("[Agent] 工作区: %s", task_ws)
    logger.info("[Agent] 仓库: %s Issue: #%d", repo, issue_number)

    if not config.get("github_write_token"):
        logger.warning("未配置 github_write_token，跳过 PR 提交阶段")

    try:
        # ── 1. Fork & Sync ──
        event_stream.write("phase", "ANALYSIS", f"Fork & 同步仓库 {repo}")
        fork_data = await fork_repo(repo, config)
        if fork_data is None:
            logger.info("[Agent] 跳过 Fork（可能已存在）")
        else:
            fork_name = fork_data.get("full_name", repo)
            logger.info("[Agent] Fork 仓库: %s", fork_name)

        await sync_fork(repo, config)

        # ── 2. Clone & Setup ──
        event_stream.write("phase", "ANALYSIS", "克隆仓库到工作区")
        repo_dir = await _clone_or_reset(task_ws, repo, config)
        if repo_dir is None:
            return _fail_result(event_stream, "克隆仓库失败")

        set_workspace_root(repo_dir)

        # ── 3. 读取 Issue 信息，获取仓库上下文 ──
        context_lines: list[str] = []
        from .api import get_readme as _get_readme

        readme = await _get_readme(repo, config)
        if readme:
            context_lines.append("=== README ===")
            context_lines.append(readme[:2000])

        from .api import get_repo_file_tree as _get_repo_file_tree

        tree = await _get_repo_file_tree(repo, config)
        if tree:
            context_lines.append("=== 目录结构 ===")
            for item in tree:
                icon = "📁" if item.get("type") == "dir" else "📄"
                context_lines.append(f"  {icon} {item.get('name', '?')}")

        # ── 4. LLM 分析问题 ──
        event_stream.write("phase", "ANALYSIS", "AI 分析 Issue")
        plan = await _plan_fix(
            repo, issue_number, issue_title, issue_body,
            "\n".join(context_lines),
            llm_client, config,
        )
        logger.info("[Agent] 修复方案: %s", plan[:200])

        # ── 5. 执行修复 ──
        event_stream.write("phase", "MODIFICATION", "AI 自动修复代码")
        success = await _execute_plan(
            repo_dir=repo_dir,
            plan=plan,
            tool_registry=tool_registry,
            llm_client=llm_client,
            event_stream=event_stream,
            config=config,
        )
        if not success:
            return _fail_result(event_stream, "自动修复失败")

        # ── 6. 测试 ──
        test_command = config.get("test_command", "")
        if test_command:
            event_stream.write("phase", "VALIDATION", f"运行测试: {test_command}")
            from .skills import run_local_test as _run_local_test

            test_result = await _run_local_test(test_command)
            event_stream.write("test_run", test_command,
                               test_result.get("success", False),
                               test_result.get("stdout", ""),
                               test_result.get("stderr", ""))
            if not test_result.get("success"):
                logger.warning("测试失败，继续尝试提交: %s", test_result.get("stderr", "")[:200])

        # ── 7. Commit & Push ──
        event_stream.write("phase", "COMMIT", "提交代码并创建 PR")
        pr_url = await _commit_and_push(repo_dir, repo, issue_number, issue_title, config, event_stream)

        if pr_url:
            event_stream.write("done", success=True,
                               summary=f"修复完成: {pr_url}",
                               pr_url=pr_url)
            logger.info("[Agent] 完成，PR: %s", pr_url)
            return {"success": True, "pr_url": pr_url, "summary": plan[:300]}

        event_stream.write("done", success=False, summary="PR 创建失败")
        return _fail_result(event_stream, "PR 创建失败")

    except Exception as e:
        logger.exception("[Agent] 执行异常")
        event_stream.write("error", message=str(e))
        return _fail_result(event_stream, str(e))


# ── 内部函数 ──


async def _clone_or_reset(workspace: Path, repo: str, config: dict) -> Path | None:
    """克隆仓库到工作区，若已存在则 git pull。"""
    repo_name = repo.split("/")[-1] if "/" in repo else repo
    repo_dir = workspace / repo_name

    if repo_dir.exists():
        logger.info("[Agent] 仓库已存在，git pull")
        try:
            proc = await asyncio.create_subprocess_exec(
                "git", "-C", str(repo_dir), "fetch", "--all",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await proc.wait()
            proc = await asyncio.create_subprocess_exec(
                "git", "-C", str(repo_dir), "reset", "--hard", "origin/HEAD",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await proc.wait()
            return repo_dir
        except Exception as e:
            logger.warning("Git pull 失败，尝试重新克隆: %s", e)
            shutil.rmtree(repo_dir, onexc=_handle_rm_error)

    parent = repo_dir.parent
    parent.mkdir(parents=True, exist_ok=True)

    token = config.get("github_write_token", "")
    clone_url = f"https://x-access-token:{token}@github.com/{repo}.git" if token else f"https://github.com/{repo}.git"

    try:
        proc = await asyncio.create_subprocess_exec(
            "git", "clone", clone_url, str(repo_dir),
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        ret = await proc.wait()
        if ret != 0:
            logger.error("克隆仓库失败: %s", repo)
            return None
        return repo_dir
    except FileNotFoundError:
        logger.error("未安装 git，无法克隆仓库")
        return None


def _handle_rm_error(func, path, exc_info) -> None:
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception:
        pass


async def _plan_fix(
    repo: str, issue_number: int, title: str, body: str,
    context: str, llm: LLMClient, config: dict,
) -> str:
    """LLM 制定修复方案。"""
    system = f"""你是一个高级软件工程师，需要根据 Issue 提出代码修改方案。

仓库: {repo}
Issue #{issue_number}: {title}

Issue 描述:
{body[:3000]}

仓库上下文:
{context[:3000]}

请输出详细的修复方案，包括：
1. 问题根因分析（1-2句）
2. 修改计划（列出需要修改的文件和具体改动）
3. 实现步骤

注意：方案要具体、可执行，后续会按照你的方案自动修改代码。"""
    try:
        return await llm.generate(prompt=system)
    except Exception:
        return "分析生成失败，请人工评估。"


async def _execute_plan(
    repo_dir: Path,
    plan: str,
    tool_registry: ToolRegistry,
    llm_client: LLMClient,
    event_stream: StreamWriter,
    config: dict,
) -> bool:
    """让 LLM 按方案一步步修改代码。"""
    from .api import close_issue as _close_issue

    repo = config.get("active_repos", [""])[0] if config.get("active_repos") else ""
    issue_number = 0

    system_prompt = f"""你是一个高级软件工程师，正在修改一个 GitHub Issue 对应的代码。

修复方案:
{plan}

你有以下工具可用：search_content/read_file_chunk/search_and_replace_block/run_local_test/done。

工作流程：
1. 先 search_content 了解相关代码
2. 用 read_file_chunk 查看具体代码
3. 用 search_and_replace_block 修改代码
4. 用 run_local_test 运行测试
5. 完成所有修改后调用 done

注意：
- 每次只改一个文件
- 修改后运行测试确认
- 全部完成后调用 done

工作区根目录: {repo_dir}"""
    messages = [{"role": "system", "content": system_prompt},
                {"role": "user", "content": f"请开始执行以下修复方案：\n\n{plan}"}]

    MAX_STEPS = 50
    for step in range(MAX_STEPS):
        try:
            response_text = ""
            async for chunk_type, text in llm_client.generate_stream(messages):
                if chunk_type == "reasoning":
                    event_stream.write("reasoning", text=text)
                elif chunk_type == "content":
                    event_stream.write("think", text=text)
                    response_text += text

            tool_call = json.loads(response_text) if response_text.strip().startswith("{") else None

            if tool_call and "tool" in tool_call:
                tool_name = tool_call["tool"]
                tool_args = tool_call.get("arguments", {})
                event_stream.write("tool_call", name=tool_name, arguments=tool_args)
                result = await tool_registry.call(tool_name, **tool_args)
                event_stream.write("tool_result", name=tool_name, result=result, success=True)
                messages.append({"role": "assistant", "content": response_text})
                messages.append({"role": "tool", "content": result, "tool_call_id": tool_name})

                if tool_name == "done":
                    return result == "DONE"
            else:
                messages.append({"role": "assistant", "content": response_text})
                messages.append({"role": "user", "content": "请继续或调用 done 完成。"})

        except Exception as e:
            logger.error("执行步骤 %d 失败: %s", step, e)
            event_stream.write("error", message=str(e))
            return False

    logger.warning("执行步骤达到上限 %d，终止", MAX_STEPS)
    return False


async def _commit_and_push(
    repo_dir: Path,
    repo: str,
    issue_number: int,
    title: str,
    config: dict,
    event_stream: StreamWriter,
) -> str:
    """Git 提交、推送并创建 PR。"""
    username = config.get("github_username", "")
    email = config.get("github_email", "")
    token = config.get("github_write_token", "")

    if not token:
        logger.warning("未配置 github_write_token，跳过提交")
        return ""

    fork_name = f"{username}/{repo.split('/')[-1]}" if username else repo

    try:
        proc = await asyncio.create_subprocess_exec(
            "git", "-C", str(repo_dir), "add", "-A",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.wait()

        if username and email:
            proc = await asyncio.create_subprocess_exec(
                "git", "-C", str(repo_dir), "config", "user.name", username,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await proc.wait()
            proc = await asyncio.create_subprocess_exec(
                "git", "-C", str(repo_dir), "config", "user.email", email,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await proc.wait()

        branch = f"fix/issue-{issue_number}"
        proc = await asyncio.create_subprocess_exec(
            "git", "-C", str(repo_dir), "checkout", "-b", branch,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.wait()

        proc = await asyncio.create_subprocess_exec(
            "git", "-C", str(repo_dir), "commit", "-m", f"fix: {title}\n\nAuto-fix for issue #{issue_number}",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.wait()

        remote_url = f"https://x-access-token:{token}@github.com/{fork_name}.git"
        proc = await asyncio.create_subprocess_exec(
            "git", "-C", str(repo_dir), "push", remote_url, branch,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        ret = await proc.wait()
        if ret != 0:
            logger.error("Push 失败")
            return ""

        from .api import get_default_branch as _get_default_branch

        default_branch = await _get_default_branch(repo, config)
        pr = await create_pr(
            repo=repo,
            title=f"fix: {title}",
            body=f"Auto-fix for issue #{issue_number}\n\nThis PR was automatically generated by the GitHub Agent.",
            head=f"{username}:{branch}" if username else branch,
            base=default_branch,
            config=config,
        )
        if pr:
            return pr.get("html_url", "")

        return ""

    except Exception as e:
        logger.exception("Git 操作失败")
        return ""


def _fail_result(event_stream: StreamWriter, reason: str) -> dict:
    logger.error("[Agent] 失败: %s", reason)
    return {"success": False, "pr_url": "", "summary": reason}
