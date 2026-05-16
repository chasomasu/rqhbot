"""
历史记录清洗工具
- 备份原始文件到指定目录
- 清洗回复中的思考内容、其他人格等异常内容
- 保留清洗前后的对比统计
"""
import os
import json
import shutil
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple


class HistoryCleaner:
    """历史记录清洗器"""
    
    def __init__(self, source_dir: str, backup_dir: str, cleaned_dir: str):
        """
        初始化清洗器
        
        Args:
            source_dir: 原始历史记录目录
            backup_dir: 备份目录（存放原始文件）
            cleaned_dir: 清洗后的文件目录
        """
        self.source_dir = Path(source_dir)
        self.backup_dir = Path(backup_dir)
        self.cleaned_dir = Path(cleaned_dir)
        
        # 确保目录存在
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.cleaned_dir.mkdir(parents=True, exist_ok=True)
        
        # 需要过滤的模式
        self.thinking_patterns = [
            r'（[^）]*思考[^）]*）',
            r'【[^】]*思考[^】]*】',
            r'（.*?作为.*?）',
            r'（.*?估计.*?）',
            r'（.*?看来.*?）',
            r'（.*?觉得.*?）',
            r'（对话结束.*?）',
            r'（.*?无需继续.*?）',
            r'（.*?已读.*?）',
            r'（.*?没回.*?）',
            r'（.*?不回复.*?）',
            r'（.*?准备.*?）',
            r'（.*?睡觉.*?）',
            r'（.*?刷.*?）',
            r'（.*?哈欠.*?）',
            r'（.*?表情.*?）',
            r'（.*?简单.*?）',
            r'（.*?抱怨.*?）',
            r'（.*?翻.*?）',
            # 通用模式：任何包含动词的括号内容
            r'（[^）]{3,}）',  # 3个字符以上的括号内容都移除
        ]
        
        # 其他人格标识
        self.other_personas = [
            '小伊伊',
            '机器人已准备就绪',
            '元气满满',
            '收到指令',
        ]
        
        # 统计信息
        self.stats = {
            'total_files': 0,
            'cleaned_files': 0,
            'total_records': 0,
            'cleaned_records': 0,
            'removed_thinking': 0,
            'removed_persona': 0,
        }
    
    def backup_file(self, filename: str) -> bool:
        """备份单个文件"""
        source = self.source_dir / filename
        backup = self.backup_dir / filename
        
        if not source.exists():
            return False
        
        try:
            shutil.copy2(source, backup)
            return True
        except Exception as e:
            print(f"❌ 备份失败 {filename}: {e}")
            return False
    
    def clean_response(self, response: str) -> Tuple[str, bool]:
        """
        清洗单条回复
        
        Returns:
            (清洗后的回复, 是否被修改)
        """
        if not response or not response.strip():
            return response, False
        
        original = response
        modified = False
        
        # 0. 处理未闭合的括号（以（开头但没有）结尾）
        if response.startswith('（') and '）' not in response:
            response = '嗯'
            return response, True
        
        # 1. 移除思考内容
        for pattern in self.thinking_patterns:
            new_response = re.sub(pattern, '', response, flags=re.DOTALL)
            if new_response != response:
                response = new_response
                modified = True
                self.stats['removed_thinking'] += 1
        
        # 2. 检查其他人格
        for persona in self.other_personas:
            if persona in response:
                # 替换为简单回复
                response = '嗯'
                modified = True
                self.stats['removed_persona'] += 1
                break
        
        # 3. 清理多余空白
        response = response.strip()
        response = re.sub(r'\s+', ' ', response)
        
        # 4. 如果清洗后为空，返回默认值
        if not response:
            response = '嗯'
            modified = True
        
        return response, modified
    
    def clean_history_file(self, filename: str) -> Dict:
        """
        清洗单个历史记录文件
        
        Returns:
            清洗统计信息
        """
        source = self.source_dir / filename
        cleaned = self.cleaned_dir / filename
        
        if not source.exists():
            return {'error': '文件不存在'}
        
        try:
            # 读取原始文件
            with open(source, 'r', encoding='utf-8') as f:
                records = json.load(f)
            
            if not isinstance(records, list):
                return {'error': '文件格式错误'}
            
            file_stats = {
                'total': len(records),
                'cleaned': 0,
                'empty_responses': 0,
            }
            
            cleaned_records = []
            
            for record in records:
                if not isinstance(record, dict):
                    continue
                
                # 复制记录
                cleaned_record = record.copy()
                
                # 清洗response字段
                if 'response' in cleaned_record and cleaned_record['response']:
                    original_response = cleaned_record['response']
                    cleaned_response, was_modified = self.clean_response(original_response)
                    
                    if was_modified:
                        file_stats['cleaned'] += 1
                        self.stats['cleaned_records'] += 1
                    
                    cleaned_record['response'] = cleaned_response
                
                # 统计空回复
                if not cleaned_record.get('response'):
                    file_stats['empty_responses'] += 1
                
                cleaned_records.append(cleaned_record)
            
            # 保存清洗后的文件
            with open(cleaned, 'w', encoding='utf-8') as f:
                json.dump(cleaned_records, f, ensure_ascii=False, indent=2)
            
            self.stats['total_records'] += file_stats['total']
            return file_stats
            
        except Exception as e:
            return {'error': f'处理失败: {str(e)}'}
    
    def clean_all(self) -> Dict:
        """
        清洗所有历史记录文件
        
        Returns:
            总体统计信息
        """
        print("=" * 70)
        print("🧹 Joha历史记录清洗工具")
        print("=" * 70)
        print(f"源目录: {self.source_dir}")
        print(f"备份目录: {self.backup_dir}")
        print(f"清洗目录: {self.cleaned_dir}")
        print()
        
        # 获取所有JSON文件
        json_files = sorted([f.name for f in self.source_dir.glob('*.json')])
        
        if not json_files:
            print("⚠️ 未找到任何JSON文件")
            return self.stats
        
        self.stats['total_files'] = len(json_files)
        print(f"📁 找到 {len(json_files)} 个历史记录文件\n")
        
        # 处理每个文件
        for i, filename in enumerate(json_files, 1):
            print(f"[{i}/{len(json_files)}] 处理 {filename}...", end=' ')
            
            # 1. 备份原始文件
            if self.backup_file(filename):
                print("✅ 已备份", end=' ')
            else:
                print("❌ 备份失败", end=' ')
                continue
            
            # 2. 清洗文件
            result = self.clean_history_file(filename)
            
            if 'error' in result:
                print(f"❌ {result['error']}")
            else:
                self.stats['cleaned_files'] += 1
                total = result['total']
                cleaned = result['cleaned']
                print(f"📊 共{total}条, 清洗{cleaned}条")
        
        # 打印总结
        self.print_summary()
        
        return self.stats
    
    def print_summary(self):
        """打印清洗总结"""
        print("\n" + "=" * 70)
        print("📊 清洗总结")
        print("=" * 70)
        print(f"总文件数: {self.stats['total_files']}")
        print(f"成功清洗: {self.stats['cleaned_files']}")
        print(f"总记录数: {self.stats['total_records']}")
        print(f"清洗记录: {self.stats['cleaned_records']}")
        print(f"移除思考: {self.stats['removed_thinking']}")
        print(f"移除人格: {self.stats['removed_persona']}")
        
        if self.stats['total_records'] > 0:
            clean_rate = self.stats['cleaned_records'] / self.stats['total_records'] * 100
            print(f"\n清洗率: {clean_rate:.2f}%")
        
        print("\n✅ 清洗完成！")
        print(f"   原始文件备份至: {self.backup_dir}")
        print(f"   清洗文件保存至: {self.cleaned_dir}")
        print("=" * 70)


def main():
    """主函数"""
    # 配置路径
    project_root = Path(__file__).parent.parent.parent
    source_dir = project_root / "joha" / "storage" / "history"
    backup_dir = project_root / "joha" / "storage" / "history-backup"
    # 清洗后的文件保存到工作目录的 new-history 文件夹
    cleaned_dir = project_root / "new-history"
    
    # 创建清洗器并执行
    cleaner = HistoryCleaner(
        source_dir=str(source_dir),
        backup_dir=str(backup_dir),
        cleaned_dir=str(cleaned_dir)
    )
    
    stats = cleaner.clean_all()
    
    # 保存清洗报告
    report_file = cleaned_dir / "cleaning_report.json"
    report = {
        'timestamp': datetime.now().isoformat(),
        'stats': stats,
        'source_dir': str(source_dir),
        'backup_dir': str(backup_dir),
        'cleaned_dir': str(cleaned_dir),
    }
    
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n📄 清洗报告已保存: {report_file}")


if __name__ == "__main__":
    main()
