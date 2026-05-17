from .main import KinkusPlugin

def setup(bot):
    """插件入口函数"""
    plugin = KinkusPlugin()
    bot.register_plugin(plugin)

__all__ = ["KinkusPlugin"]
