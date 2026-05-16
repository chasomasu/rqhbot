"""
知识库迁移脚本 - txt 格式转换为结构化 JSON
将旧版逐词存储的 txt 文件转换为结构化 JSON 格式
"""
import os
import re
import json
from datetime import datetime
from pathlib import Path


def parse_txt_file(txt_path: Path) -> dict:
    """
    解析单个 txt 文件，提取结构化信息
    
    Args:
        txt_path: txt 文件路径
        
    Returns:
        结构化字典，包含 id, filename, title, source, full_text, question, response, timestamp, word_count, char_count
    """
    try:
        content = txt_path.read_text(encoding='utf-8')
        
        # 提取时间戳（从文件名或内容）
        filename = txt_path.name
        timestamp_match = re.match(r'(\d{8}_\d{6})', filename)
        if timestamp_match:
            timestamp_str = timestamp_match.group(1)
            timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S").isoformat()
        else:
            timestamp = datetime.now().isoformat()
        
        # 提取标题（从文件名去除时间戳和扩展名）
        title = re.sub(r'^\d{8}_\d{6}-', '', filename.replace('.txt', ''))
        title = title.replace('_', ' ').replace('-', ' ').strip()
        
        # 提取用户问题和 AI 回复
        question = ""
        response = ""
        
        # 尝试匹配标准格式
        question_match = re.search(r'【用户问题】\s*\n(.*?)(?=\n\n【AI 回复】|$)', content, re.DOTALL)
        response_match = re.search(r'【AI 回复】\s*\n(.*)', content, re.DOTALL)
        
        if question_match:
            question = question_match.group(1).strip()
        if response_match:
            response = response_match.group(1).strip()
        
        # 如果没有标准格式，尝试其他解析方式
        if not question and not response:
            lines = content.strip().split('\n')
            for i, line in enumerate(lines):
                if '【用户问题】' in line or '问题' in line:
                    if i + 1 < len(lines):
                        question = lines[i + 1].strip()
                if '【AI 回复】' in line or '回复' in line:
                    if i + 1 < len(lines):
                        response = lines[i + 1].strip()
        
        # 如果仍然没有提取到，使用整个内容作为 full_text
        full_text = content.strip()
        
        # 计算统计信息
        word_count = len(full_text.split())
        char_count = len(full_text)
        
        return {
            'id': f"doc_{timestamp}_{filename}",
            'filename': filename,
            'title': title[:100],  # 限制标题长度
            'source': 'txt_migration',
            'full_text': full_text,
            'question': question[:500] if question else '',  # 限制问题长度
            'response': response[:1000] if response else '',  # 限制回复长度
            'timestamp': timestamp,
            'word_count': word_count,
            'char_count': char_count,
        }
    
    except Exception as e:
        print(f"❌ 解析失败 {txt_path}: {e}")
        return None


def convert_txt_to_json(txt_dir: str, output_dir: str = None):
    """
    将 txt 目录下的所有文件转换为 JSON
    
    Args:
        txt_dir: txt 文件目录
        output_dir: JSON 输出目录（默认与 txt_dir 相同）
    """
    txt_path = Path(txt_dir)
    if output_dir is None:
        output_dir = txt_dir
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # 查找所有 txt 文件
    txt_files = list(txt_path.rglob("*.txt"))
    
    if not txt_files:
        print(f"⚠️  未找到任何 txt 文件: {txt_dir}")
        return
    
    print(f"📂 找到 {len(txt_files)} 个 txt 文件")
    
    converted = []
    failed = []
    
    for txt_file in txt_files:
        result = parse_txt_file(txt_file)
        if result:
            converted.append(result)
        else:
            failed.append(str(txt_file))
    
    # 保存为独立的 JSON 文件
    for doc in converted:
        json_filename = doc['filename'].replace('.txt', '.json')
        json_path = output_path / json_filename
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(doc, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 转换完成:")
    print(f"   成功: {len(converted)} 个文件")
    print(f"   失败: {len(failed)} 个文件")
    
    if failed:
        print(f"\n❌ 失败的文件:")
        for f in failed[:10]:  # 只显示前10个
            print(f"   - {f}")
        if len(failed) > 10:
            print(f"   ... 还有 {len(failed) - 10} 个文件")
    
    # 保存转换报告
    report = {
        'timestamp': datetime.now().isoformat(),
        'total_files': len(txt_files),
        'converted': len(converted),
        'failed': len(failed),
        'failed_files': failed,
    }
    
    report_path = output_path / "conversion_report.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n📄 转换报告已保存: {report_path}")


if __name__ == "__main__":
    # 配置路径
    project_root = Path(__file__).parent.parent.parent
    txt_dir = project_root / "joha" / "storage" / "txt"
    
    print("=" * 60)
    print("知识库迁移工具 - txt → JSON")
    print("=" * 60)
    print(f"\n源目录: {txt_dir}")
    print(f"目标目录: {txt_dir}")
    print("\n开始转换...\n")
    
    convert_txt_to_json(str(txt_dir))
    
    print("\n" + "=" * 60)
    print("转换完成！")
    print("=" * 60)
