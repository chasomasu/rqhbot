"""
rqhspeech_v2 插件 - 根据got.txt建议优化的群聊发言统计管理程序

主要优化点：
1. 修复group_id类型不一致问题（统一转为字符串）
2. 修复设置用户名乱码键名bug
3. 统一命令格式（查询发言）
4. 封装公共函数（获取用户名、加载/保存数据）
5. 优化周切换函数参数
6. 使用logging模块替代手写日志
7. 代码结构拆分，更易维护
8. 添加管理员权限检查
9. 管理器全局单例，避免重复实例化
10. 命令处理函数独立到 command_handler.py
"""

from ncatbot.plugin_system import filter_registry, NcatBotPlugin
from ncatbot.core import GroupMessage
from datetime import datetime, timedelta

from .speech_config import SpeechConfig
from .data_manager import (
    user_manager, log_manager,
    load_user_data, get_display_username,
    user_exists, check_and_handle_week_transition
)
from .archive_manager import DailyArchiver, auto_archive
from .command_handler import CommandHandler


class rqhspeech(NcatBotPlugin):
    """rqhspeech 发言统计插件"""

    name = "rqhspeech"
    version = "4.0.0"
    dependencies = {}

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        # 根据got.txt建议：管理器全局单例，避免重复实例化
        self.user_mgr = user_manager
        self.log_mgr = log_manager
        # 初始化命令处理器
        self.cmd_handler = CommandHandler(self.user_mgr, self.log_mgr)

    async def on_load(self):
        """插件加载时调用"""
        print(f"✅ {self.name} 插件已加载")
        print(f"📦 插件版本：{self.version}")
            
        # 显示当前模式
        if SpeechConfig.USE_WHITELIST_MODE:
            print(f"🔒 当前模式：白名单模式（仅允许 {len(SpeechConfig.ALLOWED_GROUPS)} 个群）")
        else:
            print(f"🌐 当前模式：所有群可用")

    # ========== 核心消息处理 ==========

    @filter_registry.group_filter
    async def handle_message(self, event: GroupMessage):
        """
        处理群消息
        根据got.txt建议：
        1. group_id转为字符串
        2. 自动注册用户
        3. 更新发言统计
        """
        # 获取消息内容
        m = "".join(seg.text for seg in event.message.filter_text())

        # 根据got.txt建议：group_id转为字符串
        group_id = str(event.group_id)
        user_id = str(event.sender.user_id)
        username = event.sender.nickname

        # 检查是否在允许群聊中
        if not SpeechConfig.is_allowed_group(group_id):
            return False

        # 检查用户是否存在，不存在则自动注册
        exists = user_exists(user_id)

        if not exists:
            # 自动注册新用户
            user_data = self.user_mgr.create_user(user_id, username)
            from .data_manager import save_user_data
            save_user_data(user_id, user_data)
            print(f"✅ 自动为新用户 {username}({user_id}) 创建用户文件")
            exists = True

        # 更新发言统计
        if exists:
            self.user_mgr.update_user_message(user_id, group_id)

            # 获取更新后的数据用于日志
            user_data = load_user_data(user_id)
            if user_data:
                user_data, current_week_key = check_and_handle_week_transition(user_data)

                if current_week_key in user_data.get("weekly_stats", {}):
                    week_data = user_data["weekly_stats"][current_week_key]
                    if group_id in week_data:
                        group_data = week_data[group_id]
                        current_date_str = datetime.now().strftime("%Y-%m-%d")
                        daily_count = group_data["每日明细"].get(current_date_str, 0)
                        week_total = group_data["累计数据"].get("总发言数", 0)

                        # 记录日志
                        self.log_mgr.log_message(user_id, username, group_id, daily_count, week_total)

        # ========== 命令处理 ==========

        # 注册命令
        if m == "注册":
            return await self.cmd_handler.handle_register(event, user_id, username)

        # 发言日榜
        elif m == "发言日榜":
            return await self.cmd_handler.handle_daily_rank(event, group_id)

        # 历史日榜
        elif m.startswith("历史日榜"):
            return await self.cmd_handler.handle_history_rank(event, group_id, m)

        # 我的发言
        elif m == "我的发言":
            return await self.cmd_handler.handle_my_stats(event, user_id, group_id)

        # 发言周榜
        elif m == "发言周榜":
            return await self.cmd_handler.handle_weekly_rank(event, group_id)
        
        # 历史周榜 - 新增
        elif m.startswith("历史周榜"):
            return await self.cmd_handler.handle_history_weekly_rank(event, group_id, m)
        
        # 发言月榜 - 新增
        elif m == "发言月榜":
            return await self.cmd_handler.handle_monthly_rank(event, group_id)
        
        # 历史月榜 - 新增
        elif m.startswith("历史月榜"):
            return await self.cmd_handler.handle_history_monthly_rank(event, group_id, m)
        
        # 发言季榜 - 新增
        elif m == "发言季榜":
            return await self.cmd_handler.handle_seasonal_rank(event, group_id)
        
        # 发言年榜 - 新增
        elif m == "发言年榜":
            return await self.cmd_handler.handle_yearly_rank(event, group_id)
        
        # 历史年榜 - 新增
        elif m.startswith("历史年榜"):
            return await self.cmd_handler.handle_history_yearly_rank(event, group_id, m)

        # 设置用户名 - 根据got.txt建议修复
        elif m.startswith("设置用户名"):
            return await self.cmd_handler.handle_set_username(event, user_id, m)

        # 查询发言 - 根据got.txt建议统一命令格式
        elif m.startswith("查询发言") or m.startswith("查发言"):
            return await self.cmd_handler.handle_query_user(event, group_id, m)

        # 管理员命令
        elif m.startswith("删除用户"):
            return await self.cmd_handler.handle_delete_user(event, m)
        elif m == "自动归档":
            return await self.cmd_handler.handle_auto_archive(event)
        
        # 群管理命令
        elif m.startswith("加白名单") or m.startswith("加入白名单"):
            return await self.cmd_handler.handle_add_group(event, m)
        elif m.startswith("移除白名单") or m.startswith("移出白名单"):
            return await self.cmd_handler.handle_remove_group(event, m)
        elif m == "查看白名单":
            return await self.cmd_handler.handle_view_whitelist(event)
        elif m.startswith("切换白名单模式"):
            return await self.cmd_handler.handle_toggle_whitelist_mode(event)

        return False
