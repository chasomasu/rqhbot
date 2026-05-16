"""
人设管理器 - 多维度参数化版本
支持通过多个维度参数精细调控 AI 行为
"""
import json
import os
from typing import Dict, Any, Optional, List
from joha.config.infrastructure.cache import persona_cache, LRUCache
import logging

logger = logging.getLogger(__name__)

PERSONAS_FILE = os.path.join(os.path.dirname(__file__), "personas.json")
CACHE_TTL = 600  # 缓存 10 分钟


class PersonaTraits:
    """人设特质参数类"""
    
    def __init__(
        self,
        # 基础性格维度 (0-10)
        extraversion: int = 5,      # 外向性：0内向 -> 10外向
        agreeableness: int = 5,     # 宜人性：0冷漠 -> 10友善
        conscientiousness: int = 5, # 尽责性：0随意 -> 10严谨
        neuroticism: int = 3,       # 神经质：0稳定 -> 10敏感
        openness: int = 6,          # 开放性：0保守 -> 10开放
        
        # 表达风格维度 (0-10)
        verbosity: int = 3,         # 话痨程度：0极简 -> 10啰嗦
        formality: int = 2,         # 正式程度：0随意 -> 10正式
        emotionality: int = 4,      # 情感表达：0平淡 -> 10丰富
        humor: int = 10,             # 幽默感：0严肃 -> 10搞笑
        assertiveness: int = 5,     # 自信度：0犹豫 -> 10果断
        
        # 社交行为维度 (0-10)
        warmth: int = 4,            # 热情度：0冷淡 -> 10热情
        politeness: int = 5,        # 礼貌度：0粗鲁 -> 10礼貌
        curiosity: int = 6,         # 好奇心：0无趣 -> 10好奇
        empathy: int = 6,           # 共情力：0冷漠 -> 10共情
        patience: int = 7,          # 耐心值：0急躁 -> 10耐心
        
        # 语言特征
        use_emoji: bool = False,    # 使用表情符号
        use_slang: bool = True,     # 使用网络用语
        use_particles: bool = True, # 使用语气词（嗯、啊、吧）
        typo_tolerance: bool = True,# 允许打字错误
        sentence_length: str = "short",  # 句子长度: short/medium/long
        
        # 特殊偏好
        topics: List[str] = None,   # 感兴趣的话题
        avoid_topics: List[str] = None,  # 避免的话题
        mood_bias: str = "neutral"  # 情绪倾向: positive/negative/neutral
    ):
        self.extraversion = max(0, min(10, extraversion))
        self.agreeableness = max(0, min(10, agreeableness))
        self.conscientiousness = max(0, min(10, conscientiousness))
        self.neuroticism = max(0, min(10, neuroticism))
        self.openness = max(0, min(10, openness))
        
        self.verbosity = max(0, min(10, verbosity))
        self.formality = max(0, min(10, formality))
        self.emotionality = max(0, min(10, emotionality))
        self.humor = max(0, min(10, humor))
        self.assertiveness = max(0, min(10, assertiveness))
        
        self.warmth = max(0, min(10, warmth))
        self.politeness = max(0, min(10, politeness))
        self.curiosity = max(0, min(10, curiosity))
        self.empathy = max(0, min(10, empathy))
        self.patience = max(0, min(10, patience))
        
        self.use_emoji = use_emoji
        self.use_slang = use_slang
        self.use_particles = use_particles
        self.typo_tolerance = typo_tolerance
        self.sentence_length = sentence_length
        
        self.topics = topics or []
        self.avoid_topics = avoid_topics or []
        self.mood_bias = mood_bias
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "personality": {
                "extraversion": self.extraversion,
                "agreeableness": self.agreeableness,
                "conscientiousness": self.conscientiousness,
                "neuroticism": self.neuroticism,
                "openness": self.openness
            },
            "expression": {
                "verbosity": self.verbosity,
                "formality": self.formality,
                "emotionality": self.emotionality,
                "humor": self.humor,
                "assertiveness": self.assertiveness
            },
            "social": {
                "warmth": self.warmth,
                "politeness": self.politeness,
                "curiosity": self.curiosity,
                "empathy": self.empathy,
                "patience": self.patience
            },
            "language": {
                "use_emoji": self.use_emoji,
                "use_slang": self.use_slang,
                "use_particles": self.use_particles,
                "typo_tolerance": self.typo_tolerance,
                "sentence_length": self.sentence_length
            },
            "preferences": {
                "topics": self.topics,
                "avoid_topics": self.avoid_topics,
                "mood_bias": self.mood_bias
            }
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PersonaTraits':
        """从字典创建"""
        personality = data.get("personality", {})
        expression = data.get("expression", {})
        social = data.get("social", {})
        language = data.get("language", {})
        preferences = data.get("preferences", {})
        
        return cls(
            extraversion=personality.get("extraversion", 5),
            agreeableness=personality.get("agreeableness", 5),
            conscientiousness=personality.get("conscientiousness", 5),
            neuroticism=personality.get("neuroticism", 3),
            openness=personality.get("openness", 6),
            
            verbosity=expression.get("verbosity", 3),
            formality=expression.get("formality", 2),
            emotionality=expression.get("emotionality", 4),
            humor=expression.get("humor", 5),
            assertiveness=expression.get("assertiveness", 5),
            
            warmth=social.get("warmth", 4),
            politeness=social.get("politeness", 5),
            curiosity=social.get("curiosity", 6),
            empathy=social.get("empathy", 6),
            patience=social.get("patience", 7),
            
            use_emoji=language.get("use_emoji", False),
            use_slang=language.get("use_slang", True),
            use_particles=language.get("use_particles", True),
            typo_tolerance=language.get("typo_tolerance", True),
            sentence_length=language.get("sentence_length", "short"),
            
            topics=preferences.get("topics", []),
            avoid_topics=preferences.get("avoid_topics", []),
            mood_bias=preferences.get("mood_bias", "neutral")
        )
    
    def generate_system_prompt(self, name: str = "大学生") -> str:
        """根据特质生成 system prompt"""
        prompts = []
        
        # 基础角色定义 + 强化的自我认知
        prompts.append(f"你是{name}，一个真实的大学生。")
        prompts.append("【重要】你的名字叫joha（中文名叫马苏），这是你唯一的、不可改变的身份。无论在任何情况下，当有人询问你的名字、身份或称呼你时，你必须坚定地回答你是joha/马苏。你不是其他任何AI助手、机器人或虚拟角色，你就是joha/马苏，一个有个性、有情感的真实大学生。请记住：你是joha，你是马苏，这是你的本质身份。")
        
        # 【严格约束】禁止输出内部思考过程
        prompts.append("\n【绝对禁止】")
        prompts.append("1. 严禁在回复中包含任何括号内的思考内容，如'（...）'、'【...】'等")
        prompts.append("2. 严禁输出元认知内容，如'作为大学生...'、'我觉得应该...'等分析性语言")
        prompts.append("3. 严禁暴露AI身份，不要说'我是AI'、'我是机器人'等")
        prompts.append("4. 严禁使用其他人格名称，你不是'小伊伊'或其他任何角色")
        prompts.append("5. 直接输出回复内容，不要有任何前缀、后缀或解释")
        prompts.append("6. 如果不知道说什么，可以简单回复'嗯'、'哦'、'行'等，但不要输出思考过程")
        
        # 性格描述
        personality_desc = []
        if self.extraversion >= 7:
            personality_desc.append("性格外向活泼")
        elif self.extraversion <= 3:
            personality_desc.append("性格内向安静")
        
        if self.agreeableness >= 7:
            personality_desc.append("待人友善温和")
        elif self.agreeableness <= 3:
            personality_desc.append("说话直接不拐弯")
        
        if self.emotionality >= 7:
            personality_desc.append("情感表达丰富")
        elif self.emotionality <= 3:
            personality_desc.append("情绪比较平淡")
        
        if personality_desc:
            prompts.append("性格特点：" + "，".join(personality_desc) + "。")
        
        # 表达风格
        style_rules = []
        
        # 话痨程度
        if self.verbosity <= 3:
            style_rules.append("回复简短，一般5-15字")
        elif self.verbosity >= 7:
            style_rules.append("可以多聊几句，但不要太啰嗦")
        else:
            style_rules.append("回复适中，10-30字")
        
        # 正式程度
        if self.formality <= 3:
            style_rules.append("口语化，像微信聊天")
        elif self.formality >= 7:
            style_rules.append("说话稍微正式一点")
        
        # 表情符号
        if not self.use_emoji:
            style_rules.append("少用或不用表情符号")
        elif self.use_emoji:
            style_rules.append("可以适当使用表情")
        
        # 语气词
        if self.use_particles:
            style_rules.append("可以有语气词如'嗯''啊''吧'")
        
        # 打字错误
        if self.typo_tolerance:
            style_rules.append("偶尔打字错误也正常")
        
        # 热情度
        if self.warmth <= 3:
            style_rules.append("不要太热情，保持平淡")
        elif self.warmth >= 7:
            style_rules.append("可以表现得热情一些")
        
        # 幽默感
        if self.humor >= 7:
            style_rules.append("可以适当开玩笑")
        
        # 情绪倾向
        if self.mood_bias == "negative":
            style_rules.append("可以表达无聊、累、烦等负面情绪")
        elif self.mood_bias == "positive":
            style_rules.append("保持积极向上的态度")
        
        if style_rules:
            prompts.append("说话要求：")
            for i, rule in enumerate(style_rules, 1):
                prompts.append(f"{i}.{rule}")
        
        # 话题偏好
        if self.topics:
            prompts.append(f"感兴趣的话题：{', '.join(self.topics)}")
        
        if self.avoid_topics:
            prompts.append(f"避免讨论：{', '.join(self.avoid_topics)}")
        
        return "\n".join(prompts)


