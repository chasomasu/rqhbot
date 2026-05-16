"""
知识库分片合并脚本 - 将独立 JSON 文件合并为分片式存储
每片上限 100 条记录，超出自动新建分片
"""
import os
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict


def load_json_files(json_dir: str) -> List[Dict]:
    """
    加载目录下所有独立的 JSON 文件
    
    Args:
        json_dir: JSON 文件目录
        
    Returns:
        文档列表
    """
    json_path = Path(json_dir)
    json_files = list(json_path.glob("*.json"))
    
    # 排除分片文件和报告文件
    json_files = [f for f in json_files if not f.name.startswith('knowledge_') and not f.name.endswith('_report.json')]
    
    documents = []
    
    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                doc = json.load(f)
                documents.append(doc)
        except Exception as e:
            print(f"❌ 加载失败 {json_file}: {e}")
    
    return documents


def merge_to_shards(documents: List[Dict], output_dir: str, shard_size: int = 100):
    """
    将文档列表合并为分片文件
    
    Args:
        documents: 文档列表
        output_dir: 输出目录
        shard_size: 每个分片的最大文档数（默认100）
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    if not documents:
        print("⚠️  没有文档需要合并")
        return
    
    print(f"📊 总文档数: {len(documents)}")
    print(f"📦 分片大小: {shard_size} 条/片")
    print(f"📁 预计分片数: {(len(documents) + shard_size - 1) // shard_size}")
    
    # 按时间戳排序
    documents.sort(key=lambda x: x.get('timestamp', ''))
    
    # 分片
    shards = []
    for i in range(0, len(documents), shard_size):
        shard_docs = documents[i:i + shard_size]
        shard_num = (i // shard_size) + 1
        shards.append((shard_num, shard_docs))
    
    # 保存分片文件
    for shard_num, shard_docs in shards:
        shard_filename = f"knowledge_{shard_num:04d}.json"
        shard_path = output_path / shard_filename
        
        shard_data = {
            'metadata': {
                'shard_number': shard_num,
                'total_shards': len(shards),
                'document_count': len(shard_docs),
                'created_at': datetime.now().isoformat(),
                'version': '1.8.0',
            },
            'documents': shard_docs,
        }
        
        with open(shard_path, 'w', encoding='utf-8') as f:
            json.dump(shard_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 已保存分片 {shard_num}/{len(shards)}: {shard_filename} ({len(shard_docs)} 条)")
    
    # 保存合并报告
    report = {
        'timestamp': datetime.now().isoformat(),
        'total_documents': len(documents),
        'shard_size': shard_size,
        'total_shards': len(shards),
        'shards': [
            {
                'shard_number': num,
                'document_count': len(docs),
                'filename': f"knowledge_{num:04d}.json",
            }
            for num, docs in shards
        ],
    }
    
    report_path = output_path / "merge_report.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n📄 合并报告已保存: {report_path}")
    print(f"\n✅ 分片合并完成！")


def main():
    """主函数"""
    project_root = Path(__file__).parent.parent.parent
    json_dir = project_root / "joha" / "storage" / "txt"
    
    print("=" * 60)
    print("知识库分片合并工具 - 独立 JSON → 分片式存储")
    print("=" * 60)
    print(f"\n源目录: {json_dir}")
    print(f"目标目录: {json_dir}")
    print("\n开始合并...\n")
    
    # 加载所有独立 JSON 文件
    documents = load_json_files(str(json_dir))
    
    if not documents:
        print("⚠️  未找到任何独立的 JSON 文件")
        return
    
    # 合并为分片
    merge_to_shards(documents, str(json_dir), shard_size=100)
    
    print("\n" + "=" * 60)
    print("合并完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
