"""
配置文件 - 用于存储路径和配置常量
根据got.txt建议优化：
1. 统一配置管理
2. 添加更多实用配置项
3. 优化目录结构
4. 允许的群聊列表从JSON文件读取
"""

import json
import os
from datetime import datetime


class SpeechConfig:
    """配置类 - 封装所有配置常量"""

    def __init__(self):
        self.BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        self.DATA_DIR = os.path.join(self.BASE_DIR, "data")
        self.USERS_DIR = os.path.join(self.DATA_DIR, "users")
        self.ARCHIVES_DIR = os.path.join(self.DATA_DIR, "archives")
        self.DAILY_RANKINGS_DIR = os.path.join(self.ARCHIVES_DIR, "daily")
        self.WEEKLY_RANKINGS_DIR = os.path.join(self.ARCHIVES_DIR, "weekly")
        self.BACKUPS_DIR = os.path.join(self.DATA_DIR, "backups")
        self.DAILY_DATA_DIR = os.path.join(self.BACKUPS_DIR, "daily_all_zongjie")
        self.WEEKLY_DATA_DIR = os.path.join(self.BACKUPS_DIR, "weekly_all_zongjie")
        self.MONTHLY_DATA_DIR = os.path.join(self.DATA_DIR, "monthly")
        self.SEASONAL_DATA_DIR = os.path.join(self.DATA_DIR, "seasonal")
        self.YEARLY_DATA_DIR = os.path.join(self.DATA_DIR, "yearly")
        self.LOGS_DIR = os.path.join(self.DATA_DIR, "logs")

        self.LEGACY_USERS_DIR = os.path.join(self.BASE_DIR, "base_data", "users")
        self.LEGACY_DAILY_DATA_ROOT = os.path.join(self.BASE_DIR, "daily_data")
        self.LEGACY_DAILY_DATA_DIR = os.path.join(self.LEGACY_DAILY_DATA_ROOT, "daily_all_zongjie")
        self.LEGACY_DAILY_RANKINGS_DIR = os.path.join(self.LEGACY_DAILY_DATA_ROOT, "rankings")
        self.LEGACY_WEEKLY_DATA_ROOT = os.path.join(self.BASE_DIR, "weekly_data")
        self.LEGACY_WEEKLY_DATA_DIR = os.path.join(self.LEGACY_WEEKLY_DATA_ROOT, "weekly_all_zongjie")
        self.LEGACY_LOGS_DIR = os.path.join(self.BASE_DIR, "logs")

        self.CONFIG_FILE = os.path.join(self.BASE_DIR, "speech_config.json")

        self.ALLOWED_GROUPS = self._load_allowed_groups()
        self.ADMIN_USERS = self._load_admin_users()

        self.USE_WHITELIST_MODE = False

        self.USER_FILE_EXTENSION = ".json"
        self.RANKING_FILE_EXTENSION = ".json"
        self.CSV_FILE_EXTENSION = ".csv"
        self.LOG_FILE_EXTENSION = ".log"

        self.RANKING_TOP_N = 20
        self.RANKING_DAILY_TOP_N = 15
        self.RANKING_WEEKLY_TOP_N = 10
        self.RANKING_MONTHLY_TOP_N = 10
        self.RANKING_SEASONAL_TOP_N = 10
        self.RANKING_YEARLY_TOP_N = 10
        self.MIN_MESSAGES_FOR_RANKING = 1

        self.DATE_FORMAT = "%Y-%m-%d"
        self.DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
        self.DISPLAY_DATE_FORMAT = "%Y年%m月%d日"

        self.ARCHIVE_DAILY = True
        self.BACKUP_BEFORE_ARCHIVE = True
        self.ENABLE_LOGGING = True

        self._init_directories()

    def _load_allowed_groups(self):
        """从 JSON 文件加载允许的群聊列表"""
        if os.path.exists(self.CONFIG_FILE):
            try:
                with open(self.CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    allowed_groups = config.get("allowed_groups", [])
                    self.USE_WHITELIST_MODE = config.get("use_whitelist_mode", False)
                    return set(str(group_id) for group_id in allowed_groups)
            except Exception as e:
                print(f"加载允许的群聊列表失败：{e}")
                return set()
        else:
            default_config = {
                "allowed_groups": [],
                "admin_users": [],
                "use_whitelist_mode": False
            }
            self._save_config(default_config)
            return set()

    def _load_admin_users(self):
        """从JSON文件加载管理员列表"""
        if os.path.exists(self.CONFIG_FILE):
            try:
                with open(self.CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    admin_users = config.get("admin_users", [])
                    return set(str(user_id) for user_id in admin_users)
            except Exception as e:
                print(f"加载管理员列表失败: {e}")
                return set()
        else:
            return set()

    def _save_config(self, config):
        """保存配置到JSON文件"""
        try:
            with open(self.CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存配置文件失败: {e}")

    def add_allowed_group(self, group_id):
        """添加允许的群聊"""
        self.ALLOWED_GROUPS.add(str(group_id))
        self._save_allowed_groups()

    def remove_allowed_group(self, group_id):
        """移除允许的群聊"""
        self.ALLOWED_GROUPS.discard(str(group_id))
        self._save_allowed_groups()

    def add_admin_user(self, user_id):
        """添加管理员"""
        self.ADMIN_USERS.add(str(user_id))
        self._save_allowed_groups()

    def remove_admin_user(self, user_id):
        """移除管理员"""
        self.ADMIN_USERS.discard(str(user_id))
        self._save_allowed_groups()

    def _save_allowed_groups(self):
        """保存允许的群聊列表和管理员列表到JSON文件"""
        try:
            config = {
                "allowed_groups": list(self.ALLOWED_GROUPS),
                "admin_users": list(self.ADMIN_USERS)
            }
            self._save_config(config)
        except Exception as e:
            print(f"保存配置失败: {e}")

    def get_allowed_groups_list(self):
        """获取允许的群聊列表（返回列表格式）"""
        return list(self.ALLOWED_GROUPS)

    def _init_directories(self):
        """初始化所有需要的目录"""
        directories = [
            self.DATA_DIR,
            self.USERS_DIR,
            self.ARCHIVES_DIR,
            self.DAILY_RANKINGS_DIR,
            self.WEEKLY_RANKINGS_DIR,
            self.BACKUPS_DIR,
            self.DAILY_DATA_DIR,
            self.WEEKLY_DATA_DIR,
            self.MONTHLY_DATA_DIR,
            self.SEASONAL_DATA_DIR,
            self.YEARLY_DATA_DIR,
            self.LOGS_DIR,
        ]
        for directory in directories:
            os.makedirs(directory, exist_ok=True)

    def resolve_existing_file(self, primary_file, legacy_file=None):
        """优先使用规范路径，缺失时兼容读取旧路径"""
        if os.path.exists(primary_file):
            return primary_file
        if legacy_file and os.path.exists(legacy_file):
            return legacy_file
        return primary_file

    def get_current_date(self):
        """获取当前日期字符串"""
        return datetime.now().strftime(self.DATE_FORMAT)

    def get_current_datetime(self):
        """获取当前日期时间字符串"""
        return datetime.now().strftime(self.DATETIME_FORMAT)

    def get_ranking_filename(self, date=None):
        """获取排行榜文件名"""
        if date is None:
            date = self.get_current_date()
        return f"ranking_{date}{self.RANKING_FILE_EXTENSION}"

    def get_csv_filename(self, date=None):
        """获取CSV文件名"""
        if date is None:
            date = self.get_current_date()
        return f"ranking_{date}{self.CSV_FILE_EXTENSION}"

    def get_log_filename(self):
        """获取日志文件名"""
        return f"speech_{self.get_current_date()}{self.LOG_FILE_EXTENSION}"

    def is_allowed_group(self, group_id):
        """检查群聊是否在允许列表中（根据 got.txt 建议：group_id 转为字符串比较）"""
        if not self.USE_WHITELIST_MODE:
            return True
        return str(group_id) in self.ALLOWED_GROUPS

    def is_admin(self, user_id):
        """检查用户是否为管理员"""
        return str(user_id) in self.ADMIN_USERS


SpeechConfig = SpeechConfig()

BASE_DIR = SpeechConfig.BASE_DIR
DATA_DIR = SpeechConfig.DATA_DIR
USERS_DIR = SpeechConfig.USERS_DIR
ARCHIVES_DIR = SpeechConfig.ARCHIVES_DIR
DAILY_RANKINGS_DIR = SpeechConfig.DAILY_RANKINGS_DIR
WEEKLY_RANKINGS_DIR = SpeechConfig.WEEKLY_RANKINGS_DIR
BACKUPS_DIR = SpeechConfig.BACKUPS_DIR
DAILY_DATA_DIR = SpeechConfig.DAILY_DATA_DIR
WEEKLY_DATA_DIR = SpeechConfig.WEEKLY_DATA_DIR
MONTHLY_DATA_DIR = SpeechConfig.MONTHLY_DATA_DIR
SEASONAL_DATA_DIR = SpeechConfig.SEASONAL_DATA_DIR
YEARLY_DATA_DIR = SpeechConfig.YEARLY_DATA_DIR
LOGS_DIR = SpeechConfig.LOGS_DIR
ALLOWED_GROUPS = SpeechConfig.ALLOWED_GROUPS
ADMIN_USERS = SpeechConfig.ADMIN_USERS
USER_FILE_EXTENSION = SpeechConfig.USER_FILE_EXTENSION
RANKING_FILE_EXTENSION = SpeechConfig.RANKING_FILE_EXTENSION
CSV_FILE_EXTENSION = SpeechConfig.CSV_FILE_EXTENSION
LOG_FILE_EXTENSION = SpeechConfig.LOG_FILE_EXTENSION
RANKING_TOP_N = SpeechConfig.RANKING_TOP_N
RANKING_DAILY_TOP_N = SpeechConfig.RANKING_DAILY_TOP_N
RANKING_WEEKLY_TOP_N = SpeechConfig.RANKING_WEEKLY_TOP_N
RANKING_MONTHLY_TOP_N = SpeechConfig.RANKING_MONTHLY_TOP_N
RANKING_SEASONAL_TOP_N = SpeechConfig.RANKING_SEASONAL_TOP_N
RANKING_YEARLY_TOP_N = SpeechConfig.RANKING_YEARLY_TOP_N
MIN_MESSAGES_FOR_RANKING = SpeechConfig.MIN_MESSAGES_FOR_RANKING
DATE_FORMAT = SpeechConfig.DATE_FORMAT
DATETIME_FORMAT = SpeechConfig.DATETIME_FORMAT
DISPLAY_DATE_FORMAT = SpeechConfig.DISPLAY_DATE_FORMAT
ARCHIVE_DAILY = SpeechConfig.ARCHIVE_DAILY
BACKUP_BEFORE_ARCHIVE = SpeechConfig.BACKUP_BEFORE_ARCHIVE
ENABLE_LOGGING = SpeechConfig.ENABLE_LOGGING
get_current_date = SpeechConfig.get_current_date
get_current_datetime = SpeechConfig.get_current_datetime
get_ranking_filename = SpeechConfig.get_ranking_filename
get_csv_filename = SpeechConfig.get_csv_filename
get_log_filename = SpeechConfig.get_log_filename
is_allowed_group = SpeechConfig.is_allowed_group
is_admin = SpeechConfig.is_admin
