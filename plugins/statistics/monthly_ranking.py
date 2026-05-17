"""
月度排行榜生成系统
统计当月用户发言总数
"""

from datetime import datetime
from typing import Dict, List, Any

from .data_manager import user_manager
from .speech_config import SpeechConfig


class MonthlyRankingSystem:
    """月度排行榜系统"""

    def __init__(self, users_dir: str = None, group_id: str = None):
        """初始化"""
        self.users_dir = users_dir or SpeechConfig.USERS_DIR
        self.group_id = str(group_id) if group_id is not None else None

    def calculate_monthly_stats(self, year: int = None, month: int = None, group_id: str = None) -> List[Dict[str, Any]]:
        """计算月度统计数据"""
        target_group_id = str(group_id) if group_id is not None else self.group_id
        if target_group_id is None:
            return []
        return user_manager.get_monthly_ranking_stats(target_group_id, year, month)

    def generate_monthly_ranking(self, year: int = None, month: int = None, top_n: int = 20, group_id: str = None) -> str:
        """生成月度排行榜报告"""
        if year is None or month is None:
            now = datetime.now()
            year = now.year
            month = now.month

        stats = self.calculate_monthly_stats(year, month, group_id)

        if not stats:
            return f"❌ {year}年{month}月 没有找到用户数据或没有用户在此期间发言"

        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append(f"🏆 发言月榜 ({year}年{month}月)")
        report_lines.append("=" * 80)
        report_lines.append(f"📊 总统计用户数: {len(stats)} (有发言记录的用户)")
        report_lines.append(f"📅 统计周期: {year}年{month}月")
        report_lines.append("")
        report_lines.append("排名 | 用户名           | 总发言数 | 活跃天数")
        report_lines.append("-" * 60)

        for i, user in enumerate(stats[:top_n], 1):
            report_lines.append(
                f"{i:4d} | {user['用户名']:15s} | "
                f"{user['总发言数']:7d} | {user['活跃天数']:8d}"
            )

        report_lines.append("")
        total_messages = sum(user["总发言数"] for user in stats)
        total_active_days = sum(user["活跃天数"] for user in stats)
        report_lines.append("📈 月度总结")
        report_lines.append("-" * 40)
        report_lines.append(f"• 总发言数: {total_messages:,} 条")
        report_lines.append(f"• 总活跃天数: {total_active_days:,} 天")
        report_lines.append(f"• 发言冠军: {stats[0]['用户名']} ({stats[0]['总发言数']} 条)")

        if len(stats) > 1:
            report_lines.append(f"• 发言亚军: {stats[1]['用户名']} ({stats[1]['总发言数']} 条)")
        if len(stats) > 2:
            report_lines.append(f"• 发言季军: {stats[2]['用户名']} ({stats[2]['总发言数']} 条)")

        report_lines.append("")
        report_lines.append("=" * 80)

        return "\n".join(report_lines)


def get_monthly_rankings(users_dir: str = None, year: int = None, month: int = None, top_n: int = 20, group_id: str = None) -> List[Dict[str, Any]]:
    """获取月度排行榜数据，供其他模块调用"""
    monthly_system = MonthlyRankingSystem(users_dir, group_id)
    stats = monthly_system.calculate_monthly_stats(year, month)
    return stats[:top_n]


def get_monthly_rankings_by_start_date(users_dir: str = None, start_date_str: str = None, top_n: int = 20, group_id: str = None) -> List[Dict[str, Any]]:
    """通过月份起始日期获取月度排行榜数据"""
    if start_date_str is None:
        now = datetime.now()
        year = now.year
        month = now.month
    else:
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
            year = start_date.year
            month = start_date.month
        except ValueError:
            print(f"❌ 日期格式错误: {start_date_str}")
            return []

    monthly_system = MonthlyRankingSystem(users_dir, group_id)
    stats = monthly_system.calculate_monthly_stats(year, month)
    return stats[:top_n]


def get_monthly_summary(users_dir: str = None, year: int = None, month: int = None, group_id: str = None) -> Dict[str, Any]:
    """获取月度统计摘要，供其他模块调用"""
    monthly_system = MonthlyRankingSystem(users_dir, group_id)
    stats = monthly_system.calculate_monthly_stats(year, month)

    if not stats:
        return {
            "total_users": 0,
            "total_messages": 0,
            "top_user": None
        }

    return {
        "total_users": len(stats),
        "total_messages": sum(user["总发言数"] for user in stats),
        "top_user": stats[0]
    }


def main():
    """主函数"""
    print("月度排行榜生成系统 v1.0")
    print("=" * 50)
    print("请通过机器人命令或传入 group_id 调用月榜统计")


if __name__ == "__main__":
    main()
