"""
AI 意图识别器
用于更精确地识别用户消息的意图类型
支持多种意图分类：闲聊、提问、命令、情感、编程问题等
支持独立的识别器 API 配置替换
"""
from typing import Dict, Optional
from joha.ai.clients import create_client_from_provider
from joha.ai.providers import provider_manager, Provider
from joha.config.infrastructure.logger import tprint


class IntentClassifier:
    """AI 意图识别器"""

    def __init__(self, provider_name: str = ""):
        self.provider = None
        self.use_custom_config = False
        
        # 从配置中读取意图识别设置
        from joha.config.managers.config_manager import config as config_manager
        intent_config = config_manager.get("intent_recognition", {})
        
        # 检查是否使用自定义配置（优先级最高）
        custom_config = intent_config.get("custom_config", {})
        if custom_config.get("api_key") and custom_config.get("base_url") and custom_config.get("model"):
            # 使用自定义配置创建临时 provider
            self.provider = Provider(
                name="custom-intent",
                role="intent",
                api_key=custom_config["api_key"],
                base_url=custom_config["base_url"],
                model=custom_config["model"]
            )
            self.use_custom_config = True
            tprint("info", f"[IntentClassifier] 使用自定义配置: {custom_config['model']}")
        else:
            # 如果没有自定义配置，尝试使用 provider_name
            if provider_name:
                self.provider = provider_manager.get(provider_name)
            else:
                # 尝试获取配置的 provider_name
                configured_provider = intent_config.get("provider_name", "")
                
                # 如果配置了 provider_name，优先从 _available_configs 中查找
                if configured_provider:
                    available_configs = config_manager.get("intent_recognition._available_configs", {})
                    conf = available_configs.get(configured_provider)
                    if conf:
                        self.provider = Provider(
                            name=configured_provider,
                            role="intent",
                            api_key=conf.get("api_key", ""),
                            base_url=conf.get("base_url", ""),
                            model=conf.get("model", "")
                        )
                    else:
                        # 如果 _available_configs 中没有，再从 provider_manager 找
                        self.provider = provider_manager.get(configured_provider)
                
                # 如果没有配置或找不到，尝试获取默认的 classifier
                if not self.provider:
                    self.provider = provider_manager.get_default("classifier")
        
        if not self.provider:
            raise RuntimeError("没有可用的 intent/classifier provider，请检查 config.json 中的配置")

        # 使用统一的 AI 客户端
        self.client = create_client_from_provider(self.provider, client_type="classifier")
        self.model = self.provider.model
        tprint("info", f"[IntentClassifier] 使用 provider: {self.provider.name} (模型: {self.model})")

    def classify_intent(self, text: str) -> Dict[str, any]:
        """
        AI 驱动的意图识别（支持自动回退）
        """
        prompt = f"""请分析以下用户输入的意图，返回 JSON 格式结果。

用户输入：{text}

请判断主要意图类型：
- chat: 日常闲聊、打招呼、无明确目的的交流
- question: 询问信息、寻求答案的问题
- command: 要求执行特定操作或任务
- emotion: 表达情绪、感受、心情
- spam: 无意义内容、重复字符、广告等
- programming: 编程、代码、技术问题

只返回 JSON，格式如下：
{{"intent": "chat/question/command/emotion/spam/programming", "confidence": 0.9}}
"""
        messages = [{"role": "user", "content": prompt}]
        
        # 1. 尝试使用当前配置的 Provider
        if self.provider:
            try:
                import json
                response = self.client.call_with_context(messages, temperature=0.1, max_tokens=100)
                
                # 清理响应内容
                response = response.strip()
                if response.startswith('```'):
                    lines = response.split('\n')
                    if len(lines) > 2:
                        response = '\n'.join(lines[1:-1])
                    else:
                        response = response.replace('```', '').strip()
                if response.startswith('json'):
                    response = response[4:].strip()
                
                # 尝试解析 JSON
                result = json.loads(response)
                return {
                    'intent': result.get('intent', 'chat'),
                    'confidence': result.get('confidence', 0.5),
                    'details': result.get('details', {})
                }
            except json.JSONDecodeError as e:
                tprint("warning", f"[IntentClassifier] 主模型 {self.provider.name} JSON 解析失败: {e}，正在尝试回退...")
            except Exception as e:
                tprint("warning", f"[IntentClassifier] 主模型 {self.provider.name} 失败: {e}，正在尝试回退...")

        # 2. 回退逻辑：最多尝试 2 个备选 provider
        from joha.ai.providers import provider_manager
        MAX_FALLBACK = 2
        fallback_count = 0
        all_providers = provider_manager.list_all()
        tried_names = {self.provider.name} if self.provider else set()
        for p in all_providers:
            if p.name in tried_names:
                continue
            if fallback_count >= MAX_FALLBACK:
                break

            try:
                tprint("info", f"[IntentClassifier] 尝试回退到: {p.name}")
                retry_client = create_client_from_provider(p, client_type="classifier")
                response = retry_client.call_with_context(messages, temperature=0.1, max_tokens=100)

                import json
                response = response.strip()
                if response.startswith('```'):
                    response = response.replace('```', '').strip()
                if response.startswith('json'):
                    response = response[4:].strip()

                result = json.loads(response)

                self.provider = p
                self.client = retry_client
                tprint("info", f"[IntentClassifier] 回退成功，已切换到: {p.name}")

                return {
                    'intent': result.get('intent', 'chat'),
                    'confidence': result.get('confidence', 0.5),
                    'details': result.get('details', {})
                }
            except json.JSONDecodeError:
                tprint("warning", f"[IntentClassifier] 回退模型 {p.name} JSON 解析失败")
                fallback_count += 1
                continue
            except Exception:
                fallback_count += 1
                continue

        # 3. 全部失败，降级到规则
        tprint("warning", "[IntentClassifier] 所有模型均失败，降级到规则检测")
        return self._fallback_classification(text)
    
    def _fallback_classification(self, text: str) -> Dict[str, any]:
        """降级方案：基于规则的简单分类"""
        import re
        
        text_lower = text.lower().strip()
        if not text_lower:
            return {'intent': 'spam', 'confidence': 0.8, 'details': {}}
        
        # 简单的规则判断
        if re.search(r'[?？]', text):
            return {'intent': 'question', 'confidence': 0.6, 'details': {}}
        elif re.search(r'^\s*[#!/]', text):
            return {'intent': 'command', 'confidence': 0.7, 'details': {}}
        elif any(word in text_lower for word in ['开心', '难过', '生气', '喜欢', '讨厌']):
            return {'intent': 'emotion', 'confidence': 0.5, 'details': {}}
        elif len(set(text)) < len(text) * 0.3 and len(text) > 5:  # 字符重复度高
            return {'intent': 'spam', 'confidence': 0.7, 'details': {}}
        else:
            return {'intent': 'chat', 'confidence': 0.4, 'details': {}}


# 全局实例（延迟初始化）
_intent_classifier_instance = None

def get_intent_classifier() -> IntentClassifier:
    """获取意图识别器实例（延迟初始化）"""
    global _intent_classifier_instance
    if _intent_classifier_instance is None:
        _intent_classifier_instance = IntentClassifier()
    return _intent_classifier_instance

def reload_intent_classifier():
    """重新加载意图识别器（用于配置变更后）"""
    global _intent_classifier_instance
    _intent_classifier_instance = None
    return get_intent_classifier()

# 为了向后兼容，提供一个代理对象
class _IntentClassifierProxy:
    def __getattr__(self, name):
        return getattr(get_intent_classifier(), name)

intent_classifier = _IntentClassifierProxy()
