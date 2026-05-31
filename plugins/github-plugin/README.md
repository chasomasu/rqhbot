# GitHub Plugin — rqhbot QQ 机器人

> GitHub Issue/PR 自动化管理插件，适用于 [rqhbot](https://github.com/rqhbot) QQ 机器人框架

[![Version](https://img.shields.io/badge/version-3.5.0-blue.svg)](plugins/github-plugin)
[![Python](https://img.shields.io/badge/python-3.8+-green.svg)](https://www.python.org/)

## 简介

本插件为 rqhbot 机器人提供 **AI 驱动的 GitHub Issue/PR 全生命周期管理**，支持：

- 自动检测新 Issue/PR（轮询或 Webhook）
- LLM 自动标签分类 + 垃圾检测 + 智能回复
- AI 自动代码修复（Fork → 修改 → 测试 → 创建 PR）
- PR 自动代码审阅（结构化报告 + 行内评论）
- 通过 QQ 群聊/私聊 `/gh` 指令管理任务

## 功能特性

### Issue 自动化管理

- **自动检测** — 通过轮询 GitHub API 定时检测新 Issue/PR，无需公网 IP 或 Webhook
- **智能标签分类** — LLM 自动判断类型（bug/feature/docs/question/refactor）、优先级、难度和模块区域
- **垃圾检测与自动关闭** — 识别广告、占位符、无意义提交等垃圾 Issue，生成关闭评论后自动关闭
- **后台信息收集** — 自动拉取仓库 README 和目录结构，必要时追问补充信息（最多 12 轮）
- **对话状态机** — `GATHERING_INFO → AWAITING_RESPONSE → READY → FIXING → DONE`
- **智能回复** — 新 Issue 自动生成友好回复，告知提交者后续处理流程

### AI 代码修复

- **完整 Agent 循环** — 管理员在 QQ 中确认后自动执行：
  1. Fork 仓库 → 同步上游 → Clone 到本地 → 创建修复分支
  2. LLM 分析代码（4 个内置工具辅助定位）
  3. 修改代码 → 运行测试
  4. 提交代码 + 创建 PR
- **内置工具系统**：
  - `search_content` — 原生 Python 搜索关键词
  - `read_file_chunk` — 按行读取文件片段
  - `search_and_replace_block` — 精确代码块替换（校验唯一性）
  - `run_local_test` — 在沙盒中运行测试命令
- **控制台实时可视化** — 实时展示 Agent 工作过程

### PR 自动审阅

- **自动代码审阅** — 获取 diff，LLM 按维度（正确性/安全性/风格/测试/性能）分析
- **结构化审阅报告** — 严重程度（critical/warning/suggestion）、文件、行号、建议
- **双模式审阅** — `quick`（快速）和 `deep`（深度）
- **自动去重** — 避免重复审阅

### QQ 聊天命令

| 命令 | 说明 |
|------|------|
| `/gh <task_id> auto` | 启动 Issue 自动修复 |
| `/gh <task_id> status` | 查询任务状态 |
| `/gh <task_id> abort` | 中止任务 |
| `/gh review <pr_number> [quick\|deep]` | 手动触发 PR 审阅（单仓库） |
| `/gh review <索引> <pr_number> [quick\|deep]` | 多仓库时指定索引 |

## 架构

```
NapCat (QQ)
    ↓ WebSocket
rqhbot SDK (BotClient / EventBus / PluginBase)
    ↓
GithubPlugin (main.py)
    │
    ├── core/poller.py  ── 定时轮询 GitHub API（默认 60s）
    ├── core/webhook.py ── Webhook HTTP 服务器（可选）
    │
    ├── core/labeler.py  ── LLM 自动标签分类
    ├── core/closer.py   ── 垃圾 Issue/PR 检测与关闭
    ├── core/commenter.py ── 智能回复生成
    ├── core/gatherer.py  ── 信息收集与分析
    │
    ├── tracker.py       ── Issue 状态机（后台信息收集循环）
    ├── core/agent_loop.py ── Agent 核心循环（Fork→修改→测试→PR）
    ├── core/review.py   ── PR 自动代码审阅
    ├── core/commands.py ── /gh 指令处理
    │
    ├── core/api.py      ── GitHub REST API 封装（httpx）
    ├── core/llm.py      ── OpenAI 兼容 LLM 客户端
    ├── core/store.py    ── JSON 文件键值持久化存储
    ├── core/skills.py   ── Agent 工具注册表
    │
    └── console_viewer.py ── 控制台实时可视化
```

## 安装

### 前置要求

- Python 3.8+
- rqhbot 机器人框架已配置运行
- GitHub Personal Access Token (PAT)
- Git（AI 代码修复功能需要）

### 安装步骤

```bash
# 1. 插件已位于 plugins/github-plugin/ 目录下

# 2. 安装额外依赖
pip install httpx openai

# 3. 配置 config.json（见下方说明）

# 4. 重启 rqhbot 机器人
```

## 配置

### config.json 配置项

```json
{
    "github_write_token": "ghp_xxx",
    "github_username": "your-username",
    "github_email": "your-email@example.com",
    "active_repos": ["owner/repo1", "owner/repo2"],
    "admin_user_id": "123456789",

    "llm": {
        "base_url": "https://api.openai.com/v1",
        "api_key": "sk-xxx",
        "model": "gpt-4o"
    },

    "max_retries": 3,
    "max_questions": 12,
    "test_command": "pytest",
    "workspace_dir": "data/github_workspace",

    "auto_label": true,
    "auto_review": true,
    "auto_close_garbage": true,
    "review_mode": "quick",

    "poll_interval_seconds": 60,
    "webhook_secret": "",
    "webhook_host": "0.0.0.0",
    "webhook_port": 8080
}
```

### 配置项说明

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `github_write_token` | string | `""` | GitHub PAT（用于 Fork/PR/标签/评论等写操作） |
| `github_username` | string | `""` | GitHub 用户名（git 提交者身份） |
| `github_email` | string | `""` | GitHub 邮箱（git 提交者 email） |
| `active_repos` | array | `[]` | 需要监控的仓库列表（`owner/repo` 格式） |
| `admin_user_id` | string | `""` | 管理员 QQ 号（有权限执行 /gh 命令） |
| `llm.base_url` | string | `https://api.openai.com/v1` | LLM API 地址 |
| `llm.api_key` | string | `""` | LLM API Key |
| `llm.model` | string | `gpt-4o` | LLM 模型名 |
| `max_retries` | int | `3` | 代码修复最大重试轮数 |
| `max_questions` | int | `12` | 信息收集最大追问次数 |
| `test_command` | string | `"pytest"` | 代码修改后运行的测试命令 |
| `workspace_dir` | string | `"data/github_workspace"` | 代码修复工作区目录 |
| `auto_label` | bool | `true` | 启用 Issue 自动标签分类 |
| `auto_review` | bool | `true` | 启用 PR 自动审阅 |
| `auto_close_garbage` | bool | `true` | 启用垃圾检测自动关闭 |
| `review_mode` | string | `"quick"` | PR 审阅模式：`quick`（快速）或 `deep`（深度） |
| `poll_interval_seconds` | int | `60` | 轮询间隔（秒），0=禁用轮询 |
| `webhook_secret` | string | `""` | Webhook 签名密钥（留空不校验签名） |
| `webhook_host` | string | `"0.0.0.0"` | Webhook HTTP 监听地址 |
| `webhook_port` | int | `8080` | Webhook HTTP 监听端口 |

## 工作流程

### Issue 生命周期

```
新 Issue 提交（轮询或 Webhook）
    │
    ▼
┌─────────────┐
│  垃圾检测   │───是──▶ 生成关闭评论 → 关闭 Issue
└─────┬───────┘
      │ 否
      ▼
┌─────────────┐
│  自动标签   │──▶ 根据内容自动分类打标签
└─────┬───────┘
      │
      ▼
┌─────────────┐
│  智能回复   │──▶ 自动回复用户
└─────┬───────┘
      │
      ▼
┌─────────────────┐
│  后台信息收集    │◀──────────────────┐
│  (IssueTracker)  │                   │
└─────┬───────────┘                   │
      │                               │
      ├── 信息不足 ──▶ 追问提问者 ──▶ 等待回复
      │                               │
      ├── 需要查看代码 ──▶ 获取文件 ──┘
      │
      ├── 应关闭 ──▶ 生成关闭评论 → 关闭 Issue
      │
      └── 信息就绪 ──▶ QQ 通知管理员
                        │
                        ▼
                  管理员发送 /gh <task_id> auto
                        │
                        ▼
                  ┌─────────────┐
                  │  Agent Loop │
                  │ Fork→修改   │
                  │ 测试→PR    │
                  └─────┬───────┘
                        │
                        ▼
                  ┌─────────────┐
                  │  创建 PR    │──▶ 完成
                  └─────────────┘
```

### Agent Loop 详解

```
1. 工作区准备
   ├── Fork 仓库（幂等）
   ├── Sync upstream
   ├── Clone 到本地
   └── 创建 fix-issue-{number} 分支

2. 代码分析与修改
   ├── LLM 接收 Issue 信息 + 工具定义
   ├── 循环调用工具（最多 50 轮）：
   │   ├── search_content       — 定位相关代码
   │   ├── read_file_chunk      — 查看上下文
   │   ├── search_and_replace   — 修改代码
   │   └── run_local_test       — 运行测试
   └── 调用 done 结束循环

3. 验证阶段
   ├── 运行 test_command（如 pytest）
   └── 失败 → LLM 分析错误并修复 → 重新验证

4. 提交与 PR
   ├── git add + commit
   ├── git push
   └── 创建 PR（自动检测默认分支）
```

## 文件结构

```
github-plugin/
├── main.py              # 插件入口（PluginBase 子类）
├── cli.py               # 独立 CLI 入口（cli/poll/serve 三种模式）
├── config.json          # 插件配置文件
├── plugin.json          # 插件元数据
├── __init__.py          # 包说明
├── README.md            # 本文件
│
├── tracker.py           # Issue 状态机 & 后台信息收集
├── monitor_config.py    # 从 github_monitor 读取配置
├── console_viewer.py    # 控制台实时可视化
├── stream_writer.py     # 结构化事件日志流
│
└── core/
    ├── __init__.py      # 统一导出
    ├── api.py           # GitHub REST API 封装（httpx）
    ├── agent_loop.py    # Agent 核心循环
    ├── closer.py        # 垃圾 Issue/PR 检测与关闭
    ├── commands.py      # /gh 指令处理
    ├── commenter.py     # Issue 智能回复生成
    ├── config.py        # 配置模型 GithubAgentConfig
    ├── gatherer.py      # LLM 驱动的信息收集与分析
    ├── labeler.py       # Issue 自动标签分类
    ├── llm.py           # OpenAI 兼容 LLM 客户端
    ├── poller.py        # GitHub API 轮询模块
    ├── review.py        # PR 自动代码审阅
    ├── skills.py        # Agent 工具注册表
    ├── store.py         # JSON 文件键值存储
    └── webhook.py       # Webhook 事件处理器
```

## 独立运行模式

插件支持脱离 rqhbot 独立运行（通过 `cli.py`）：

```bash
# 单次执行命令
python cli.py cli status <task_id>
python cli.py cli review <pr_number> quick

# 轮询守护模式
python cli.py poll --config config.json

# Webhook 服务器模式
python cli.py serve --config config.json --port 8080
```

## 依赖

| 依赖 | 用途 |
|------|------|
| `httpx>=0.27` | 异步 HTTP 客户端（GitHub API 调用） |
| `openai>=1.55` | OpenAI 兼容 API 的 LLM 客户端 |
| `git`（系统命令） | 仓库克隆/提交/推送（AI 修复功能需要） |

---

> **注意**：插件支持 **轮询模式**（默认启用）和 **Webhook 模式**，轮询模式无需公网 IP，适合无法接收外部 HTTP 请求的环境。Webhook 模式需确保 rqhbot 所在服务器有公网 IP 或使用 frp/ngrok 内网穿透。
