import os
import shutil

def clean_folders():
    """清理每个文件夹，只保留data_anonymized.json"""
    current_dir = os.getcwd()
    deleted_count = 0
    kept_count = 0
    
    for folder_name in os.listdir(current_dir):
        folder_path = os.path.join(current_dir, folder_name)
        
        if os.path.isdir(folder_path):
            # 检查目标文件是否存在
            target_file = os.path.join(folder_path, "data_anonymized.json")
            target_exists = os.path.exists(target_file)
            
            # 遍历文件夹内容
            for file_name in os.listdir(folder_path):
                file_path = os.path.join(folder_path, file_name)
                
                # 保留目标文件，删除其他所有内容
                if os.path.isfile(file_path):
                    if file_name == "data_anonymized.json":
                        kept_count += 1
                    else:
                        os.remove(file_path)
                        deleted_count += 1
                
                # 删除子目录
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
                    deleted_count += 1
            
            # 如果目标文件不存在，记录警告
            if not target_exists:
                print(f"警告: 文件夹 {folder_name} 中未找到 data_anonymized.json")
    
    print(f"清理完成！保留了 {kept_count} 个目标文件，删除了 {deleted_count} 个文件/文件夹")
    return True

if __name__ == "__main__":
    print("=== 文件夹重命名与清理工具 ===")
    
    # 第一步：重命名文件夹
    clean_folders()
    print("\n所有操作已完成！")