"""
知识库数据迁移脚本 - 备份旧文件并执行转换
"""
import shutil
from pathlib import Path
from datetime import datetime


def backup_and_migrate():
    """备份旧 txt 文件并执行迁移"""
    project_root = Path(__file__).parent.parent.parent
    txt_dir = project_root / "joha" / "storage" / "txt"
    backup_dir = txt_dir / "txt_backup"
    
    print("=" * 60)
    print("知识库数据迁移工具")
    print("=" * 60)
    
    # 1. 备份旧 txt 文件
    txt_files = list(txt_dir.glob("*.txt"))
    if txt_files:
        print(f"\n📦 步骤 1: 备份 {len(txt_files)} 个 txt 文件")
        backup_dir.mkdir(exist_ok=True)
        
        for txt_file in txt_files:
            backup_path = backup_dir / txt_file.name
            shutil.copy2(txt_file, backup_path)
            print(f"   ✅ 已备份: {txt_file.name}")
        
        print(f"✅ 备份完成: {backup_dir}")
    else:
        print("\n⚠️  未找到需要备份的 txt 文件")
    
    # 2. 执行 txt → JSON 转换
    print(f"\n🔄 步骤 2: 执行 txt → JSON 转换")
    from joha.scripts.convert_txt_to_json import convert_txt_to_json
    convert_txt_to_json(str(txt_dir))
    
    # 3. 执行 JSON → 分片合并
    print(f"\n🔄 步骤 3: 执行 JSON → 分片合并")
    from joha.scripts.merge_knowledge_shards import merge_to_shards, load_json_files
    
    documents = load_json_files(str(txt_dir))
    if documents:
        merge_to_shards(documents, str(txt_dir), shard_size=100)
        
        # 4. 移动独立 JSON 文件到备份目录
        print(f"\n📦 步骤 4: 备份独立 JSON 文件")
        old_individual_dir = txt_dir / "old_individual"
        old_individual_dir.mkdir(exist_ok=True)
        
        json_files = [f for f in txt_dir.glob("*.json") 
                     if not f.name.startswith('knowledge_') and not f.name.endswith('_report.json')]
        
        for json_file in json_files:
            backup_path = old_individual_dir / json_file.name
            shutil.move(str(json_file), str(backup_path))
            print(f"   ✅ 已移动: {json_file.name}")
        
        print(f"✅ 独立 JSON 文件已备份到: {old_individual_dir}")
    else:
        print("⚠️  没有 JSON 文件需要合并")
    
    print("\n" + "=" * 60)
    print("迁移完成！")
    print("=" * 60)


if __name__ == "__main__":
    backup_and_migrate()
