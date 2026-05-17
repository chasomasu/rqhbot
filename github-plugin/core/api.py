"""Coding Agent GitHub API 封装。

基于 httpx 封装 Issue/PR/Label/Fork 等高级操作的快捷函数。
内嵌 _GitHubClient 替代原 sirius_chat.github.client 组件。
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════
# 内嵌 GitHub REST API 客户端（替代 sirius_chat.github.client）
# ═══════════════════════════════════════════════════════════════════════


class _GitHubClient:
    """异步 httpx 封装的 GitHub REST API 客户端。"""

    _BASE = "https://api.github.com"

    def __init__(self, token: str) -> None:
        self._token = token
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> _GitHubClient:
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "SiriusCodingAgent/2.2",
        }
        self._client = httpx.AsyncClient(
            base_url=self._BASE,
            headers=headers,
            timeout=30.0,
        )
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def get_json(self, path: str) -> dict[str, Any] | None:
        """GET 请求并解析 JSON 响应，失败返回 None。"""
        if self._client is None:
            raise RuntimeError("_GitHubClient 未初始化，请在 async with 块中使用")
        resp = await self._client.get(path)
        if resp.status_code == 200:
            return resp.json()
        logger.debug("GET %s 失败: %d %s", path, resp.status_code, resp.text[:200])
        return None

    async def get(self, path: str, params: dict | None = None, headers: dict | None = None) -> httpx.Response:
        """GET 请求，返回完整 Response。"""
        if self._client is None:
            raise RuntimeError("_GitHubClient 未初始化，请在 async with 块中使用")
        req_headers = dict(headers) if headers else {}
        return await self._client.get(path, params=params, headers=req_headers or None)

    async def post(self, path: str, json: dict | None = None) -> httpx.Response:
        """POST 请求，返回完整 Response。"""
        if self._client is None:
            raise RuntimeError("_GitHubClient 未初始化，请在 async with 块中使用")
        return await self._client.post(path, json=json)

    async def post_json(self, path: str, json: dict | None = None) -> dict[str, Any] | None:
        """POST 请求并解析 JSON 响应，失败返回 None。"""
        if self._client is None:
            raise RuntimeError("_GitHubClient 未初始化，请在 async with 块中使用")
        resp = await self._client.post(path, json=json)
        if resp.status_code in (200, 201):
            return resp.json()
        logger.error("POST %s 失败: %d %s", path, resp.status_code, resp.text[:200])
        return None

    async def patch(self, path: str, json: dict | None = None) -> httpx.Response:
        """PATCH 请求，返回完整 Response。"""
        if self._client is None:
            raise RuntimeError("_GitHubClient 未初始化，请在 async with 块中使用")
        return await self._client.patch(path, json=json)

    async def delete(self, path: str) -> httpx.Response:
        """DELETE 请求，返回完整 Response。"""
        if self._client is None:
            raise RuntimeError("_GitHubClient 未初始化，请在 async with 块中使用")
        return await self._client.delete(path)


def _github_headers(token: str, extra_accept: str = "") -> dict[str, str]:
    """构建 GitHub API 请求头，可指定额外的 Accept 头。"""
    headers: dict[str, str] = {
        "Authorization": f"Bearer {token}",
        "User-Agent": "SiriusCodingAgent/2.2",
    }
    if extra_accept:
        headers["Accept"] = extra_accept
    else:
        headers["Accept"] = "application/vnd.github.v3+json"
    return headers


# ═══════════════════════════════════════════════════════════════════════
# Token 与用户解析
# ═══════════════════════════════════════════════════════════════════════


def _token_for_repo(config: dict[str, Any], repo: str = "") -> str:
    """获取读操作 token，从 github_monitor 的 per-repo token 读取。"""
    monitor = config.get("_monitor")
    if monitor is not None and repo:
        token = monitor.get_token(repo)
        if token:
            return token
    return ""


def _write_token_for_repo(config: dict[str, Any], repo: str = "") -> str:
    """获取写操作 token。

    优先级：插件级 github_write_token > monitor per-repo token > 空。
    """
    explicit = config.get("github_write_token", "")
    if explicit:
        return explicit
    monitor = config.get("_monitor")
    if monitor is not None and repo:
        token = monitor.get_token(repo)
        if token:
            return token
    return ""


def _resolve_github_username(repo: str, config: dict[str, Any]) -> str:
    """解析 GitHub 用户名。

    优先级：配置 github_username > 仓库 owner（repo.split("/")[0]）> 空。
    """
    explicit = config.get("github_username", "")
    if explicit:
        return explicit
    return repo.split("/")[0] if "/" in repo else ""


# ═══════════════════════════════════════════════════════════════════════
# Issue / PR 查询
# ═══════════════════════════════════════════════════════════════════════


async def get_issue(repo: str, issue_number: int, config: dict[str, Any]) -> dict[str, Any] | None:
    async with _GitHubClient(_token_for_repo(config, repo)) as client:
        result = await client.get_json(f"/repos/{repo}/issues/{issue_number}")
        if result is None:
            logger.error("获取 Issue #%d 失败", issue_number)
        return result


async def is_issue_closed(repo: str, issue_number: int, config: dict[str, Any]) -> bool:
    """检查 GitHub 侧 Issue 是否已关闭（轻量，只取 state 字段）。"""
    async with _GitHubClient(_token_for_repo(config, repo)) as client:
        result = await client.get_json(f"/repos/{repo}/issues/{issue_number}")
        if isinstance(result, dict):
            return result.get("state", "open") == "closed"
        logger.debug("检查 Issue #%d 状态失败，假定未关闭", issue_number)
        return False


async def get_issue_comments(
    repo: str, issue_number: int, config: dict[str, Any], *, since: str | None = None
) -> list[dict[str, Any]]:
    """获取 Issue 评论列表，可按 since (ISO timestamp) 增量拉取。"""
    params: dict[str, Any] = {"per_page": 100, "sort": "created", "direction": "asc"}
    if since:
        params["since"] = since
    async with _GitHubClient(_token_for_repo(config, repo)) as client:
        resp = await client.get(f"/repos/{repo}/issues/{issue_number}/comments", params=params)
        if resp.status_code == 200:
            return resp.json()
        logger.error("获取 Issue #%d 评论失败: %d", issue_number, resp.status_code)
        return []


async def get_pr(repo: str, pr_number: int, config: dict[str, Any]) -> dict[str, Any] | None:
    async with _GitHubClient(_token_for_repo(config, repo)) as client:
        result = await client.get_json(f"/repos/{repo}/pulls/{pr_number}")
        if result is None:
            logger.error("获取 PR #%d 失败", pr_number)
        return result


async def get_pr_diff(repo: str, pr_number: int, config: dict[str, Any]) -> str:
    """获取 PR 的 diff 内容。"""
    token = _token_for_repo(config, repo)
    headers = _github_headers(token, extra_accept="application/vnd.github.v3.diff")
    async with httpx.AsyncClient(headers=headers, timeout=30.0) as cli:
        resp = await cli.get(f"https://api.github.com/repos/{repo}/pulls/{pr_number}")
        if resp.status_code == 200:
            return resp.text
        logger.error("获取 PR #%d diff 失败: %d", pr_number, resp.status_code)
        return ""


async def get_pr_files(repo: str, pr_number: int, config: dict[str, Any]) -> list[dict[str, Any]]:
    async with _GitHubClient(_token_for_repo(config, repo)) as client:
        resp = await client.get(f"/repos/{repo}/pulls/{pr_number}/files", params={"per_page": 100})
        if resp.status_code == 200:
            return resp.json()
        return []


async def get_pr_reviews(repo: str, pr_number: int, config: dict[str, Any]) -> list[dict[str, Any]]:
    async with _GitHubClient(_token_for_repo(config, repo)) as client:
        resp = await client.get(f"/repos/{repo}/pulls/{pr_number}/reviews", params={"per_page": 100})
        if resp.status_code == 200:
            return resp.json()
        return []


# ═══════════════════════════════════════════════════════════════════════
# 仓库操作
# ═══════════════════════════════════════════════════════════════════════


async def get_default_branch(repo: str, config: dict[str, Any]) -> str:
    """获取仓库的默认分支名（main/master/...）。"""
    async with _GitHubClient(_token_for_repo(config, repo)) as client:
        result = await client.get_json(f"/repos/{repo}")
        if isinstance(result, dict):
            return str(result.get("default_branch", "main"))
        logger.warning("获取默认分支失败 %s，fallback main", repo)
        return "main"


async def fork_repo(repo: str, config: dict[str, Any]) -> dict[str, Any] | None:
    async with _GitHubClient(_write_token_for_repo(config, repo)) as client:
        resp = await client.post(f"/repos/{repo}/forks")
        if resp.status_code in (200, 201, 202):
            return resp.json()
        if resp.status_code == 422:
            logger.info("已 Fork 过 %s，跳过", repo)
            return None
        logger.error("Fork 失败 %s: %d %s", repo, resp.status_code, resp.text[:200])
        return None


async def sync_fork(repo: str, config: dict[str, Any]) -> bool:
    username = _resolve_github_username(repo, config)
    default_branch = await get_default_branch(repo, config)
    async with _GitHubClient(_write_token_for_repo(config, repo)) as client:
        resp = await client.post(
            f"/repos/{username}/{repo.split('/')[-1]}/merge-upstream",
            json={"branch": default_branch},
        )
        if resp.status_code == 200:
            return True
        logger.warning("同步 Fork 失败 %s: %d %s", repo, resp.status_code, resp.text[:200])
        return False


# ═══════════════════════════════════════════════════════════════════════
# PR 操作
# ═══════════════════════════════════════════════════════════════════════


async def create_pr(
    repo: str,
    title: str,
    body: str,
    head: str,
    base: str,
    config: dict[str, Any],
) -> dict[str, Any] | None:
    async with _GitHubClient(_write_token_for_repo(config, repo)) as client:
        result = await client.post_json(
            f"/repos/{repo}/pulls",
            json={"title": title, "body": body, "head": head, "base": base},
        )
        if result is None:
            logger.error("创建 PR 失败: %s", repo)
        return result


async def create_review(
    repo: str,
    pr_number: int,
    body: str,
    event: str,
    config: dict[str, Any],
) -> dict[str, Any] | None:
    async with _GitHubClient(_write_token_for_repo(config, repo)) as client:
        result = await client.post_json(
            f"/repos/{repo}/pulls/{pr_number}/reviews",
            json={"body": body, "event": event},
        )
        if result is None:
            logger.error("提交 Review 失败: PR #%d", pr_number)
        return result


async def create_inline_comment(
    repo: str,
    pr_number: int,
    commit_id: str,
    path: str,
    line: int,
    body: str,
    config: dict[str, Any],
) -> dict[str, Any] | None:
    async with _GitHubClient(_write_token_for_repo(config, repo)) as client:
        resp = await client.post(
            f"/repos/{repo}/pulls/{pr_number}/comments",
            json={"body": body, "commit_id": commit_id, "path": path, "line": line, "side": "RIGHT"},
        )
        if resp.status_code == 201:
            return resp.json()
        logger.warning("行内评论失败: %d %s", resp.status_code, resp.text[:200])
        return None


# ═══════════════════════════════════════════════════════════════════════
# 标签操作
# ═══════════════════════════════════════════════════════════════════════


async def get_labels(repo: str, config: dict[str, Any]) -> list[dict[str, Any]]:
    async with _GitHubClient(_token_for_repo(config, repo)) as client:
        resp = await client.get(f"/repos/{repo}/labels", params={"per_page": 100})
        if resp.status_code == 200:
            return resp.json()
        return []


async def create_label(
    repo: str,
    name: str,
    color: str,
    description: str,
    config: dict[str, Any],
) -> bool:
    async with _GitHubClient(_write_token_for_repo(config, repo)) as client:
        resp = await client.post(
            f"/repos/{repo}/labels",
            json={"name": name, "color": color, "description": description},
        )
        return resp.status_code in (200, 201)


async def add_labels_to_issue(
    repo: str,
    issue_number: int,
    labels: list[str],
    config: dict[str, Any],
) -> bool:
    async with _GitHubClient(_write_token_for_repo(config, repo)) as client:
        resp = await client.post(
            f"/repos/{repo}/issues/{issue_number}/labels",
            json={"labels": labels},
        )
        return resp.status_code == 200


async def remove_label_from_issue(
    repo: str,
    issue_number: int,
    label_name: str,
    config: dict[str, Any],
) -> bool:
    """从 Issue 移除单个标签。"""
    from urllib.parse import quote
    async with _GitHubClient(_write_token_for_repo(config, repo)) as client:
        resp = await client.delete(
            f"/repos/{repo}/issues/{issue_number}/labels/{quote(label_name, safe='')}"
        )
        return resp.status_code in (200, 204)


async def set_all_labels_to_issue(
    repo: str,
    issue_number: int,
    labels: list[str],
    config: dict[str, Any],
) -> bool:
    """全量替换 Issue 标签。先删除全部已有标签，再添加新标签。"""
    from urllib.parse import quote

    existing = await get_issue_labels(repo, issue_number, config)
    old_names = [lb.get("name", "") for lb in existing if lb.get("name", "")]
    for name in old_names:
        async with _GitHubClient(_write_token_for_repo(config, repo)) as client:
            resp = await client.delete(f"/repos/{repo}/issues/{issue_number}/labels/{quote(name, safe='')}")
            if resp.status_code not in (200, 204):
                logger.debug("删除标签 %s 失败: %d", name, resp.status_code)
    if labels:
        return await add_labels_to_issue(repo, issue_number, labels, config)
    return True


async def get_issue_labels(
    repo: str,
    issue_number: int,
    config: dict[str, Any],
) -> list[dict[str, Any]]:
    """获取某个 Issue 当前所有标签。"""
    async with _GitHubClient(_token_for_repo(config, repo)) as client:
        resp = await client.get(f"/repos/{repo}/issues/{issue_number}/labels")
        if resp.status_code == 200:
            return resp.json()
        return []


async def post_issue_comment(
    repo: str,
    issue_number: int,
    body: str,
    config: dict[str, Any],
) -> bool:
    async with _GitHubClient(_write_token_for_repo(config, repo)) as client:
        resp = await client.post(
            f"/repos/{repo}/issues/{issue_number}/comments",
            json={"body": body},
        )
        if resp.status_code in (200, 201):
            return True
        logger.error("发表 Issue 评论失败: %d %s", resp.status_code, resp.text[:200])
        return False


# ═══════════════════════════════════════════════════════════════════════
# Issue / PR 状态操作
# ═══════════════════════════════════════════════════════════════════════


async def get_file_content(
    repo: str, path: str, ref: str = "HEAD", config: dict[str, Any] | None = None
) -> str:
    """获取仓库文件原始内容（最多 64KB）。"""
    if config is None:
        config = {}
    async with _GitHubClient(_token_for_repo(config, repo)) as client:
        resp = await client.get(
            f"/repos/{repo}/contents/{path}",
            params={"ref": ref},
            headers={"Accept": "application/vnd.github.v3.raw"},
        )
        if resp.status_code == 200:
            return resp.text[:65536]
        logger.debug("获取文件 %s 失败: %d", path, resp.status_code)
        return ""


async def close_issue(
    repo: str,
    issue_number: int,
    comment_body: str | None = None,
    config: dict[str, Any] | None = None,
    state_reason: str = "not_planned",
) -> bool:
    """关闭 Issue，可选附带一条关闭说明评论。

    先发表评论（若提供），再 PATCH state=closed。
    state_reason: "completed" | "not_planned"
    """
    if config is None:
        config = {}
    async with _GitHubClient(_write_token_for_repo(config, repo)) as client:
        if comment_body:
            await client.post(
                f"/repos/{repo}/issues/{issue_number}/comments",
                json={"body": comment_body},
            )
        resp = await client.patch(
            f"/repos/{repo}/issues/{issue_number}",
            json={"state": "closed", "state_reason": state_reason},
        )
        if resp.status_code == 200:
            logger.info("已关闭 Issue %s #%d", repo, issue_number)
            return True
        logger.error("关闭 Issue %s #%d 失败: %d %s", repo, issue_number, resp.status_code, resp.text[:200])
        return False


async def close_pr(
    repo: str,
    pr_number: int,
    comment_body: str | None = None,
    config: dict[str, Any] | None = None,
) -> bool:
    """关闭 PR，可选附带一条关闭说明评论。"""
    if config is None:
        config = {}
    async with _GitHubClient(_write_token_for_repo(config, repo)) as client:
        if comment_body:
            await client.post(
                f"/repos/{repo}/issues/{pr_number}/comments",
                json={"body": comment_body},
            )
        resp = await client.patch(
            f"/repos/{repo}/pulls/{pr_number}",
            json={"state": "closed"},
        )
        if resp.status_code == 200:
            logger.info("已关闭 PR %s #%d", repo, pr_number)
            return True
        logger.error("关闭 PR %s #%d 失败: %d %s", repo, pr_number, resp.status_code, resp.text[:200])
        return False


# ═══════════════════════════════════════════════════════════════════════
# 仓库上下文（README + 项目结构）
# ═══════════════════════════════════════════════════════════════════════


async def get_readme(repo: str, config: dict[str, Any]) -> str:
    """获取仓库 README 原始内容（最多 8KB）。"""
    async with _GitHubClient(_token_for_repo(config, repo)) as client:
        resp = await client.get(
            f"/repos/{repo}/readme",
            headers={"Accept": "application/vnd.github.v3.raw"},
        )
        if resp.status_code == 200:
            return resp.text[:8192]
        logger.debug("获取 README 失败 %s: %d", repo, resp.status_code)
        return ""


async def get_repo_file_tree(repo: str, config: dict[str, Any]) -> list[dict[str, Any]]:
    """获取仓库顶层目录结构（最多 50 项）。

    排除 .git/ node_modules/ __pycache__ 等 noise 目录。
    """
    async with _GitHubClient(_token_for_repo(config, repo)) as client:
        resp = await client.get(f"/repos/{repo}/contents", params={"per_page": 50})
        if resp.status_code == 200:
            items = resp.json()
            if isinstance(items, list):
                noise = {".git", "node_modules", "__pycache__", ".venv", "venv", ".idea", ".vscode"}
                return [it for it in items if it.get("name", "") not in noise]
        logger.debug("获取仓库文件树失败 %s: %d", repo, resp.status_code)
        return []


# ═══════════════════════════════════════════════════════════════════════
# 列表轮询
# ═══════════════════════════════════════════════════════════════════════


async def list_repo_issues(
    repo: str,
    config: dict[str, Any],
    *,
    since: str | None = None,
    state: str = "open",
    per_page: int = 30,
) -> list[dict[str, Any]]:
    async with _GitHubClient(_token_for_repo(config, repo)) as client:
        params: dict[str, Any] = {"state": state, "sort": "created", "direction": "desc", "per_page": per_page}
        if since:
            params["since"] = since
        resp = await client.get(f"/repos/{repo}/issues", params=params)
        if resp.status_code == 200:
            return [item for item in resp.json() if "pull_request" not in item]
        logger.error("获取 Issue 列表失败 %s: %d %s", repo, resp.status_code, resp.text[:200])
        return []


async def list_repo_pulls(
    repo: str,
    config: dict[str, Any],
    *,
    state: str = "open",
    per_page: int = 30,
) -> list[dict[str, Any]]:
    async with _GitHubClient(_token_for_repo(config, repo)) as client:
        resp = await client.get(
            f"/repos/{repo}/pulls",
            params={"state": state, "sort": "updated", "direction": "desc", "per_page": per_page},
        )
        if resp.status_code == 200:
            return resp.json()
        logger.error("获取 PR 列表失败 %s: %d %s", repo, resp.status_code, resp.text[:200])
        return []
