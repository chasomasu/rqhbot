"""
通用问题分类器
使用统一的 AI 客户端架构和 ProviderManager
"""
from joha.ai.clients import create_client_from_provider
from joha.ai.providers import provider_manager
from joha.config.infrastructure.logger import tprint


class QuestionClassifier:
    """问题识别器 - 通过 AI 判断问题类型"""

    def __init__(self, provider_name: str = ""):
        if provider_name:
            self.provider = provider_manager.get(provider_name)
        else:
            self.provider = provider_manager.get_default("classifier")

        if not self.provider:
            raise RuntimeError("没有可用的 classifier provider，请检查 config.json 中的 providers 配置")

        # 使用统一的 AI 客户端
        self.client = create_client_from_provider(self.provider, client_type="classifier")
        self.model = self.provider.model
        tprint("info", f"[QuestionClassifier] 使用 provider: {self.provider.name} (模型: {self.model})")

    def classify_intent(self, text: str) -> dict:
        """
        统一意图识别
        
        Args:
            text: 用户输入文本
            
        Returns:
            dict: {
                'is_programming': bool,  # 是否为编程问题
                'intent_type': str,      # 意图类型: programming/chat/question/other
                'confidence': float      # 置信度 (0-1)
            }
        """
        prompt = f"""请分析以下用户输入的意图，返回 JSON 格式结果。

用户输入：{text}

请判断：
1. 是否为编程/代码/软件开发相关问题
2. 意图类型：programming(编程技术)、question(普通问题)、chat(闲聊)、other(其他)
3. 置信度：0.0-1.0

只返回 JSON，格式如下：
{{"is_programming": true/false, "intent_type": "programming/question/chat/other", "confidence": 0.9}}
"""

        messages = [{"role": "user", "content": prompt}]
        
        try:
            import json
            response = self.client.call_with_context(messages, temperature=0.3, max_tokens=100)
            
            # 尝试解析 JSON
            response = response.strip()
            # 移除可能的 markdown 代码块标记
            if response.startswith('```'):
                response = response.split('\n', 1)[-1].rsplit('\n', 1)[0]
            if response.startswith('json'):
                response = response[4:].strip()
            
            result = json.loads(response)
            return {
                'is_programming': result.get('is_programming', False),
                'intent_type': result.get('intent_type', 'other'),
                'confidence': result.get('confidence', 0.5)
            }
        except Exception as e:
            tprint("warning", f"[QuestionClassifier] 意图识别失败: {e}")
            # 降级：简单判断
            is_prog = self._simple_programming_check(text)
            return {
                'is_programming': is_prog,
                'intent_type': 'programming' if is_prog else 'chat',
                'confidence': 0.3
            }
    
    def _simple_programming_check(self, text: str) -> bool:
        """简单的编程问题判断（降级方案）"""
        programming_keywords = [
            '代码', '编程', 'python', 'java', 'javascript', 'c++', 'html', 'css',
            '函数', '变量', '类', '对象', '算法', '数据结构', 'bug', '错误',
            'debug', '编译', '运行', 'api', '数据库', 'sql', '框架'
        ]
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in programming_keywords)

    def is_programming_question(self, text: str) -> bool:
        """判断是否为编程问题（向后兼容）"""
        result = self.classify_intent(text)
        return result['is_programming']


# 全局实例（延迟初始化）
_classifier_instance = None

def get_classifier() -> QuestionClassifier:
    """获取分类器实例（延迟初始化）"""
    global _classifier_instance
    if _classifier_instance is None:
        _classifier_instance = QuestionClassifier()
    return _classifier_instance

# 为了向后兼容，提供一个代理对象
class _ClassifierProxy:
    def __getattr__(self, name):
        return getattr(get_classifier(), name)

classifier = _ClassifierProxy()
