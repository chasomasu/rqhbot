# 配置管理器使用指南

## 📋 概述

RqhBot 使用 YAML 配置文件 `config.yaml` 管理所有配置，并提供便捷的配置管理器 API。

配置文件位置：项目根目录的 `config.yaml`

## 🚀 快速开始

### 导入配置管理器

```python
from sdk.config import config_manager
```

### 基本用法

```python
# 获取配置值
ws_url = config_manager.get('napcat.ws_url', 'ws://localhost:3001')

# 设置配置值（自动保存到 config.yaml）
config_manager.set_ws_uri('ws://localhost:3002')
```

## 📝 NapCat 配置方法

### 设置机器人信息

```python
from sdk.config import config_manager

# 设置机器人 QQ 号
config_manager.set_bot_uin("3831279795")

# 设置根账号
config_manager.set_root("2654278608")
```

### 设置 WebSocket 连接

```python
# 设置 WebSocket URI
config_manager.set_ws_uri("ws://localhost:3002")

# 设置 WebSocket Token
config_manager.set_ws_token("Chasomasu")
```

### 设置 WebUI

```python
# 设置 WebUI URI
config_manager.set_webui_uri("http://localhost:6098")

# 设置 WebUI Token
config_manager.set_webui_token("qVkC0,Mqh+=X;4{}")
```

## 🔧 Bot 配置方法

### 插件系统配置

```python
# 设置是否加载插件
config_manager.set_load_plugins(True)   # 启用插件
config_manager.set_load_plugins(False)  # 禁用插件

# 设置插件目录
config_manager.set_plugin_dir("plugins")
```

## 📊 日志配置方法

```python
# 设置日志级别（DEBUG, INFO, WARNING, ERROR, CRITICAL）
config_manager.set_log_level("DEBUG")

# 设置日志目录
config_manager.set_log_dir("log")
```

## ⚙️ 其他配置方法

```python
# 设置调试模式
config_manager.set_debug(True)

# 重新加载配置（从文件重新读取）
config_manager.reload()

# 显示当前配置
config_manager.show()
```

## 📁 配置文件结构

`config.yaml` 完整结构：

```yaml
# NapCat 连接配置
napcat:
  ws_url: "ws://localhost:3001"        # WebSocket 地址
  access_token: ""                      # WebSocket Token
  bot_uin: ""                           # 机器人 QQ 号
  root: ""                              # 根账号
  webui_uri: "http://localhost:6098"   # WebUI 地址
  webui_token: ""                       # WebUI Token

# 机器人配置
bot:
  load_plugins: true                    # 是否加载插件
  plugin_dir: "plugins"                 # 插件目录

# 日志配置
logging:
  level: "INFO"                         # 日志级别
  log_dir: "log"                        # 日志目录
  log_file: "bot.log"                   # 日志文件名

# 其他配置
settings:
  debug: false                          # 调试模式
  auto_reconnect: true                  # 自动重连
  reconnect_interval: 5                 # 重连间隔（秒）
```

## 💡 使用示例

### 示例 1：初始化配置

```python
from sdk.config import config_manager

# 首次运行时设置基本配置
config_manager.set_ws_uri("ws://localhost:3001")
config_manager.set_ws_token("your_token_here")
config_manager.set_bot_uin("123456789")
config_manager.set_load_plugins(True)

print("配置已保存！")
```

### 示例 2：在 main.py 中使用

```python
from sdk.config import config_manager

def main():
    # 从配置读取 WebSocket 地址
    ws_url = config_manager.get('napcat.ws_url', 'ws://localhost:3001')
    
    # 从配置读取是否加载插件
    load_plugins = config_manager.get('bot.load_plugins', True)
    
    # 从配置读取插件目录
    plugin_dir = config_manager.get('bot.plugin_dir', 'plugins')
    
    print(f"WebSocket: {ws_url}")
    print(f"插件系统: {'启用' if load_plugins else '禁用'}")
    
    # 启动机器人
    bot.client.ws_url = ws_url
    bot.start(load_plugins=load_plugins)
```

### 示例 3：动态切换配置

```python
from sdk.config import config_manager

# 根据环境切换配置
environment = "production"  # 或 "development"

if environment == "production":
    config_manager.set_ws_uri("ws://prod.example.com:3001")
    config_manager.set_debug(False)
    config_manager.set_log_level("WARNING")
else:
    config_manager.set_ws_uri("ws://localhost:3001")
    config_manager.set_debug(True)
    config_manager.set_log_level("DEBUG")

print("配置已更新！")
```

### 示例 4：查看当前配置

```python
from sdk.config import config_manager

# 显示完整配置
config_manager.show()

# 获取特定配置项
ws_url = config_manager.get('napcat.ws_url')
print(f"WebSocket URL: {ws_url}")

# 获取带默认值的配置
timeout = config_manager.get('settings.timeout', 30)
print(f"Timeout: {timeout}")
```

## 🔍 通用方法

### get() - 获取配置值

```python
# 基本用法
value = config_manager.get('key')

# 带默认值
value = config_manager.get('key', 'default_value')

# 嵌套键（使用点号分隔）
ws_url = config_manager.get('napcat.ws_url')
token = config_manager.get('napcat.access_token')
```

### set() - 设置配置值

```python
# 设置简单值
config_manager.set('settings.debug', True)

# 设置嵌套值
config_manager.set('napcat.ws_url', 'ws://localhost:3002')

# 注意：set() 不会自动保存，需要调用 save()
config_manager.save()
```

### save() - 保存配置

```python
# 手动保存配置到文件
config_manager.save()
```

### reload() - 重新加载配置

```python
# 从文件重新加载配置（丢弃未保存的修改）
config_manager.reload()
```

## ⚠️ 注意事项

1. **自动保存**：所有 `set_*()` 方法都会自动保存配置到 `config.yaml`
2. **配置优先级**：命令行参数 > YAML 配置 > 环境变量 > 默认值
3. **路径问题**：配置文件路径相对于项目根目录
4. **格式要求**：YAML 文件需要正确的缩进和格式

## 🎯 最佳实践

### 1. 首次运行初始化

```python
from sdk.config import config_manager
import os

config_path = "config.yaml"
if not os.path.exists(config_path):
    # 首次运行，设置默认配置
    config_manager.set_ws_uri("ws://localhost:3001")
    config_manager.set_load_plugins(True)
    config_manager.set_debug(False)
    print("已创建默认配置文件")
```

### 2. 配置验证

```python
from sdk.config import config_manager

# 验证必要配置
ws_url = config_manager.get('napcat.ws_url')
if not ws_url:
    print("错误：未配置 WebSocket 地址")
    config_manager.set_ws_uri("ws://localhost:3001")
```

### 3. 备份配置

```python
import shutil
from pathlib import Path

# 备份配置文件
config_path = Path("config.yaml")
backup_path = Path("config.yaml.backup")

if config_path.exists():
    shutil.copy(config_path, backup_path)
    print("配置已备份")
```

## 📚 相关文档

- [README.md](../README.md) - 项目主文档
- [API.md](./05_API.md) - API 参考文档
- [config.yaml](../config.yaml) - 配置文件示例

---

**最后更新**: 2026-05-16  
**版本**: 3.5.0
