from .main import CultivationPlugin

def setup(bot):
    """插件入口函数"""
    plugin = CultivationPlugin()
    bot.register_plugin(plugin)

__all__ = ["CultivationPlugin"]
