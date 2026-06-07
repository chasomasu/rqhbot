# RqhBot

<div align="center">

![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)
![Version](https://img.shields.io/badge/Version-3.5.0-orange.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![OneBot](https://img.shields.io/badge/OneBot-11-00b894.svg)
![NapCat](https://img.shields.io/badge/NapCat-supported-6c5ce7.svg)

基于 **NapCat / OneBot 11** 协议的 Python QQ 机器人开发框架。

它提供强类型事件模型、异步 WebSocket 客户端、插件系统、配置管理和常用 Bot API 封装，适合快速搭建个人机器人、群管理机器人和业务自动化机器人。

[文档索引](docs/01_INDEX.md) · [快速开始](docs/03_QUICK_START.md) · [配置指南](docs/04_CONFIG_GUIDE.md) · [API 参考](docs/05_API.md) · [插件开发](docs/06_PLUGIN_DEVELOPMENT.md)

</div>

---

## 特性

- **异步架构**：基于 `asyncio` + `websockets`，适合高并发消息处理。
- **NapCat / OneBot 11 支持**：通过 WebSocket 与 NapCat 通信。
- **强类型事件模型**：群消息、私聊消息、通知、请求等事件均有清晰的数据结构。
- **简洁 Bot API**：封装发送消息、撤回消息、群管理、好友管理等常用能力。
- **插件系统**：支持插件化开发、热加载、配置隔离和事件订阅。
- **事件总线**：插件与核心逻辑解耦，便于扩展。
- **配置管理**：支持 YAML 配置和环境变量。
- **日志系统**：内置日志配置，便于调试和线上排查。

## 预览

```python
from sdk import BotClient

bot = BotClient()

@bot.on_group_message()
async def hello(event):
    if event.message.get_plain_text() == "hello":
        await bot.api.send_group_message(event.group_id, "你好！")

bot.start()
```

## 环境要求

- Python 3.8+
- 已安装并配置 NapCat
- NapCat WebSocket 服务已启动

NapCat 相关链接：

- [NapCat 安装指南](https://napneko.github.io/guide/napcat)
- [NapCat 文档站](https://napneko.github.io/)

## 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/rqhbot/rqhbot.git
cd rqhbot
```

如果你是直接下载源码压缩包，进入项目目录即可。

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

开发环境可额外安装：

```bash
pip install -r requirements-dev.txt
```

### 3. 创建配置文件

项目提供了配置示例文件：

```bash
cp config.yaml.example config.yaml
```

Windows PowerShell 可使用：

```powershell
Copy-Item config.yaml.example config.yaml
```

然后编辑 `config.yaml`：

```yaml
napcat:
  ws_url: "ws://localhost:3001"
  access_token: ""

bot:
  plugin_dir: "plugins"
  load_plugins: true

settings:
  debug: false
```

### 4. 启动机器人

```bash
python run.py
```

启动前请确保 NapCat 已登录 QQ，并且 WebSocket 地址与 `config.yaml` 中的 `napcat.ws_url` 一致。

## 项目结构

```text
rqhbot/
├── sdk/                    # SDK 核心代码
│   ├── config/             # 配置管理
│   ├── core/               # WebSocket 客户端、事件模型、API 封装
│   └── pluginsystem/       # 插件系统
├── plugins/                # 插件目录
├── docs/                   # 项目文档
├── tests/                  # 单元测试
├── config.yaml.example     # 配置示例
├── requirements.txt        # 运行依赖
├── requirements-dev.txt    # 开发依赖
├── pyproject.toml          # 项目元数据与工具配置
└── run.py                  # 启动入口
```

## 核心模块

| 模块 | 说明 |
| --- | --- |
| `sdk.BotClient` | 面向用户的机器人入口，支持装饰器注册事件 |
| `sdk.core.NapCatClient` | 底层 WebSocket 客户端 |
| `sdk.core.BotAPI` | OneBot / NapCat API 封装 |
| `sdk.core.EventBus` | 事件总线，用于插件和核心解耦 |
| `sdk.pluginsystem.PluginBase` | 插件基类 |
| `sdk.pluginsystem.HotReloadPluginManager` | 插件热加载管理器 |

## 插件示例

在 `plugins/example/main.py` 中创建插件：

```python
from sdk import PluginBase, group_server


class ExamplePlugin(PluginBase):
    name = "example"
    version = "1.0.0"
    description = "示例插件"

    @group_server(equals="ping")
    async def on_ping(self, event):
        if self.api is None:
            return
        await self.api.send_group_message(event.group_id, "pong")
```

更多写法请查看：[插件开发文档](docs/06_PLUGIN_DEVELOPMENT.md)。

## 文档导航

- [文档索引](docs/01_INDEX.md)
- [项目概述](docs/02_OVERVIEW.md)
- [快速开始](docs/03_QUICK_START.md)
- [配置指南](docs/04_CONFIG_GUIDE.md)
- [API 参考](docs/05_API.md)
- [插件开发](docs/06_PLUGIN_DEVELOPMENT.md)

## 测试

```bash
python -m pytest tests/ -v
```

如果需要开发依赖：

```bash
pip install -r requirements-dev.txt
```

## 适用场景

- QQ 群自动回复机器人
- 群管理与数据统计机器人
- AI 聊天机器人接入
- 消息推送与业务通知
- 自定义自动化工作流

## 技术栈

- Python 3.8+
- asyncio
- websockets
- PyYAML
- python-dotenv
- aiohttp / requests
- NapCat / OneBot 11

## 贡献

欢迎提交 Issue 和 Pull Request。

建议流程：

1. Fork 本仓库
2. 创建功能分支
3. 提交修改并补充必要测试
4. 发起 Pull Request

## 许可证

本项目采用 MIT License。

---

<div align="center">

**RqhBot v3.5.0**

Made by RqhBot Team

</div>
