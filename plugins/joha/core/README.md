# Core 模块结构说明

## 目录结构

```
joha/core/
├── __init__.py              # 主入口，导出所有核心组件
├── handlers/                # 处理器模块
│   ├── __init__.py
│   ├── message.py          # 消息处理器 - 接收和预处理群消息
│   ├── commands.py         # 命令处理器 - 处理所有 Bot 命令
│   └── service.py          # 业务服务层 - 学习和回复的核心逻辑
├── builders/               # 构建器模块
│   ├── __init__.py
│   ├── message_builder.py  # 消息构建器 - 构建 LLM 上下文
│   └── message_queue.py    # 消息队列 - 智能合并短时间内的多条消息
└── utils/                  # 工具模块
    ├── __init__.py
    ├── runtime_context.py  # 运行时上下文 - 管理启动期注入的运行参数
    ├── persona_monitor.py  # 人设监控器 - 监控回复是否符合人设
    ├── response_postprocessor.py  # 回复后处理器 - 过滤和清洗 AI 回复
    └── clean_history.py    # 历史记录清洗工具 - 备份和清洗历史记录
```

## 模块职责

### handlers/ - 处理器模块
负责消息的接收、处理和业务逻辑执行。

- **message.py**: 消息入口，处理来自 QQ 平台的原始消息
- **commands.py**: 命令解析和执行，包括管理员命令和用户命令
- **service.py**: 核心业务逻辑，包括学习、决策、回复生成等完整流程

### builders/ - 构建器模块
负责构建各种数据结构和上下文。

- **message_builder.py**: 构建发送给 LLM 的消息上下文（包含历史、人设等）
- **message_queue.py**: 消息队列管理，实现消息合并和批量处理

### utils/ - 工具模块
提供各种辅助功能和工具类。

- **runtime_context.py**: 运行时上下文，存储全局运行状态
- **persona_monitor.py**: 人设稳定性监控，检测回复是否偏离人设
- **response_postprocessor.py**: 回复后处理，过滤思考内容、异常人格等
- **clean_history.py**: 历史记录清洗工具，用于批量处理历史数据

## 导入方式

### 从主入口导入（推荐）
```python
from joha.core import (
    message_service,
    message_handler,
    command_handler,
    runtime_context,
    message_builder,
    message_queue_manager,
    persona_monitor,
    post_processor,
)
```

### 从子模块导入
```python
# 处理器
from joha.core.handlers import message_service, command_handler

# 构建器
from joha.core.builders import message_builder, message_queue_manager

# 工具
from joha.core.utils import runtime_context, persona_monitor, post_processor
```

### 直接从具体文件导入
```python
from joha.core.handlers.service import message_service
from joha.core.builders.message_queue import message_queue_manager
from joha.core.utils.persona_monitor import persona_monitor
```

## 重构说明

本次重构将原本扁平的 core 目录（10个文件）按功能分拆为3个子模块：

**优势：**
- ✅ 清晰的职责划分，便于理解和维护
- ✅ 降低模块间耦合度
- ✅ 便于单元测试和代码复用
- ✅ 符合单一职责原则

**注意事项：**
- 保持了向后兼容，原有导入路径仍然有效（通过 `__init__.py` 导出）
- 内部引用使用完整路径以避免循环依赖
- 建议新代码使用推荐的导入方式
