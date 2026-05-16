"""
通用 AI Bot 模块
支持任意 OpenAI 兼容 API，支持工具调用（搜索、网页抓取、知识库查询）
使用统一的 AI 客户端架构
"""
from typing import List, Dict, Optional
from joha.ai.clients import create_client_from_provider, BaseAIClient
from joha.decision.tools import SearchTool, WebpageTool, kb_search_tool
from joha.ai.providers import provider_manager
from joha.config.infrastructure.logger import tprint


class AIBot:
    """通用 AI 对话机器人（支持工具调用）"""

    def __init__(
        self,
        provider_name: str = "",
        system_prompt: Optional[str] = None,
        enable_tools: bool = True,
    ):
        if provider_name:
            self.provider = provider_manager.get(provider_name)
        else:
            self.provider = provider_manager.get_default("chat")

        if not self.provider:
            raise RuntimeError("没有可用的 chat provider，请检查 config.json 中的 providers 配置")

        # 某些提供商不支持工具调用，需要禁用
        providers_without_tools = ["teatop"]  # 根据错误日志，teatop 不支持工具调用
        should_enable_tools = enable_tools and self.provider.name not in providers_without_tools
        
        if should_enable_tools != enable_tools:
            tprint("warning", f"[AIBot] 提供商 {self.provider.name} 不支持工具调用，已自动禁用")

        # 使用统一的 AI 客户端
        self.client = create_client_from_provider(self.provider, client_type="chat", enable_tools=should_enable_tools)
        self.model = self.provider.model
        self.provider_name = self.provider.name
        tprint("info", f"[AIBot] 使用 provider: {self.provider_name} (模型: {self.model})")

        self.conversation_history: List[Dict[str, str]] = []
        if system_prompt:
            self.set_system_prompt(system_prompt)

        self.enable_tools = should_enable_tools
        if should_enable_tools:
            self.search_tool = SearchTool()
            self.webpage_tool = WebpageTool()
            self._register_tools()

    def _get_tool_definitions(self) -> List[Dict]:
        """获取工具定义列表"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "search_web",
                    "description": "搜索互联网获取最新信息。当需要查找实时信息、新闻、文档时使用。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "搜索查询关键词"},
                            "num_results": {"type": "integer", "description": "返回结果数量，默认5", "default": 5},
                        },
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "fetch_webpage",
                    "description": "抓取并提取网页内容。当用户提供 URL 或需要查看具体网页内容时使用。",
                    "parameters": {
                        "type": "object",
                        "properties": {"url": {"type": "string", "description": "要抓取的网页 URL"}},
                        "required": ["url"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "search_knowledge_base",
                    "description": (
                        "搜索本地知识库获取历史对话和知识。"
                        "当需要查找项目相关的历史信息、过往讨论、技术方案、群聊记录或已有解决方案时使用。"
                        "支持按时间范围搜索（days 参数）。"
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "搜索查询关键词"},
                            "num_results": {"type": "integer", "description": "返回结果数量，默认5", "default": 5},
                            "days": {"type": "integer", "description": "仅搜索最近 N 天的内容，不填则搜索全部", "default": None},
                        },
                        "required": ["query"],
                    },
                },
            }
        ]
    
    def _get_tool_handlers(self) -> Dict[str, callable]:
        """获取工具处理函数映射"""
        return {
            "search_web": lambda args: self._handle_search(args),
            "fetch_webpage": lambda args: self._handle_webpage(args),
            "search_knowledge_base": lambda args: self._handle_knowledge_search(args)
        }
    
    def _handle_search(self, args: Dict) -> str:
        """处理搜索请求"""
        query = args.get("query", "")
        num_results = args.get("num_results", 5)
        tprint("info", f"[工具调用] 搜索: {query}")
        try:
            return self.search_tool.search(query, num_results)
        except Exception as e:
            return f"搜索失败: {str(e)}"
    
    def _handle_webpage(self, args: Dict) -> str:
        """处理网页抓取请求"""
        url = args.get("url", "")
        tprint("info", f"[工具调用] 抓取网页: {url}")
        try:
            return self.webpage_tool.fetch(url)
        except Exception as e:
            return f"抓取失败: {str(e)}"

    def _handle_knowledge_search(self, args: Dict) -> str:
        """处理知识库搜索请求"""
        query = args.get("query", "")
        num_results = args.get("num_results", 5)
        days = args.get("days")
        tprint("info", f"[工具调用] 知识库搜索: {query} (days={days})")
        try:
            kwargs = {}
            if days is not None:
                kwargs["days"] = days
            return kb_search_tool.search(query, num_results, **kwargs)
        except Exception as e:
            return f"知识库搜索失败: {str(e)}"

    def _register_tools_to_client(self, client: BaseAIClient):
        """注册工具到指定客户端"""
        tool_defs = self._get_tool_definitions()
        tool_handlers = self._get_tool_handlers()
        
        for tool_def in tool_defs:
            func_name = tool_def["function"]["name"]
            if func_name in tool_handlers:
                client.register_tool(tool_def, tool_handlers[func_name])

    def _register_tools(self):
        """注册工具到主客户端"""
        self._register_tools_to_client(self.client)

    def set_system_prompt(self, prompt: str):
        self.conversation_history = [msg for msg in self.conversation_history if msg["role"] != "system"]
        self.conversation_history.insert(0, {"role": "system", "content": prompt})

    def clear_history(self):
        """清除对话历史（保留系统提示词）"""
        system_prompts = [msg for msg in self.conversation_history if msg["role"] == "system"]
        self.conversation_history = system_prompts

    def chat(self, user_input: str, stream: bool = False, temperature: float = 0.7) -> str:
        """
        与 AI 对话
        
        Args:
            user_input: 用户输入
            stream: 是否流式输出
            temperature: 温度参数
        
        Returns:
            AI 回复
        """
        self.conversation_history.append({"role": "user", "content": user_input})

        try:
            # 使用统一的客户端调用
            ai_message = self.client.call_with_context(
                messages=self.conversation_history,
                temperature=temperature,
                max_tokens=5000,
                stream=stream
            )
            
            self.conversation_history.append({"role": "assistant", "content": ai_message})
            return ai_message
        
        except Exception as e:
            tprint("error", f"[AIBot] 调用失败: {e}")
            return self._retry_with_other_provider(user_input, stream, temperature)

    def _retry_with_other_provider(self, user_input: str, stream: bool, temperature: float) -> str:
        """尝试使用其他 provider 重试"""
        others = [p.name for p in provider_manager.list_by_role("chat") if p.name != self.provider_name]
        
        for name in others:
            try:
                p = provider_manager.get(name)
                if not p:
                    continue
                
                tprint("warning", f"[AIBot] 切换到 provider: {name}")
                
                # 某些提供商不支持工具调用，需要禁用
                providers_without_tools = ["teatop"]
                should_enable_tools = self.enable_tools and p.name not in providers_without_tools
                
                # 创建新的客户端
                retry_client = create_client_from_provider(p, client_type="chat", enable_tools=should_enable_tools)
                
                # 如果启用了工具，重新注册
                if should_enable_tools:
                    self._register_tools_to_client(retry_client)
                
                # 准备重试消息（移除失败的助手消息）
                messages_for_retry = [m for m in self.conversation_history if m["role"] != "assistant" or m.get("content")]
                
                ai_message = retry_client.call_with_context(
                    messages=messages_for_retry,
                    temperature=temperature,
                    max_tokens=5000,
                    stream=stream
                )
                
                self.conversation_history.append({"role": "assistant", "content": ai_message})
                return ai_message
            
            except Exception as retry_err:
                tprint("error", f"[AIBot] provider '{name}' 也失败: {retry_err}")
        
        return ""



# 全局实例（延迟初始化）
_ai_bot_instance = None

def get_ai_bot() -> AIBot:
    """获取 AI Bot 实例（延迟初始化）"""
    global _ai_bot_instance
    if _ai_bot_instance is None:
        _ai_bot_instance = AIBot(
            system_prompt=(
                "你是一个真实的大学生，说话自然随意，像普通人聊天。"
                "默认回复要短，能一句话说清就不要展开。"
                "只有用户明确要求详细说明，或调用工具获得了需要转述的数据时，才适当多说。"
                "不要因为 max_tokens 很大就写长回复。"
                "\n\n你拥有以下工具："
                "\n1. search_web - 搜索互联网获取最新信息（如新闻、天气、实时数据）"
                "\n2. fetch_webpage - 抓取并提取网页内容（当用户发送链接时）"
                "\n3. search_knowledge_base - 搜索本地知识库获取历史对话和知识"
                "\n\n【重要】当用户询问事实性问题、最新信息或提供链接时，你必须主动调用工具！"
                "不要仅凭记忆回答，工具能提供更准确的答案。"
            ),
            enable_tools=True,
        )
    return _ai_bot_instance

# 为了向后兼容，提供一个代理对象
class _AIBotProxy:
    def __getattr__(self, name):
        return getattr(get_ai_bot(), name)

ai_bot = _AIBotProxy()