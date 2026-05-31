"""rqhbot-github-plugin 核心业务模块

统一导出 core 包下的核心类和函数，
入口文件通过 from core.xxx import yyy 导入。
"""

from .commands import handle_gh_command
from .config import GithubAgentConfig
from .llm import LLMClient
from .store import JsonFileStore
from .poller import start_polling_loop
from .webhook import handle_issue_opened, handle_pr_event
from .api import (
    get_pr,
    get_issue,
    list_repo_issues,
    list_repo_pulls,
    close_pr,
    post_issue_comment as create_comment,
)

__all__ = [
    'handle_gh_command',
    'GithubAgentConfig',
    'LLMClient',
    'JsonFileStore',
    'start_polling_loop',
    'handle_issue_opened',
    'handle_pr_event',
    'get_pr',
    'get_issue',
    'list_repo_issues',
    'list_repo_pulls',
    'create_comment',
    'close_pr',
]
