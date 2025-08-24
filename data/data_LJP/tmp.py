import os
import shutil

# 获取当前目录
current_dir = os.getcwd()
print(current_dir)
# 收集所有数字文件夹并转换为整数
folders = []
for name in os.listdir(current_dir):
    if os.path.isdir(os.path.join(current_dir, name)):
        try:
            folder_id = int(name[8:])
            folders.append((folder_id, name))
        except ValueError:
            pass

# 按原始数字排序
folders.sort(key=lambda x: x[0])
print(folders)
# 创建临时目录用于中转
temp_dir = os.path.join(current_dir, "TEMP_RENAME_DIR")
os.makedirs(temp_dir, exist_ok=True)

# 第一步：将所有文件夹移动到临时目录（使用临时名称）
for idx, (_, name) in enumerate(folders):
    src = os.path.join(current_dir, name)
    temp_name = f"temp_{idx}"
    dst = os.path.join(temp_dir, temp_name)
    shutil.move(src, dst)

# 第二步：从临时目录移回并重命名为1~200
ids=[10*i+j for i in range(40) for j in range(5)]
print(len(ids))
for new_id, (_, temp_name) in enumerate(folders, start=1):
    src = os.path.join(temp_dir, f"temp_{new_id-1}")
    dst = os.path.join(current_dir, str(ids[new_id-1]))
    shutil.move(src, dst)

# 删除临时目录
shutil.rmtree(temp_dir)

# print("重命名完成！原始文件夹已按数字顺序重命名为1~200。")