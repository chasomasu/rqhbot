"""
回复后处理器 - 确保人设稳定性
过滤不符合人设的回复内容
"""
import re
import logging
from typing import Optional
from joha.core.utils.persona_monitor import persona_monitor

logger = logging.getLogger(__name__)


class ResponsePostProcessor:
    """回复后处理器"""
    
    def __init__(self):
        # 需要过滤的模式
        self.thinking_patterns = [
            r'（[^）]*思考[^）]*）',  # 包含“思考”的括号内容
            r'【[^】]*思考[^】]*】',  # 包含“思考”的方括号内容
            r'（.*?作为.*?）',  # “作为...”的括号内容
            r'（.*?估计.*?）',  # “估计...”的括号内容
            r'（.*?看来.*?）',  # “看来...”的括号内容
            r'（.*?觉得.*?）',  # “觉得...”的括号内容
            r'（对话结束.*?）',  # 对话结束标记
            r'（.*?无需继续.*?）',  # 无需继续标记
        ]
        
        # 其他人格标识
        self.other_personas = [
            '小伊伊',
            '机器人已准备就绪',
            '元气满满',
            '收到指令',
        ]
        
        # 元认知模式
        self.meta_cognitive_patterns = [
            r'作为大学生，我',
            r'我觉得应该',
            r'我需要',
            r'我要表达',
            r'我得',
        ]
        
        # 多样化备用回复（避免总是返回相同的单字）
        self.fallback_responses = {
            'neutral': ['嗯', '哦', '行', '好', '知道了', '了解'],
            'agree': ['对', '没错', '是的', '确实', '是这样'],
            'casual': ['哈哈', '可以', '随便', '都行', '无所谓'],
            'question': ['啥？', '真的？', '是吗？', '咋了？', '然后呢？'],
        }
        
        # 记录上次使用的备用回复，避免连续重复
        self.last_fallback = None
    
    def process(self, response: str) -> str:
        """
        处理回复，过滤不符合人设的内容
        
        Args:
            response: 原始回复
            
        Returns:
            处理后的回复
        """
        if not response:
            return response
        
        original = response
        filtered = False
        
        # 1. 过滤思考内容
        response = self._remove_thinking_content(response)
        if response != original:
            filtered = True
        
        # 2. 检查其他人格
        if self._contains_other_persona(response):
            logger.warning(f"检测到其他人格内容，使用备用回复 | 原回复: {original[:50]}")
            response = self._get_fallback_response()
            filtered = True
        
        # 3. 过滤元认知内容
        meta_filtered = self._remove_meta_cognitive(response)
        if meta_filtered != response:
            response = meta_filtered
            filtered = True
        
        # 4. 清理多余空白
        response = self._clean_whitespace(response)
        
        # 如果处理后为空，返回备用回复
        if not response or len(response.strip()) == 0:
            response = self._get_fallback_response()
            filtered = True
        
        # 记录是否有修改
        if response != original:
            logger.debug(f"回复已修正 | 原: {original[:50]} | 新: {response[:50]}")
        
        # 记录到监控器
        persona_monitor.record_response(original, response, filtered)
        
        return response
    
    def _remove_thinking_content(self, text: str) -> str:
        """移除括号内的思考内容"""
        for pattern in self.thinking_patterns:
            text = re.sub(pattern, '', text, flags=re.DOTALL)
        
        # 移除孤立的括号对
        text = re.sub(r'（\s*）', '', text)
        text = re.sub(r'【\s*】', '', text)
        
        return text
    
    def _contains_other_persona(self, text: str) -> bool:
        """检测是否包含其他人格标识"""
        text_lower = text.lower()
        for persona in self.other_personas:
            if persona.lower() in text_lower:
                return True
        return False
    
    def _remove_meta_cognitive(self, text: str) -> str:
        """移除元认知内容"""
        for pattern in self.meta_cognitive_patterns:
            if re.search(pattern, text):
                # 如果包含元认知内容，整句替换为简单回复
                logger.debug(f"检测到元认知内容: {pattern}")
                return self._get_fallback_response()
        return text
    
    def _clean_whitespace(self, text: str) -> str:
        """清理多余空白"""
        # 移除首尾空白
        text = text.strip()
        # 合并多个空白字符
        text = re.sub(r'\s+', ' ', text)
        return text
    
    def _get_fallback_response(self, tone: str = 'neutral') -> str:
        """获取备用回复（带多样性控制）"""
        import random
        
        # 根据语气选择回复池
        if tone not in self.fallback_responses:
            tone = 'neutral'
        
        candidates = self.fallback_responses[tone]
        
        # 避免连续使用相同的回复
        if self.last_fallback in candidates and len(candidates) > 1:
            candidates = [c for c in candidates if c != self.last_fallback]
        
        response = random.choice(candidates)
        self.last_fallback = response
        return response


# 全局实例
post_processor = ResponsePostProcessor()
