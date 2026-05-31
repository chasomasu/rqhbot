from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

from sdk.core.events import GroupMessageEvent, PrivateMessageEvent
from sdk.pluginsystem import PluginBase, filter_registry

from .data_manager import (
    user_manager,
    log_manager,
    load_user_data,
    save_user_data,
    get_display_username,
    user_exists,
    check_and_handle_week_transition,
)
from .speech_config import SpeechConfig
from .archive_manager import auto_archive

logger = logging.getLogger(__name__)


class RqhspeechPlugin(PluginBase):
    """Rqhspeech 发言统计插件 - 发言日榜、周榜、月榜、用户统计等功能"""

    def __init__(self):
        super().__init__()
        self.name = "rqhspeech"
        self.version = "4.0.0"
        self.config = {}

    async def on_load(self, api, event_bus, plugin_dir=None):
        await super().on_load(api, event_bus, plugin_dir)
        logger.info(f"插件 {self.name} 已加载 (v{self.version})")
        self.config = await self.load_config()

    async def on_unload(self):
        logger.info(f"插件 {self.name} 卸载中")

    def _format_rankings(self, title: str, rankings, top_n: int) -> str:
        lines = [f"{title}\n"]
        for i, (uid, count) in enumerate(rankings[:top_n], 1):
            ud = load_user_data(uid)
            name = get_display_username(ud, uid) if ud else uid
            medal = ["🥇", "🥈", "🥉"][i - 1] if i <= 3 else f"{i:2d}."
            lines.append(f"{medal} [{name}]: {count}条")
        return "\n".join(lines)

    @filter_registry.group_filter
    async def rqhbase_group(self, event: GroupMessageEvent):
        text = event.message.plain_text.strip()
        group_id = str(event.group_id)
        user_id = str(event.user_id)
        username = event.user_name or str(user_id)

        # 白名单检查
        if not SpeechConfig.is_allowed_group(group_id):
            return

        # 自动注册
        if not user_exists(user_id):
            user_data = user_manager.create_user(user_id, username)
            save_user_data(user_id, user_data)
            logger.info(f"自动注册新用户: {username}({user_id})")

        # 记录发言
        user_manager.update_user_message(user_id, group_id)

        # 日志
        user_data = load_user_data(user_id)
        if user_data:
            user_data, week_key = check_and_handle_week_transition(user_data)
            if week_key in user_data.get("weekly_stats", {}):
                week_data = user_data["weekly_stats"][week_key]
                if group_id in week_data:
                    gd = week_data[group_id]
                    today_str = datetime.now().strftime("%Y-%m-%d")
                    daily_count = gd["每日明细"].get(today_str, 0)
                    week_total = gd["累计数据"].get("总发言数", 0)
                    log_manager.log_message(user_id, username, group_id, daily_count, week_total)

        # 命令路由
        await self._route_command(event, text, user_id, group_id)

    @filter_registry.private_filter
    async def rqhbase_private(self, event: PrivateMessageEvent):
        text = event.message.plain_text.strip()
        user_id = str(event.user_id)
        username = event.user_name or str(user_id)
        group_id = "0"

        if not user_exists(user_id):
            user_data = user_manager.create_user(user_id, username)
            save_user_data(user_id, user_data)

        await self._route_command(event, text, user_id, group_id)

    async def _route_command(self, event, text: str, user_id: str, group_id: str):
        """命令路由"""
        if text == "注册":
            await self._cmd_register(event, user_id, event.user_name or user_id)
        elif text == "发言日榜":
            await self._cmd_daily_rank(event, group_id)
        elif text.startswith("历史日榜"):
            await self._cmd_history_rank(event, group_id, text)
        elif text == "我的发言":
            await self._cmd_my_stats(event, user_id, group_id)
        elif text == "发言周榜":
            await self._cmd_weekly_rank(event, group_id)
        elif text.startswith("历史周榜"):
            await self._cmd_history_weekly_rank(event, group_id, text)
        elif text == "发言月榜":
            await self._cmd_monthly_rank(event, group_id)
        elif text.startswith("历史月榜"):
            await self._cmd_history_monthly_rank(event, group_id, text)
        elif text == "发言季榜":
            await self._cmd_seasonal_rank(event, group_id)
        elif text == "发言年榜":
            await self._cmd_yearly_rank(event, group_id)
        elif text.startswith("历史年榜"):
            await self._cmd_history_yearly_rank(event, group_id, text)
        elif text.startswith("设置用户名"):
            await self._cmd_set_username(event, user_id, text)
        elif text.startswith("查询发言") or text.startswith("查发言"):
            await self._cmd_query_user(event, group_id, text)
        elif text.startswith("删除用户"):
            await self._cmd_delete_user(event, text)
        elif text == "自动归档":
            await self._cmd_auto_archive(event)
        elif text.startswith("加白名单") or text.startswith("加入白名单"):
            await self._cmd_add_group(event, text)
        elif text.startswith("移除白名单") or text.startswith("移出白名单"):
            await self._cmd_remove_group(event, text)
        elif text == "查看白名单":
            await self._cmd_view_whitelist(event)
        elif text.startswith("切换白名单模式"):
            await self._cmd_toggle_whitelist(event)
        elif text == "帮助":
            await self.reply_with_event(event, self._get_help_text())

    # ========== 命令实现 ==========

    async def _cmd_register(self, event, user_id: str, username: str):
        if user_exists(user_id):
            await self.reply_with_event(event, "❌ 用户已注册")
            return
        user_data = user_manager.create_user(user_id, username)
        save_user_data(user_id, user_data)
        await self.reply_with_event(event, f"✅ 用户 {username} ({user_id}) 已注册")

    async def _cmd_daily_rank(self, event, group_id: str):
        rankings = user_manager.get_daily_rankings(group_id)
        if not rankings:
            await self.reply_with_event(event, "暂无发言记录")
            return
        lines = ["📊 发言日榜 (本群)\n"]
        for i, (uid, count) in enumerate(rankings[:SpeechConfig.RANKING_DAILY_TOP_N], 1):
            ud = load_user_data(uid)
            name = get_display_username(ud, uid) if ud else uid
            medal = ["🥇", "🥈", "🥉"][i - 1] if i <= 3 else f"{i:2d}."
            lines.append(f"{medal} [{name}]: {count}条")
        await self.reply_with_event(event, "\n".join(lines))

    async def _cmd_history_rank(self, event, group_id: str, text: str):
        parts = text.split()
        if len(parts) != 2:
            await self.reply_with_event(event, "❌ 格式错误，请使用: 历史日榜 YYYY-MM-DD")
            return
        target_date = parts[1]
        try:
            datetime.strptime(target_date, "%Y-%m-%d")
        except ValueError:
            await self.reply_with_event(event, "❌ 日期格式错误，请使用 YYYY-MM-DD 格式")
            return
        rankings = user_manager.get_daily_rankings(group_id, target_date)
        if not rankings:
            await self.reply_with_event(event, f"📅 {target_date} 暂无发言记录")
            return
        lines = [f"📅 {target_date} 发言日榜 (本群)\n"]
        for i, (uid, count) in enumerate(rankings[:SpeechConfig.RANKING_DAILY_TOP_N], 1):
            ud = load_user_data(uid)
            name = get_display_username(ud, uid) if ud else uid
            medal = ["🥇", "🥈", "🥉"][i - 1] if i <= 3 else f"{i:2d}."
            lines.append(f"{medal} [{name}]: {count}条")
        await self.reply_with_event(event, "\n".join(lines))

    async def _cmd_my_stats(self, event, user_id: str, group_id: str):
        if not user_exists(user_id):
            await self.reply_with_event(event, "❌ 你未注册，请发送「注册」")
            return
        user_data = load_user_data(user_id)
        if not user_data:
            await self.reply_with_event(event, "❌ 获取数据失败")
            return
        user_data, week_key = check_and_handle_week_transition(user_data)
        today_count = week_total = 0
        daily_details = {}
        if week_key in user_data.get("weekly_stats", {}):
            wd = user_data["weekly_stats"][week_key]
            if group_id in wd:
                gd = wd[group_id]
                today_str = datetime.now().strftime("%Y-%m-%d")
                today_count = gd["每日明细"].get(today_str, 0)
                week_total = gd["累计数据"].get("总发言数", 0)
                daily_details = gd["每日明细"]
        month_total = user_manager.get_user_month_count(user_id, group_id)
        year_total = user_manager.get_user_year_count(user_id, group_id)
        summary = user_data.get("summary", {})
        total_messages = summary.get("total_messages", 0)
        total_weeks = summary.get("total_weeks", 0)

        lines = [
            "📊 你的发言统计（本群）\n",
            f"   今日发言: {today_count} 条",
            f"   本周发言: {week_total} 条",
            f"   本月发言: {month_total} 条",
            f"   本年发言: {year_total} 条\n",
        ]
        if daily_details:
            lines.append(f"📅 本周每日明细 ({week_key}):")
            for date in sorted(daily_details.keys()):
                weekday = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][datetime.strptime(date, "%Y-%m-%d").weekday()]
                lines.append(f"   {date} ({weekday}): {daily_details[date]} 条")
        lines.extend([
            "\n📈 累计统计:",
            f"   总发言数: {total_messages} 条",
            f"   活跃周数: {total_weeks} 周\n",
            "💪 继续努力！",
        ])
        await self.reply_with_event(event, "\n".join(lines))

    async def _cmd_weekly_rank(self, event, group_id: str):
        rankings = user_manager.get_weekly_rankings(group_id)
        if not rankings:
            await self.reply_with_event(event, "暂无发言记录")
            return
        lines = ["📊 发言周榜 (本群)\n"]
        for i, (uid, count) in enumerate(rankings[:SpeechConfig.RANKING_WEEKLY_TOP_N], 1):
            ud = load_user_data(uid)
            name = get_display_username(ud, uid) if ud else uid
            medal = ["🥇", "🥈", "🥉"][i - 1] if i <= 3 else f"{i:2d}."
            lines.append(f"{medal} [{name}]: {count}条")
        await self.reply_with_event(event, "\n".join(lines))

    async def _cmd_history_weekly_rank(self, event, group_id: str, text: str):
        parts = text.split()
        if len(parts) != 2:
            await self.reply_with_event(event, "❌ 格式错误，请使用:\n历史周榜 YYYY-MM-DD\n或\n历史周榜 W数字")
            return
        rankings, week_info = user_manager.get_historical_weekly_rankings(group_id, parts[1])
        if week_info in ["无效的周数", "周数格式错误", "日期格式错误，请使用 YYYY-MM-DD 格式"]:
            await self.reply_with_event(event, f"❌ {week_info}")
            return
        if not rankings:
            await self.reply_with_event(event, f"📅 {week_info} 暂无发言记录")
            return
        lines = [f"📊 {week_info} 发言周榜\n"]
        for i, (uid, count) in enumerate(rankings[:SpeechConfig.RANKING_WEEKLY_TOP_N], 1):
            ud = load_user_data(uid)
            name = get_display_username(ud, uid) if ud else uid
            medal = ["🥇", "🥈", "🥉"][i - 1] if i <= 3 else f"{i:2d}."
            lines.append(f"{medal} [{name}]: {count}条")
        await self.reply_with_event(event, "\n".join(lines))

    async def _cmd_monthly_rank(self, event, group_id: str):
        rankings = user_manager.get_monthly_rankings(group_id)
        if not rankings:
            await self.reply_with_event(event, "暂无月榜记录")
            return
        now = datetime.now()
        await self.reply_with_event(
            event,
            self._format_rankings(f"📊 发言月榜 ({now.year}年{now.month}月)", rankings, SpeechConfig.RANKING_MONTHLY_TOP_N)
        )

    async def _cmd_history_monthly_rank(self, event, group_id: str, text: str):
        parts = text.split()
        if len(parts) != 2:
            await self.reply_with_event(event, "❌ 格式错误，请使用: 历史月榜 YYYY-MM-DD")
            return
        try:
            target = datetime.strptime(parts[1], "%Y-%m-%d")
        except ValueError:
            await self.reply_with_event(event, "❌ 日期格式错误，请使用 YYYY-MM-DD 格式")
            return
        rankings = user_manager.get_monthly_rankings_by_start_date(group_id, parts[1])
        if not rankings:
            await self.reply_with_event(event, f"{target.year}年{target.month}月 暂无发言记录")
            return
        await self.reply_with_event(
            event,
            self._format_rankings(f"📊 {target.year}年{target.month}月 发言月榜", rankings, SpeechConfig.RANKING_MONTHLY_TOP_N)
        )

    async def _cmd_seasonal_rank(self, event, group_id: str):
        now = datetime.now()
        season = (now.month - 1) // 3 + 1
        season_name = {1: "春季", 2: "夏季", 3: "秋季", 4: "冬季"}[season]
        rankings = user_manager.get_seasonal_rankings(group_id)
        if not rankings:
            await self.reply_with_event(event, "暂无发言记录")
            return
        lines = [f"📊 发言季榜 ({now.year}年{season_name})\n"]
        for i, (uid, count) in enumerate(rankings[:SpeechConfig.RANKING_SEASONAL_TOP_N], 1):
            ud = load_user_data(uid)
            name = get_display_username(ud, uid) if ud else uid
            medal = ["🥇", "🥈", "🥉"][i - 1] if i <= 3 else f"{i:2d}."
            lines.append(f"{medal} [{name}]: {count}条")
        await self.reply_with_event(event, "\n".join(lines))

    async def _cmd_yearly_rank(self, event, group_id: str):
        rankings = user_manager.get_yearly_rankings(group_id)
        if not rankings:
            await self.reply_with_event(event, "暂无年榜记录")
            return
        year = datetime.now().year
        lines = [f"📊 发言年榜 ({year}年)\n"]
        for i, (uid, count) in enumerate(rankings[:SpeechConfig.RANKING_YEARLY_TOP_N], 1):
            ud = load_user_data(uid)
            name = get_display_username(ud, uid) if ud else uid
            medal = ["🥇", "🥈", "🥉"][i - 1] if i <= 3 else f"{i:2d}."
            lines.append(f"{medal} [{name}]: {count}条")
        await self.reply_with_event(event, "\n".join(lines))

    async def _cmd_history_yearly_rank(self, event, group_id: str, text: str):
        parts = text.split()
        if len(parts) != 2:
            await self.reply_with_event(event, "❌ 格式错误，请使用: 历史年榜 YYYY")
            return
        try:
            target_year = int(parts[1])
            if target_year < 2000 or target_year > 9999:
                raise ValueError
        except ValueError:
            await self.reply_with_event(event, "❌ 年份格式错误，请使用 YYYY 格式（如 2026）")
            return
        rankings = user_manager.get_yearly_rankings(group_id, target_year)
        if not rankings:
            await self.reply_with_event(event, f"{target_year}年 暂无发言记录")
            return
        lines = [f"📊 {target_year}年 发言年榜\n"]
        for i, (uid, count) in enumerate(rankings[:SpeechConfig.RANKING_YEARLY_TOP_N], 1):
            ud = load_user_data(uid)
            name = get_display_username(ud, uid) if ud else uid
            medal = ["🥇", "🥈", "🥉"][i - 1] if i <= 3 else f"{i:2d}."
            lines.append(f"{medal} [{name}]: {count}条")
        await self.reply_with_event(event, "\n".join(lines))

    async def _cmd_set_username(self, event, user_id: str, text: str):
        if not user_exists(user_id):
            await self.reply_with_event(event, "❌ 你未注册，请先发送「注册」")
            return
        new_name = text[5:].strip()
        if not new_name:
            await self.reply_with_event(event, "❌ 请提供要设置的用户名\n格式：设置用户名 你的新名字")
            return
        if len(new_name) > 20:
            await self.reply_with_event(event, "❌ 用户名过长，请控制在20个字符以内")
            return
        ud = load_user_data(user_id)
        old_name = get_display_username(ud, f"用户{user_id}")
        if user_manager.set_username(user_id, new_name):
            await self.reply_with_event(event, f"✅ 用户名已更新：{old_name} → {new_name}")
        else:
            await self.reply_with_event(event, "❌ 更新用户名失败")

    async def _cmd_query_user(self, event, group_id: str, text: str):
        target_user_id = None
        search_type = ""

        # 检查是否有 @用户 (从 segments 中找 at 段)
        for seg in event.message.segments:
            if seg.get("type") == "at":
                target_user_id = str(seg.get("data", {}).get("qq", ""))
                if target_user_id:
                    search_type = "@用户"
                    break

        if not target_user_id:
            query_param = text[4:].strip() if text.startswith("查询发言") else text[3:].strip()
            if not query_param:
                await self.reply_with_event(
                    event,
                    "❌ 请提供查询参数\n格式1：查询发言 QQ号\n格式2：查询发言 用户名\n格式3：查询发言 @用户",
                )
                return
            if query_param.isdigit():
                target_user_id = query_param
                search_type = "QQ号"
            else:
                target_user_id = user_manager.search_user_by_username(query_param)
                search_type = "用户名"

        if not target_user_id or not user_exists(target_user_id):
            if search_type == "@用户":
                await self.reply_with_event(event, "❌ 未找到该用户（可能未注册）")
            else:
                await self.reply_with_event(event, f"❌ 未找到{search_type}为 {target_user_id or '未知'} 的用户")
            return

        ud = load_user_data(target_user_id)
        if not ud:
            await self.reply_with_event(event, "❌ 获取用户数据失败")
            return
        target_name = get_display_username(ud, "未知用户")
        ud, week_key = check_and_handle_week_transition(ud)
        today_count = week_total = active_days = 0
        daily_details = {}
        if week_key in ud.get("weekly_stats", {}):
            wd = ud["weekly_stats"][week_key]
            if group_id in wd:
                gd = wd[group_id]
                today_str = datetime.now().strftime("%Y-%m-%d")
                today_count = gd["每日明细"].get(today_str, 0)
                week_total = gd["累计数据"].get("总发言数", 0)
                active_days = gd["累计数据"].get("活跃天数", 0)
                daily_details = gd["每日明细"]
        month_total = user_manager.get_user_month_count(target_user_id, group_id)
        year_total = user_manager.get_user_year_count(target_user_id, group_id)
        summary = ud.get("summary", {})
        total_messages = summary.get("total_messages", 0)
        total_weeks = summary.get("total_weeks", 0)
        avg_per_week = summary.get("avg_messages_per_week", 0)

        lines = [
            f"👤 用户 {target_name} ({target_user_id})\n",
            "📊 本群发言统计：",
            f"   今日发言: {today_count} 条",
            f"   本周发言: {week_total} 条",
            f"   本月发言: {month_total} 条",
            f"   本年发言: {year_total} 条",
            f"   活跃天数: {active_days} 天\n",
        ]
        if daily_details:
            lines.append(f"📅 本周每日明细 ({week_key}):")
            for date in sorted(daily_details.keys()):
                if daily_details[date] > 0:
                    weekday = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][datetime.strptime(date, "%Y-%m-%d").weekday()]
                    lines.append(f"   {date} ({weekday}): {daily_details[date]} 条")
        lines.extend([
            "\n📈 累计统计:",
            f"   总发言数: {total_messages} 条",
            f"   活跃周数: {total_weeks} 周",
            f"   周均发言: {avg_per_week} 条",
        ])
        await self.reply_with_event(event, "\n".join(lines))

    async def _cmd_delete_user(self, event, text: str):
        user_id = str(event.user_id)
        if not SpeechConfig.is_admin(user_id):
            await self.reply_with_event(event, "❌ 你没有权限执行此操作")
            return
        parts = text.split()
        if len(parts) != 2:
            await self.reply_with_event(event, "❌ 格式错误，请使用: 删除用户 QQ号")
            return
        target = parts[1]
        if not user_exists(target):
            await self.reply_with_event(event, f"❌ 用户 {target} 不存在")
            return
        from .data_manager import get_user_file
        try:
            Path(get_user_file(target)).unlink()
            await self.reply_with_event(event, f"✅ 用户 {target} 已删除")
        except Exception as e:
            await self.reply_with_event(event, f"❌ 删除用户失败: {e}")

    async def _cmd_auto_archive(self, event):
        user_id = str(event.user_id)
        if not SpeechConfig.is_admin(user_id):
            await self.reply_with_event(event, "❌ 你没有权限执行此操作")
            return
        await self.reply_with_event(event, "🔄 开始执行自动归档...")
        success, message = auto_archive()
        if success:
            reply = f"✅ 自动归档完成\n\n{message[:500]}" if len(message) > 500 else f"✅ 自动归档完成\n\n{message}"
        else:
            reply = f"❌ 自动归档失败\n\n{message}"
        await self.reply_with_event(event, reply)

    async def _cmd_add_group(self, event, text: str):
        user_id = str(event.user_id)
        if not SpeechConfig.is_admin(user_id):
            await self.reply_with_event(event, "❌ 你没有权限执行此操作")
            return
        parts = text.split()
        if len(parts) != 2:
            await self.reply_with_event(event, "❌ 格式错误，请使用：加白名单 QQ群号")
            return
        group_id = parts[1]
        if not group_id.isdigit():
            await self.reply_with_event(event, "❌ 群号必须是数字")
            return
        SpeechConfig.add_allowed_group(group_id)
        await self.reply_with_event(event, f"✅ 已将群 {group_id} 加入白名单")

    async def _cmd_remove_group(self, event, text: str):
        user_id = str(event.user_id)
        if not SpeechConfig.is_admin(user_id):
            await self.reply_with_event(event, "❌ 你没有权限执行此操作")
            return
        parts = text.split()
        if len(parts) != 2:
            await self.reply_with_event(event, "❌ 格式错误，请使用：移除白名单 QQ群号")
            return
        group_id = parts[1]
        if not group_id.isdigit():
            await self.reply_with_event(event, "❌ 群号必须是数字")
            return
        SpeechConfig.remove_allowed_group(group_id)
        await self.reply_with_event(event, f"✅ 已将群 {group_id} 移出白名单")

    async def _cmd_view_whitelist(self, event):
        user_id = str(event.user_id)
        if not SpeechConfig.is_admin(user_id):
            await self.reply_with_event(event, "❌ 你没有权限执行此操作")
            return
        groups = SpeechConfig.get_allowed_groups_list()
        if not groups:
            await self.reply_with_event(event, "📋 当前白名单为空\n💡 使用「加白名单 QQ群号」添加")
            return
        lines = [f"📋 白名单列表 ({len(groups)} 个群)\n"]
        for i, gid in enumerate(sorted(groups), 1):
            lines.append(f"{i}. {gid}")
        lines.append("\n💡 使用「移除白名单 QQ群号」移除")
        await self.reply_with_event(event, "\n".join(lines))

    async def _cmd_toggle_whitelist(self, event):
        user_id = str(event.user_id)
        if not SpeechConfig.is_admin(user_id):
            await self.reply_with_event(event, "❌ 你没有权限执行此操作")
            return
        SpeechConfig.USE_WHITELIST_MODE = not SpeechConfig.USE_WHITELIST_MODE
        SpeechConfig._save_allowed_groups()
        mode_text = "✅ 已开启" if SpeechConfig.USE_WHITELIST_MODE else "❌ 已关闭"
        mode_desc = "仅白名单群可用" if SpeechConfig.USE_WHITELIST_MODE else "所有群可用"
        await self.reply_with_event(event, f"{mode_text}白名单模式\n当前状态：{mode_desc}")

    def _get_help_text(self) -> str:
        return (
            "📜 统计插件帮助\n\n"
            "📝 基础命令\n"
            "- 注册 - 注册新用户\n"
            "- 我的发言 - 查看自己的发言统计\n"
            "- 设置用户名 名字 - 设置显示名称\n"
            "- 查询发言 QQ号/用户名/@用户 - 查询他人统计\n\n"
            "🏆 排行榜\n"
            "- 发言日榜 - 今日排行\n"
            "- 发言周榜 - 本周排行\n"
            "- 发言月榜 - 本月排行\n"
            "- 发言季榜 - 本季排行\n"
            "- 发言年榜 - 本年排行\n"
            "- 历史日榜 YYYY-MM-DD\n"
            "- 历史周榜 YYYY-MM-DD / W数字\n"
            "- 历史月榜 YYYY-MM-DD\n"
            "- 历史年榜 YYYY\n\n"
            "⚙️ 管理员命令\n"
            "- 加白名单 群号\n"
            "- 移除白名单 群号\n"
            "- 查看白名单\n"
            "- 切换白名单模式\n"
            "- 自动归档\n"
            "- 删除用户 QQ号"
        )