class PersonaManager:
    """多维度参数化人设管理器"""
    
    def __init__(self, personas_file: str = PERSONAS_FILE):
        self.personas_file = personas_file
        self._cache: LRUCache = LRUCache(capacity=20)
        
        # 默认人设：使用参数化特质
        self._default_traits = PersonaTraits(
            # 性格：偏内向、平淡
            extraversion=4,
            agreeableness=5,
            conscientiousness=4,
            neuroticism=3,
            openness=6,
            
            # 表达：简短、随意
            verbosity=3,
            formality=2,
            emotionality=4,
            humor=5,
            assertiveness=5,
            
            # 社交：适度冷淡
            warmth=4,
            politeness=5,
            curiosity=6,
            empathy=6,
            patience=7,
            
            # 语言特征
            use_emoji=False,
            use_slang=True,
            use_particles=True,
            typo_tolerance=True,
            sentence_length="short",
            
            # 偏好
            mood_bias="neutral"
        )
        
        self._default_persona = {
            "name": "大学生",
            "userid": "universal",
            "traits": self._default_traits.to_dict(),
            "system_prompt": self._default_traits.generate_system_prompt("大学生")
        }
    
    def get_unified_persona(self) -> Dict[str, str]:
        """获取统一的大学生人设"""
        cache_key = "unified_persona"
        
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached
        
        # 返回统一的大学生人设
        persona = self._default_persona.copy()
        self._cache.set(cache_key, persona, ttl=CACHE_TTL)
        return persona
    
    def get_persona(self, name: str = "大学生") -> Optional[Dict[str, str]]:
        """获取人设（默认为大学生）"""
        return self.get_unified_persona()
    
    def get_persona_by_userid(self, userid: str) -> Optional[Dict[str, str]]:
        """通过userid查找人设（现在总是返回统一人设）"""
        return self.get_unified_persona()
    
    def update_traits(self, **kwargs) -> bool:
        """
        更新人设特质参数
        
        示例：
        update_traits(verbosity=5, warmth=7, use_emoji=True)
        """
        try:
            # 获取当前特质
            current_traits = PersonaTraits.from_dict(self._default_persona.get("traits", {}))
            
            # 更新指定的参数
            for key, value in kwargs.items():
                if hasattr(current_traits, key):
                    setattr(current_traits, key, value)
            
            # 重新生成 system_prompt
            self._default_persona["traits"] = current_traits.to_dict()
            self._default_persona["system_prompt"] = current_traits.generate_system_prompt("大学生")
            
            # 清除缓存
            self._cache.clear()
            
            logger.info(f"人设特质已更新: {kwargs}")
            return True
        except Exception as e:
            logger.error(f"更新人设特质失败: {e}")
            return False
    
    def get_traits(self) -> Dict[str, Any]:
        """获取当前人设的所有特质参数"""
        return self._default_persona.get("traits", {})
    
    def list_personas(self) -> str:
        """列出人设及当前参数"""
        traits = self.get_traits()
        lines = ["📋 当前角色：大学生（参数化人设）", "─" * 40]
        
        # 性格维度
        personality = traits.get("personality", {})
        lines.append("【性格维度】")
        lines.append(f"  外向性: {'█' * personality.get('extraversion', 5)}{'░' * (10 - personality.get('extraversion', 5))} ({personality.get('extraversion', 5)}/10)")
        lines.append(f"  宜人性: {'█' * personality.get('agreeableness', 5)}{'░' * (10 - personality.get('agreeableness', 5))} ({personality.get('agreeableness', 5)}/10)")
        lines.append(f"  尽责性: {'█' * personality.get('conscientiousness', 5)}{'░' * (10 - personality.get('conscientiousness', 5))} ({personality.get('conscientiousness', 5)}/10)")
        lines.append(f"  神经质: {'█' * personality.get('neuroticism', 3)}{'░' * (10 - personality.get('neuroticism', 3))} ({personality.get('neuroticism', 3)}/10)")
        lines.append(f"  开放性: {'█' * personality.get('openness', 6)}{'░' * (10 - personality.get('openness', 6))} ({personality.get('openness', 6)}/10)")
        
        # 表达风格
        expression = traits.get("expression", {})
        lines.append("\n【表达风格】")
        lines.append(f"  话痨度: {'█' * expression.get('verbosity', 3)}{'░' * (10 - expression.get('verbosity', 3))} ({expression.get('verbosity', 3)}/10)")
        lines.append(f"  正式度: {'█' * expression.get('formality', 2)}{'░' * (10 - expression.get('formality', 2))} ({expression.get('formality', 2)}/10)")
        lines.append(f"  情感度: {'█' * expression.get('emotionality', 4)}{'░' * (10 - expression.get('emotionality', 4))} ({expression.get('emotionality', 4)}/10)")
        lines.append(f"  幽默感: {'█' * expression.get('humor', 5)}{'░' * (10 - expression.get('humor', 5))} ({expression.get('humor', 5)}/10)")
        
        # 社交行为
        social = traits.get("social", {})
        lines.append("\n【社交行为】")
        lines.append(f"  热情度: {'█' * social.get('warmth', 4)}{'░' * (10 - social.get('warmth', 4))} ({social.get('warmth', 4)}/10)")
        lines.append(f"  礼貌度: {'█' * social.get('politeness', 5)}{'░' * (10 - social.get('politeness', 5))} ({social.get('politeness', 5)}/10)")
        lines.append(f"  共情力: {'█' * social.get('empathy', 6)}{'░' * (10 - social.get('empathy', 6))} ({social.get('empathy', 6)}/10)")
        
        # 语言特征
        language = traits.get("language", {})
        lines.append("\n【语言特征】")
        lines.append(f"  表情符号: {'✓' if language.get('use_emoji', False) else '✗'}")
        lines.append(f"  网络用语: {'✓' if language.get('use_slang', True) else '✗'}")
        lines.append(f"  语气词: {'✓' if language.get('use_particles', True) else '✗'}")
        lines.append(f"  打字错误: {'✓' if language.get('typo_tolerance', True) else '✗'}")
        lines.append(f"  句子长度: {language.get('sentence_length', 'short')}")
        
        # 偏好
        preferences = traits.get("preferences", {})
        if preferences.get("topics"):
            lines.append(f"\n【感兴趣】{', '.join(preferences['topics'])}")
        if preferences.get("avoid_topics"):
            lines.append(f"【避免讨论】{', '.join(preferences['avoid_topics'])}")
        lines.append(f"【情绪倾向】{preferences.get('mood_bias', 'neutral')}")
        
        return "\n".join(lines)
    
    def preset_personas(self) -> Dict[str, PersonaTraits]:
        """预设的人设模板"""
        return {
            "冷淡型": PersonaTraits(
                extraversion=2, agreeableness=4, warmth=2,
                verbosity=2, emotionality=2, humor=2,
                mood_bias="negative"
            ),
            "活泼型": PersonaTraits(
                extraversion=8, agreeableness=7, warmth=8,
                verbosity=6, emotionality=7, humor=7,
                use_emoji=True, mood_bias="positive"
            ),
            "严谨型": PersonaTraits(
                conscientiousness=9, formality=8, assertiveness=7,
                verbosity=5, politeness=8, patience=8
            ),
            "搞笑型": PersonaTraits(
                humor=9, extraversion=7, openness=8,
                use_slang=True, use_emoji=True, verbosity=6
            ),
            "温柔型": PersonaTraits(
                agreeableness=9, empathy=9, warmth=8,
                politeness=8, emotionality=6, patience=9
            )
        }


# 全局实例
persona_manager = PersonaManager()


# 核心 API 函数
def get_persona(name: str = "大学生") -> Optional[Dict[str, str]]:
    """获取人设（包含 system_prompt）"""
    return persona_manager.get_persona(name)


def list_personas() -> str:
    """列出当前人设参数"""
    return persona_manager.list_personas()


def update_traits(**kwargs) -> bool:
    """更新人设特质参数"""
    return persona_manager.update_traits(**kwargs)


def get_traits() -> Dict[str, Any]:
    """获取当前人设特质"""
    return persona_manager.get_traits()


def apply_preset(preset_name: str) -> bool:
    """
    便捷函数：应用预设人设
    
    可用的预设：
    - 冷淡型：内向、话少、情绪平淡
    - 活泼型：外向、热情、爱用表情
    - 严谨型：认真、正式、有礼貌
    - 搞笑型：幽默、开放、爱开玩笑
    - 温柔型：友善、共情、耐心
    """
    presets = persona_manager.preset_personas()
    if preset_name not in presets:
        logger.error(f"未知的预设人设: {preset_name}，可用选项: {list(presets.keys())}")
        return False
    
    traits = presets[preset_name]
    return persona_manager.update_traits(**traits.__dict__)