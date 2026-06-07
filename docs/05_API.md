# NapCat Python SDK API 参考

## 目录

- [BotAPI](#botapi) - 机器人 API
  - [消息发送](#消息发送)
    - [send_group_message](#send_group_messagegroup_id-message-image_path)
    - [send_private_message](#send_private_messageuser_id-message-image_path)
    - [send_group_message_segments](#send_group_message_segmentsgroup_id-segments-reply_message_id)
    - [send_private_message_segments](#send_private_message_segmentsuser_id-segments-reply_message_id)
  - [消息管理](#消息管理api)
    - [delete_message](#delete_messagemessage_id)
    - [get_message](#get_messagemessage_id)
  - [互动功能](#互动功能api)
    - [group_poke](#group_pokegroup_id-user_id)
    - [friend_poke](#friend_pokeuser_id)
  - [娱乐功能](#娱乐功能api)
    - [send_group_dice](#send_group_dicegroup_id)
    - [send_group_rps](#send_group_rpsgroup_id)
    - [send_private_dice](#send_private_diceuser_id)
    - [send_private_rps](#send_private_rpsuser_id)
  - [消息历史](#消息历史api)
    - [get_group_message_history](#get_group_message_historygroup_id-message_seq-count-reverse_order)
    - [get_private_message_history](#get_private_message_historyuser_id-message_seq-count-reverse_order)
- [PluginBase](#pluginbase) - 插件基类
- [事件类型](#事件类型)

---

## BotAPI

机器人 API 类，提供消息发送等功能。

### 访问方式

**主程序：**
```python
await bot.api.send_group_message(group_id, message)
await bot.api.send_private_message(user_id, message)
```

**插件中：**
```python
await self.api.send_group_message(group_id, message)
await self.api.send_private_message(user_id, message)
```

> **核心原则：** 插件只是模块化，API 调用与主程序完全一致，只需将 `bot.api` 换成 `self.api`。

### 消息发送

#### send_group_message(group_id, message, image_path, at_user_id, reply_message_id)

发送群消息。

```python
async def send_group_message(
    group_id: int, 
    message: str = "", 
    image_path: Optional[str] = None,
    at_user_id: Optional[int] = None,
    reply_message_id: Optional[int] = None
) -> Dict[str, Any]
```

**参数：**
- `group_id` (int): 群号
- `message` (str): 消息内容（可选，默认为空）
- `image_path` (str, optional): 图片文件路径（可选）
- `at_user_id` (int, optional): @的用户ID（可选）
- `reply_message_id` (int, optional): 回复的消息ID（可选）

**示例：**
```python
# 只发送文字
await self.api.send_group_message(123456, "大家好")

# 发送文字+图片
await self.api.send_group_message(123456, "查看图片", "./images/photo.jpg")

# @某人
await self.api.send_group_message(123456, "你好", at_user_id=789012)

# 回复消息
await self.api.send_group_message(123456, "收到", reply_message_id=12345)

# 组合使用：@ + 回复 + 图片
await self.api.send_group_message(
    123456, 
    "好的", 
    image_path="./images/ok.jpg",
    at_user_id=789012,
    reply_message_id=12345
)

# 只发送图片（无文字）
await self.api.send_group_message(123456, "", image_path="./images/photo.jpg")
```

**说明：**
- 所有参数都是可选的，可以灵活组合
- 如果提供了 `image_path` 且文件存在，会自动附加图片
- 使用 CQ 码格式构建消息

#### send_private_message(user_id, message, image_path, reply_message_id)

发送私聊消息。

```python
async def send_private_message(
    user_id: int, 
    message: str = "", 
    image_path: Optional[str] = None,
    reply_message_id: Optional[int] = None
) -> Dict[str, Any]
```

**参数：**
- `user_id` (int): 用户 QQ 号
- `message` (str): 消息内容（可选，默认为空）
- `image_path` (str, optional): 图片文件路径（可选）
- `reply_message_id` (int, optional): 回复的消息ID（可选）

**示例：**
```python
# 只发送文字
await self.api.send_private_message(789012, "你好")

# 发送文字+图片
await self.api.send_private_message(789012, "查看图片", "./images/photo.jpg")

# 回复消息
await self.api.send_private_message(789012, "收到", reply_message_id=12345)

# 组合使用：回复 + 图片
await self.api.send_private_message(
    789012, 
    "好的", 
    image_path="./images/ok.jpg",
    reply_message_id=12345
)

# 只发送图片（无文字）
await self.api.send_private_message(789012, "", image_path="./images/photo.jpg")
```

**说明：**
- 所有参数都是可选的，可以灵活组合
- 如果提供了 `image_path` 且文件存在，会自动附加图片
- 使用 CQ 码格式构建消息

#### send_group_message_segments(group_id, segments, reply_message_id)

发送群聊多格式混排消息。该方法使用 OneBot/NapCat 数组消息格式，适合文字、图片、@、表情、回复等消息段混合发送。

```python
from sdk.core import MessageSegment

async def send_group_message_segments(
    group_id: int,
    segments: List[Dict[str, Any]],
    reply_message_id: Optional[int] = None
) -> Dict[str, Any]
```

**参数：**
- `group_id` (int): 群号
- `segments` (list): 消息段列表，推荐使用 `MessageSegment` 构建
- `reply_message_id` (int, optional): 回复的消息 ID（可选，会自动插入到消息段开头）

**示例：**
```python
from sdk.core import MessageSegment

await self.api.send_group_message_segments(
    group_id=123456,
    segments=[
        MessageSegment.text("你好 "),
        MessageSegment.at(789012),
        MessageSegment.text("，请查看图片："),
        MessageSegment.image("./images/demo.png", summary="示例图片"),
        MessageSegment.text("\n再送你一个表情 "),
        MessageSegment.face(14),
    ],
)
```

**可用消息段：**
- `MessageSegment.text(content)` - 文本
- `MessageSegment.image(file, summary="")` - 图片，本地路径或 URL
- `MessageSegment.at(qq)` - @某人
- `MessageSegment.reply(message_id)` - 回复消息
- `MessageSegment.face(face_id)` - QQ 表情
- `MessageSegment.dice()` - 骰子
- `MessageSegment.rps()` - 猜拳
- `MessageSegment.json_data(data)` - JSON 卡片

#### send_private_message_segments(user_id, segments, reply_message_id)

发送私聊多格式混排消息，参数和群聊版本类似，只是目标从 `group_id` 改为 `user_id`。

```python
from sdk.core import MessageSegment

async def send_private_message_segments(
    user_id: int,
    segments: List[Dict[str, Any]],
    reply_message_id: Optional[int] = None
) -> Dict[str, Any]
```

**示例：**
```python
from sdk.core import MessageSegment

await self.api.send_private_message_segments(
    user_id=789012,
    segments=[
        MessageSegment.text("这是图文混排私聊消息："),
        MessageSegment.image("https://example.com/demo.png"),
        MessageSegment.text("\n发送完成"),
    ],
)
```

### Message 和多格式混排接收

当 NapCat 上报数组格式消息时，SDK 会解析为 `Message` 对象：

```python
from sdk.pluginsystem import group_server

@filter_registry.group_server(prefix="")
async def handle_group_message(self, event: GroupMessageEvent):
    text = event.message.plain_text
    raw = event.message.raw_message
    segments = event.message.segments
```

**字段说明：**
- `event.message.plain_text`: 从 `text` 消息段拼接出的纯文本，适合做命令判断
- `event.message.raw_message`: NapCat 上报的原始字符串内容
- `event.message.segments`: 原始消息段列表，适合读取图片、@、表情等非文本内容

**解析图片和 @ 示例：**
```python
from sdk.pluginsystem import group_server

@filter_registry.group_server(prefix="")
async def handle_group_message(self, event: GroupMessageEvent):
    images = []
    at_users = []

    for segment in event.message.segments:
        segment_type = segment.get("type")
        data = segment.get("data", {})

        if segment_type == "image":
            images.append(data.get("file"))
        elif segment_type == "at":
            at_users.append(data.get("qq"))

    if images:
        await self.reply_with_event(event, f"收到 {len(images)} 张图片")
```

**选择建议：**
- 只发纯文本或简单图片：用 `send_group_message()` / `send_private_message()`
- 需要文字、图片、@、表情、回复等按顺序混排：用 `send_group_message_segments()` / `send_private_message_segments()`
- 判断命令：优先用 `event.message.plain_text.strip()`
- 处理图片、@、表情等非文本内容：遍历 `event.message.segments`

### call(action, params)

通用 API 调用方法，可直接调用任意 OneBot API。

```python
async def call(action: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]
```

**参数：**
- `action` (str): API 动作名称，如 `send_msg`、`get_group_info` 等
- `params` (dict, optional): API 参数（可选）

**示例：**
```python
# 获取群信息
group_info = await self.api.call("get_group_info", {"group_id": 123456})

# 获取好友列表
friends = await self.api.call("get_friend_list")

# 发送自定义请求
result = await self.api.call("set_group_ban", {
    "group_id": 123456,
    "user_id": 789012,
    "duration": 600
})
```

**说明：**
- 所有 BotAPI 方法（如 send_group_message）底层都是通过 `call` 实现的
- 此方法提供更底层的访问能力，可调用未封装的 API
- 建议优先使用封装好的方法，只有在需要调用未封装 API 时使用此方法

---

## 消息管理API

### delete_message(message_id)

撤回/删除消息。

```python
async def delete_message(message_id: int) -> Dict[str, Any]
```

**参数：**
- `message_id` (int): 消息ID

**示例：**
```python
# 撤回消息
result = await self.api.send_group_message(123456, "这条消息会被撤回")
message_id = result.get("message_id")
await self.delay(2)  # 延迟2秒
await self.api.delete_message(message_id)
```

### get_message(message_id)

获取指定消息的详细信息。

```python
async def get_message(message_id: int) -> Dict[str, Any]
```

**参数：**
- `message_id` (int): 消息ID

**示例：**
```python
# 获取消息详情
msg_data = await self.api.get_message(message_id)
print(msg_data)
```

---

## 互动功能API

### group_poke(group_id, user_id)

群内戳一戳。

```python
async def group_poke(group_id: int, user_id: int) -> Dict[str, Any]
```

**参数：**
- `group_id` (int): 群号
- `user_id` (int): 要戳的用户ID

**示例：**
```python
# 戳一戳群友
await self.api.group_poke(123456, 789012)
```

### friend_poke(user_id)

好友戳一戳。

```python
async def friend_poke(user_id: int) -> Dict[str, Any]
```

**参数：**
- `user_id` (int): 要戳的用户ID

**示例：**
```python
# 戳一戳好友
await self.api.friend_poke(789012)
```

---

## 娱乐功能API

### send_group_dice(group_id)

发送群骰子消息。

```python
async def send_group_dice(group_id: int) -> Dict[str, Any]
```

**参数：**
- `group_id` (int): 群号

**示例：**
```python
# 发送骰子
await self.api.send_group_dice(123456)
```

### send_group_rps(group_id)

发送群猜拳消息（石头剪刀布）。

```python
async def send_group_rps(group_id: int) -> Dict[str, Any]
```

**参数：**
- `group_id` (int): 群号

**示例：**
```python
# 发送猜拳
await self.api.send_group_rps(123456)
```

### send_private_dice(user_id)

发送私聊骰子消息。

```python
async def send_private_dice(user_id: int) -> Dict[str, Any]
```

**参数：**
- `user_id` (int): 用户ID

**示例：**
```python
# 私聊发送骰子
await self.api.send_private_dice(789012)
```

### send_private_rps(user_id)

发送私聊猜拳消息。

```python
async def send_private_rps(user_id: int) -> Dict[str, Any]
```

**参数：**
- `user_id` (int): 用户ID

**示例：**
```python
# 私聊发送猜拳
await self.api.send_private_rps(789012)
```

---

## 消息历史API

### get_group_message_history(group_id, message_seq, count, reverse_order)

获取群消息历史记录。

```python
async def get_group_message_history(
    group_id: int, 
    message_seq: Optional[int] = None, 
    count: int = 20,
    reverse_order: bool = False
) -> Dict[str, Any]
```

**参数：**
- `group_id` (int): 群号
- `message_seq` (int, optional): 消息序号，提供则从该消息开始获取
- `count` (int): 获取数量，默认20
- `reverse_order` (bool): 是否倒序，默认False

**示例：**
```python
# 获取最近20条群消息
history = await self.api.get_group_message_history(123456, count=20)
messages = history.get("messages", [])
for msg in messages:
    print(msg.get("sender", {}).get("nickname"), msg.get("raw_message"))
```

### get_private_message_history(user_id, message_seq, count, reverse_order)

获取私聊消息历史记录。

```python
async def get_private_message_history(
    user_id: int,
    message_seq: int,
    count: int = 20,
    reverse_order: bool = False
) -> Dict[str, Any]
```

**参数：**
- `user_id` (int): 用户ID
- `message_seq` (int): 消息序号
- `count` (int): 获取数量，默认20
- `reverse_order` (bool): 是否倒序，默认False

**示例：**
```python
# 获取与某用户的聊天历史
history = await self.api.get_private_message_history(789012, message_seq=0, count=10)
messages = history.get("messages", [])
```

## PluginBase

插件基类，所有插件必须继承此类。

> **新版 API：** 插件现在只依赖 `IBotAPI` 接口和 `EventBus`，不再持有 `BotClient` 引用。事件处理支持强类型 `GroupMessageEvent`、`PrivateMessageEvent` 等 dataclass。

### 核心方法

#### on_load(api, event_bus, plugin_dir)

插件加载时调用。

```python
async def on_load(self, api: IBotAPI, event_bus: EventBus, plugin_dir: Optional[Path] = None)
```

**示例：**
```python
async def on_load(self, api, event_bus, plugin_dir=None):
    logger.info(f"插件 {self.name} 已加载")
    self.config = await self.load_config("config.json")
```

**说明：**
- `api`: `IBotAPI` 接口实例，可调用 `api.send_group_message()` 等
- `event_bus`: `EventBus` 实例，可订阅事件
- `plugin_dir`: 插件目录路径

#### on_unload()

插件卸载时调用。

```python
async def on_unload(self)
```

**示例：**
```python
async def on_unload(self):
    logger.info(f"插件 {self.name} 卸载中")
```

### 事件处理 ⭐ 必须使用过滤器

#### filter_registry.group_server / filter_registry.private_server

插件消息接收使用过滤器装饰器，分为群聊和私聊两类。

```python
from sdk.pluginsystem import PluginBase, filter_registry
from sdk.core.events import GroupMessageEvent, PrivateMessageEvent

class MyPlugin(PluginBase):
    def __init__(self):
        super().__init__()
        self.name = "my_plugin"

    @filter_registry.group_server
    async def group_ping(self, event: GroupMessageEvent):
        text = event.message.plain_text.strip()
        if text == "ping":
            await self.api.send_group_message(
                group_id=event.group_id,
                message="pong!"
            )

    @filter_registry.private_server
    async def private_echo(self, event: PrivateMessageEvent):
        text = event.message.plain_text.strip()
        if text.startswith("echo"):
            await self.api.send_private_message(
                user_id=event.user_id,
                message=text.removeprefix("echo").strip()
            )
```

**支持的过滤条件：**
- `equals`: 文本完全等于
- `keyword`: 包含单个关键词
- `keywords`: 包含任意关键词
- `contains`: 包含指定文本
- `prefix`: 指定前缀
- `prefixes`: 任意前缀
- `regex`: 正则匹配
- `custom`: 自定义过滤函数

**说明：**
- `@filter_registry.group_server` 只接收群聊消息，事件类型为 `GroupMessageEvent`
- `@filter_registry.private_server` 只接收私聊消息，事件类型为 `PrivateMessageEvent`
- 可以不传过滤条件，在函数内部按业务分支判断
- 多个过滤条件同时使用时是“并且”关系
- 当前版本不兼容重写 `on_group_message()` / `on_private_message()` 接收消息

#### reply_with_event(event, content) ⭐ 推荐

通过事件回复（自动识别群聊/私聊）。

```python
async def reply_with_event(event: Any, content: str)
```

**示例：**
```python
@filter_registry.group_server
async def group_help(self, event: GroupMessageEvent):
    if event.message.plain_text.strip() == "帮助":
        await self.reply_with_event(event, "群聊帮助")

@filter_registry.private_server
async def private_help(self, event: PrivateMessageEvent):
    if event.message.plain_text.strip() == "帮助":
        await self.reply_with_event(event, "私聊帮助")
```

### 旧版事件处理（已移除）

`on_group_message()` / `on_private_message()` 不再参与插件消息分发，旧插件必须迁移到 `filter_registry.group_server` / `filter_registry.private_server`。

### 工具方法

#### load_config(config_name)

加载插件配置（带缓存）。

```python
async def load_config(self, config_name: str = "config.json") -> Dict
```

**示例：**
```python
self.config = await self.load_config("config.json")
```

#### save_config(config, config_name)

保存插件配置。

```python
async def save_config(self, config: Dict, config_name: str = "config.json") -> bool
```

**示例：**
```python
await self.save_config(self.config)
```

#### create_task(coro)

创建后台任务（插件卸载时自动取消）。

```python
def create_task(self, coro: Coroutine) -> asyncio.Task
```

**示例：**
```python
async def background_job():
    while True:
        await asyncio.sleep(60)

self.create_task(background_job())
```

#### delay(seconds)

异步延迟。

```python
async def delay(self, seconds: float)
```

**示例：**
```python
await self.delay(1.5)  # 延迟 1.5 秒
```

### 属性

- `self.name` - 插件名称
- `self.version` - 插件版本
- `self.description` - 插件描述
- `self.author` - 作者
- `self.enabled` - 是否启用
- `self.api` - `IBotAPI` 接口实例
- `self.event_bus` - `EventBus` 实例

---

## 事件类型（强类型 dataclass）

### GroupMessageEvent

群消息事件（强类型）。

```python
@dataclass
class GroupMessageEvent(BaseEvent):
    group_id: int
    user_id: int
    message: Message
    raw_message: str
    message_id: int
    sender: Sender
    time: int
```

**属性：**
- `group_id`: 群号
- `user_id`: 发送者 QQ 号
- `message`: 消息对象（可用 `message.plain_text` 获取纯文本）
- `raw_message`: 原始消息字符串
- `message_id`: 消息 ID
- `sender`: 发送者信息
- `time`: 时间戳

### PrivateMessageEvent

私聊消息事件（强类型）。

```python
@dataclass
class PrivateMessageEvent(BaseEvent):
    user_id: int
    message: Message
    raw_message: str
    message_id: int
    sender: Sender
    time: int
```

### NoticeEvent

通知事件基类，包含：
- `GroupIncreaseNoticeEvent` - 群成员增加
- `GroupDecreaseNoticeEvent` - 群成员减少
- `GroupBanNoticeEvent` - 群禁言
- `FriendPokeNoticeEvent` - 好友戳一戳

### RequestEvent

请求事件基类，包含：
- `FriendRequestEvent` - 好友请求
- `GroupRequestEvent` - 加群请求

---

## 快速开始（新版插件示例）

### 最小插件示例（过滤器）

```python
import logging
from sdk.pluginsystem import PluginBase, filter_registry
from sdk.core.events import GroupMessageEvent, PrivateMessageEvent

logger = logging.getLogger(__name__)

class HelloPlugin(PluginBase):
    def __init__(self):
        super().__init__()
        self.name = "hello"
        self.version = "1.0.0"
        self.description = "Hello World 插件"
        self.author = "Your Name"

    @filter_registry.group_server(equals="你好")
    async def hello_group(self, event: GroupMessageEvent):
        await self.reply_with_event(event, "你好！我是群聊机器人")

    @filter_registry.private_server(equals="你好")
    async def hello_private(self, event: PrivateMessageEvent):
        await self.reply_with_event(event, "你好！我是私聊机器人")
```

### 使用 API

```python
@filter_registry.group_server(equals="测试")
async def test_group(self, event: GroupMessageEvent):
    await self.reply_with_event(event, "自动回复")
    await self.api.send_group_message(event.group_id, "直接发送")
```

---

**详细插件开发指南请查看：** [06_PLUGIN_DEVELOPMENT.md](./06_PLUGIN_DEVELOPMENT.md)
