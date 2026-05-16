# 项目概述

## 🤖 什么是 RqhBot？

RqhBot 是一个基于 NapCat OneBot11 协议的 Python QQ 机器人 SDK，提供了简洁易用的 API、强大的插件系统和事件驱动的架构。它采用模块化设计，支持热插拔插件，让开发者能够快速构建功能丰富的 QQ 机器人。

## ✨ 核心特性

### 1. 事件总线架构

- **EventBus**：所有模块通过事件总线通信，彻底解耦
- 插件只依赖 `IBotAPI` 接口，不持有 `BotClient` 引用
- 支持任意模块订阅/发布事件，扩展灵活

### 2. 强类型事件

- 所有事件（`GroupMessageEvent`、`NoticeEvent` 等）均为强类型 dataclass
- `NoticeEvent` 细分为 `GroupIncreaseNotice`、`GroupBanNotice` 等子类
- `RequestEvent` 细分为 `FriendRequestEvent`、`GroupRequestEvent`
- 自动按类型分发，无需手动解析原始 dict

### 3. 简洁的 API 设计

- 直观的接口设计，易于上手
- 完整的类型提示支持
- 异步编程模型，高性能
- `BotAPI.call()` 支持调用任意 OneBot API

### 4. 强大的插件系统

- 热插拔插件架构
- 标准化的插件接口（只依赖 `IBotAPI` + `EventBus`）
- 插件卸载时自动取消订阅
- 配置文件和数据持久化内置支持

### 5. 灵活的配置管理

- YAML 配置文件支持
- 环境变量兼容
- 动态配置更新

### 6. 完善的日志系统

- 按日期分隔的日志文件
- 可配置的日志级别
- 详细的错误追踪

## 📁 项目结构

```
rqhbot/
├── sdk/                    # SDK 核心代码
│   ├── config/            # 配置管理模块
│   ├── core/              # 核心功能模块
│   └── pluginsystem/      # 插件系统模块
├── plugins/               # 插件目录
│   ├── abc/              # ABC 综合插件
│   ├── def/              # DEF 游戏插件
│   ├── ghi/              # GHI 统计插件
│   └── yiyichat/         # YIYICHAT AI聊天插件
├── docs/                  # 文档目录
├── log/                   # 日志目录
├── config.yaml            # 配置文件
├── requirements.txt       # Python 依赖
└── run.py                 # 主入口文件
```

## 🎯 适用场景

### 1. 个人机器人

- 群聊助手
- 私人助理
- 娱乐机器人

### 2. 社群管理

- 自动回复
- 数据统计
- 内容审核

### 3. 业务集成

- 消息推送
- 客户服务
- 自动化流程

## 🔧 技术栈

- **Python 3.8+**: 主要编程语言
- **websockets**: WebSocket 通信
- **aiohttp**: HTTP 客户端
- **PyYAML**: YAML 配置解析
- **python-dotenv**: 环境变量管理

## 📊 架构设计

```
┌─────────────────┐
│   NapCat        │ ← WebSocket
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  NapCatClient   │ ← 底层连接 + API 调用
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    EventBus     │ ← 发布强类型事件，所有模块解耦
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌────────┐  ┌────────────┐
│BotClient│  │PluginManager│
│装饰器API│  │（不持有BotClient）│
└────────┘  └─────┬──────┘
                  │ IBotAPI
                  ▼
             ┌─────────┐
             │ Plugins │
             └─────────┘
```

**关键设计原则：**
- `NapCatClient` 只负责连接和 API 调用
- `EventBus` 是所有模块通信的唯一中介
- 插件只依赖 `IBotAPI` 接口，不直接引用任何其他模块

## 🚀 快速开始

详见 [快速开始指南](./03_QUICK_START.md)

## 📚 相关文档

- [配置指南](./04_CONFIG_GUIDE.md)
- [API 参考](./05_API.md)
- [插件开发](./06_PLUGIN_DEVELOPMENT.md)
- [SDK 结构说明](../sdk/README.md)

---

**版本**: 3.0.0
**最后更新**: 2026-05-16
