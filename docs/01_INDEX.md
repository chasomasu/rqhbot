# RqhBot - QQ 机器人 SDK

基于 NapCat OneBot11 协议的 Python SDK，用于开发 QQ 机器人。

## ⚡ 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置 config.yaml
cp config.yaml.example config.yaml
# 编辑 config.yaml 设置 NapCat 连接信息

# 3. 启动机器人
python run.py              # 或使用 start.bat / ./start.sh
```

## ✨ 特性

- 🚀 **简洁 API** - 易于上手
- 🔌 **插件系统** - 热插拔架构
- ⚙️ **灵活配置** - YAML + 环境变量
- 📝 **完善日志** - 按日期分隔
- 🔄 **异步支持** - 高性能
- 🎯 **强类型事件** - 类型安全，减少错误
- 🧩 **事件总线** - 模块解耦，扩展灵活

---

## 📚 文档导航

### 🚀 入门指南
- [项目概述](./02_OVERVIEW.md) - 了解 RqhBot
- [快速开始](./03_QUICK_START.md) - 5分钟上手
- [配置指南](./04_CONFIG_GUIDE.md) - 配置系统

### 💻 开发文档
- [API 参考](./05_API.md) - 完整 API
- [插件开发](./06_PLUGIN_DEVELOPMENT.md) - 开发指南（含速查表）

### 📖 文档结构

```
docs/
├── 01_INDEX.md                 # 本文档（总入口）
├── 02_OVERVIEW.md              # 项目概述
├── 03_QUICK_START.md           # 快速开始
├── 04_CONFIG_GUIDE.md          # 配置指南
├── 05_API.md                   # API 参考
└── 06_PLUGIN_DEVELOPMENT.md    # 插件开发（含速查）
```

## 🎯 推荐阅读路径

**新手**：OVERVIEW → QUICK_START → CONFIG_GUIDE  
**开发者**：API → PLUGIN_DEVELOPMENT  
**进阶**：阅读源码和示例插件

## 🆘 帮助

- 查看完整文档（当前页面）
- 提交 Issue 或 Pull Request
- 查阅 [SDK README](../sdk/README.md) 了解 SDK 结构

---

**版本**: 3.5.0 | **最后更新**: 2026-05-16
