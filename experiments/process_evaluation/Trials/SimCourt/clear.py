import os
import re

def rename_json_files():
    """
    重命名当前目录下所有匹配模式的JSON文件
    将 case_x_MMDD_HHMM.json 重命名为 case_x.json
    """
    # 编译正则表达式，匹配 case_数字_日期_时间.json
    pattern = re.compile(r'^(case_\d+)_\d{4}_\d{4}\.json$')
    
    renamed_count = 0
    error_count = 0
    
    # 获取当前目录下的所有文件
    for filename in os.listdir('.'):
        # 检查文件是否为JSON文件且匹配我们的模式
        match = pattern.match(filename)
        if match:
            # 构建新文件名
            new_filename = f"{match.group(1)}.json"
            
            try:
                # 重命名文件
                os.rename(filename, new_filename)
                print(f"✓ 已重命名: {filename} -> {new_filename}")
                renamed_count += 1
            except Exception as e:
                print(f"✗ 重命名失败 {filename}: {e}")
                error_count += 1
    
    # 打印总结
    print(f"\n{'='*50}")
    print(f"重命名完成!")
    print(f"成功: {renamed_count} 个文件")
    print(f"失败: {error_count} 个文件")
    print(f"{'='*50}")

def list_current_json_files():
    """
    列出当前目录下所有的JSON文件
    """
    print("当前目录下的JSON文件:")
    print("-" * 50)
    
    json_files = [f for f in os.listdir('.') if f.lower().endswith('.json')]
    
    if not json_files:
        print("未找到JSON文件")
        return
    
    for i, filename in enumerate(json_files, 1):
        print(f"{i:2d}. {filename}")
    
    print(f"总计: {len(json_files)} 个JSON文件")
    print("-" * 50)
    print()

if __name__ == "__main__":
    print("JSON文件重命名工具")
    print("=" * 50)
    
    # 先列出当前目录下的JSON文件
    list_current_json_files()
    
    # 询问用户是否继续
    response = input("是否要重命名这些文件? (输入 'y' 确认, 其他键取消): ")
    
    if response.lower() == 'y':
        print("\n开始重命名...")
        rename_json_files()
    else:
        print("操作已取消")