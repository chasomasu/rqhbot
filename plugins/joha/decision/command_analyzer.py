"""
命令分析器 - 自然语言指令解析
将用户的自然语言转化为具体的工具调用或动作
"""
import json
from typing import Dict, Optional
from joha.ai.clients import create_client_from_provider
from joha.ai.providers import provider_manager, Provider
from joha.config.managers.config_manager import config as config_manager
from joha.config.infrastructure.logger import tprint


class CommandAnalyzer:
    """自然语言命令分析器"""

    def __init__(self):
        self.provider = None
        self._init_provider()

    def _init_provider(self):
        """初始化工具调用专用的 Provider"""
        tool_config = config_manager.get("tool_calling", {})
        if not tool_config.get("enabled", False):
            return

        provider_name = tool_config.get("provider_name", "")
        if provider_name:
            # 优先从 _available_configs 查找，支持独立密钥
            available = config_manager.get("intent_recognition._available_configs", {})
            conf = available.get(provider_name)
            if conf:
                self.provider = Provider(
                    name=provider_name,
                    role="tool_caller",
                    api_key=conf.get("api_key", ""),
                    base_url=conf.get("base_url", ""),
                    model=conf.get("model", "")
                )
            else:
                self.provider = provider_manager.get(provider_name)
        
        if not self.provider:
            self.provider = provider_manager.get_default("chat")

        if self.provider:
            self.client = create_client_from_provider(self.provider, client_type="chat", enable_tools=False)
            tprint("info", f"[CommandAnalyzer] 已加载: {self.provider.name} ({self.provider.model})")

    def analyze(self, text: str) -> Dict[str, any]:
        """
        分析用户输入，判断是否需要调用工具
        返回格式: {
            'action': 'chat' | 'search' | 'knowledge' | 'webpage',
            'query': str,
            'confidence': float
        }
        """
        if not self.provider:
            return {'action': 'chat', 'query': text, 'confidence': 1.0}

        prompt = f"""请分析以下用户输入的意图。如果用户想查询实时信息、新闻、天气或事实性知识，请选择 'search'。
如果用户想查找项目历史、过往对话或本地记录，请选择 'knowledge'。
如果用户提供了 URL 并希望了解内容，请选择 'webpage'。
否则选择 'chat'。

用户输入：{text}

只返回 JSON 格式：
{{"action": "chat/search/knowledge/webpage", "query": "提取出的搜索关键词或原话", "confidence": 0.9}}
"""
        messages = [{"role": "user", "content": prompt}]
        
        try:
            response = self.client.call_with_context(messages, temperature=0.1, max_tokens=100)
            response = response.strip()
            if response.startswith('```'):
                response = response.split('\n', 1)[-1].rsplit('\n', 1)[0]
            
            result = json.loads(response)
            return {
                'action': result.get('action', 'chat'),
                'query': result.get('query', text),
                'confidence': result.get('confidence', 0.5)
            }
        except Exception as e:
            tprint("warning", f"[CommandAnalyzer] 分析失败: {e}")
            return {'action': 'chat', 'query': text, 'confidence': 0.0}

# 全局实例
command_analyzer = CommandAnalyzer()
