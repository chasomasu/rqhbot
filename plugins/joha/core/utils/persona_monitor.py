"""
人设稳定性监控器
实时监控回复是否符合人设参数
"""
import re
import logging
from typing import Dict, List, Tuple
from collections import deque
from datetime import datetime

logger = logging.getLogger(__name__)


class PersonaStabilityMonitor:
    """人设稳定性监控器"""
    
    def __init__(self, window_size: int = 50):
        self.window_size = window_size
        # 最近的回复历史
        self.recent_responses: deque = deque(maxlen=window_size)
        # 统计信息
        self.stats = {
            'total_responses': 0,
            'filtered_count': 0,
            'avg_length': 0,
            'single_char_ratio': 0,
            'emoji_count': 0,
        }
    
    def record_response(self, original: str, processed: str, filtered: bool = False):
        """记录一次回复"""
        self.stats['total_responses'] += 1
        if filtered:
            self.stats['filtered_count'] += 1
        
        # 记录回复信息
        response_info = {
            'timestamp': datetime.now(),
            'original': original,
            'processed': processed,
            'length': len(processed),
            'is_single_char': len(processed.strip()) <= 2,
            'has_emoji': bool(re.search(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF]', processed)),
            'filtered': filtered,
        }
        self.recent_responses.append(response_info)
        
        # 更新统计
        self._update_stats()
    
    def _update_stats(self):
        """更新统计数据"""
        if not self.recent_responses:
            return
        
        # 平均长度
        total_length = sum(r['length'] for r in self.recent_responses)
        self.stats['avg_length'] = total_length / len(self.recent_responses)
        
        # 单字回复比例
        single_char_count = sum(1 for r in self.recent_responses if r['is_single_char'])
        self.stats['single_char_ratio'] = single_char_count / len(self.recent_responses)
        
        # 表情符号计数
        self.stats['emoji_count'] = sum(1 for r in self.recent_responses if r['has_emoji'])
    
    def get_stability_report(self) -> Dict:
        """获取稳定性报告"""
        self._update_stats()
        
        report = {
            'total_responses': self.stats['total_responses'],
            'recent_window': len(self.recent_responses),
            'filtered_percentage': (
                self.stats['filtered_count'] / max(self.stats['total_responses'], 1) * 100
            ),
            'avg_response_length': round(self.stats['avg_length'], 2),
            'single_char_ratio': round(self.stats['single_char_ratio'] * 100, 2),
            'emoji_usage': self.stats['emoji_count'],
            'stability_score': self._calculate_stability_score(),
        }
        
        return report
    
    def _calculate_stability_score(self) -> float:
        """计算稳定性评分 (0-10)"""
        if not self.recent_responses:
            return 10.0
        
        score = 10.0
        
        # 1. 过滤率惩罚（过高说明AI经常输出不合规内容）
        filter_rate = self.stats['filtered_count'] / max(len(self.recent_responses), 1)
        if filter_rate > 0.1:  # 超过10%被过滤
            score -= filter_rate * 20  # 最多扣2分
        
        # 2. 单字回复比例检查（过高显得单调）
        single_ratio = self.stats['single_char_ratio']
        if single_ratio > 0.7:  # 超过70%是单字
            score -= (single_ratio - 0.7) * 5  # 最多扣1.5分
        
        # 3. 平均长度检查（应该符合人设的简短要求）
        avg_len = self.stats['avg_length']
        if avg_len < 2:  # 太短
            score -= 1
        elif avg_len > 50:  # 太长，不符合"大学生"设定
            score -= 2
        
        return max(0, min(10, score))
    
    def format_report(self) -> str:
        """格式化输出报告"""
        report = self.get_stability_report()
        
        lines = [
            "📊 Joha人设稳定性报告",
            "─" * 40,
            f"总回复数: {report['total_responses']}",
            f"监控窗口: 最近{report['recent_window']}条",
            f"过滤率: {report['filtered_percentage']:.1f}%",
            f"平均长度: {report['avg_response_length']}字",
            f"单字比例: {report['single_char_ratio']}%",
            f"表情使用: {report['emoji_usage']}次",
            "",
            f"⭐ 稳定性评分: {report['stability_score']:.1f}/10",
        ]
        
        # 评分解读
        score = report['stability_score']
        if score >= 8:
            lines.append("✅ 人设稳定，表现良好")
        elif score >= 6:
            lines.append("⚠️ 人设基本稳定，有改进空间")
        elif score >= 4:
            lines.append("❌ 人设不稳定，需要调整")
        else:
            lines.append("🚨 人设严重偏离，请立即检查")
        
        return "\n".join(lines)
    
    def check_and_alert(self) -> List[str]:
        """检查并发出警告"""
        alerts = []
        
        if not self.recent_responses:
            return alerts
        
        # 检查过滤率
        filter_rate = self.stats['filtered_count'] / max(len(self.recent_responses), 1)
        if filter_rate > 0.15:
            alerts.append(f"⚠️ 过滤率过高 ({filter_rate*100:.1f}%)，AI可能频繁输出不合规内容")
        
        # 检查单字比例
        single_ratio = self.stats['single_char_ratio']
        if single_ratio > 0.8:
            alerts.append(f"⚠️ 单字回复过多 ({single_ratio*100:.1f}%)，建议增加回复多样性")
        
        # 检查平均长度
        avg_len = self.stats['avg_length']
        if avg_len > 60:
            alerts.append(f"⚠️ 平均回复过长 ({avg_len:.1f}字)，不符合简短人设")
        
        return alerts


# 全局实例
persona_monitor = PersonaStabilityMonitor()
