# 快速开始指南

## 🎯 5分钟上手 RqhBot

本指南将帮助你在 5 分钟内启动第一个 QQ 机器人。

## 📋 前置要求

- Python 3.8 或更高版本
- NapCat 已安装并运行
- 基本的 Python 知识

## 🚀 安装步骤

### 1. 克隆项目

```bash
git clone https://github.com/your-repo/rqhbot.git
cd rqhbot
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置 NapCat 连接

编辑 `config.yaml` 文件：

```yaml
napcat:
  ws_url: "ws://localhost:3001"  # NapCat WebSocket 地址
  access_token: ""                # 访问令牌（如果有）
```

### 4. 启动机器人

**Windows:**

```bash
start.bat
```

**Linux/Mac:**

```bash
chmod +x start.sh
./start.sh
```

或者直接运行：

```bash
python run.py
```

## ✅ 验证安装

启动后，你应该看到类似输出：

```
==================================================
  RqhBot - QQ机器人
==================================================
WebSocket: ws://localhost:3001
插件系统: 启用
插件目录: plugins
调试模式: 关闭
==================================================

正在连接...
连接成功！
```

## 💬 测试机器人

在 QQ 群中发送：

- `测试` - 应该回复 "收到测试消息！"
- `hello` - 应该回复 "你好！"
- `help` - 显示可用命令列表

## 🔧 基础配置

### 启用/禁用插件

编辑 `config.yaml`：

```yaml
bot:
  load_plugins: true  # true=启用, false=禁用
```

### 修改日志级别

```yaml
logging:
  level: "DEBUG"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
```

### 开启调试模式

```yaml
settings:
  debug: true
```

## 📝 第一个自定义机器人

创建 `my_bot.py`：

```python
from sdk import BotClient, GroupMessageEvent
from sdk.config import config_manager

bot = BotClient()

@bot.on_group_message()
async def handle_message(msg: GroupMessageEvent):
    text = msg.message.plain_text

    if text == "ping":
        await bot.api.send_group_message(
            group_id=msg.group_id,
            message="pong!"
        )

if __name__ == "__main__":
    bot.client.ws_url = config_manager.get("napcat.ws_url")
    bot.start(load_plugins=False)
```

运行：

```bash
python my_bot.py
```

> **注意**：`msg` 是强类型 `GroupMessageEvent`，直接用 `msg.group_id`、`msg.message.plain_text` 等属性访问，不再需要 `message.get()`。

## 🎓 下一步

- 📖 阅读 [配置指南](./04_CONFIG_GUIDE.md) 了解详细配置
- 🔌 查看 [插件开发指南](./06_PLUGIN_DEVELOPMENT.md) 学习开发插件
- 📚 参考 [API 文档](./05_API.md) 了解完整 API

## ❓ 常见问题

### Q: 连接失败怎么办？

A: 检查 NapCat 是否运行，WebSocket 地址是否正确

### Q: 插件不加载？

A: 检查 `config.yaml` 中 `load_plugins` 是否为 `true`

### Q: 如何查看日志？

A: 日志文件在 `log/` 目录下，按日期命名

## 🆘 获取帮助

- 查看 [故障排除](./TROUBLESHOOTING.md)
- 提交 [Issue](https://github.com/your-repo/issues)
- 阅读 [完整文档](./01_INDEX.md)

---

**祝你使用愉快！** 🎉
