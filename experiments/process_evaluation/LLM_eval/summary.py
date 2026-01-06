'''

在summary中写一下对于评价结果的统计。
结果来源于3个文件夹：sim_human_compare，sim_AgentsCourt_compare,sim_AgentCourt_compare
各自有50个评价记录
其中sim_human_compare中的记录是ref_1.json~ref_50.json
而另外两个sim_AgentsCourt_compare,sim_AgentCourt_compare中的记录是1.json~50.json

你要统计的事情是：
1.把50个记录按顺序合并到一个json里面，合并的时候，同一个评价维度的放到一起，合并成一个list。
比如sim_human_compare里面有30项，你最后输出的json应该就类似是：
{
    "法庭调查-审判长-引导结构清晰性":[C,A,B,C,A,B],  (这个list长度应当为50)
    "法庭调查-审判长-中立性与流程控制":[C,A,B,C,A,B]  (这个list长度应当为50)
    ...
}
而sim_AgentCourt_compare和sim_AgentsCourt_compare只有6项，那么保存json的时候就保留那6项就行了。（也就是只有6个key）

保存的json直接保存到和当前summary.py同目录就行。

2.计算每一项中，认为simcourt好的有多少个，认为其他的（human或者AgentsCourt或者AgentCourt)好的有多少个，平手的有多少个。
注意，A，B，C本身只是一个选项，由于simcourt有时候在A有时候在B的位置，所以你要还原一下。
具体来说，sim_human_compare里面，
POSITION_OFFSET_LIST = [1, -1, 1, 1, -1, -1, -1, 1, 1, -1, 1, -1, -1, 1, 1, -1, 1, -1, -1, 1,
                        1, -1, 1, -1, -1, 1, -1, 1, -1, 1, -1, -1, 1, -1, 1, -1, 1, 1, -1, 1,
                        -1, 1, -1, -1, 1, -1, 1, -1, 1, -1]
而对于sim_AgentCourt_compare和sim_AgentsCourt_compare,位置偏移是：
POSITION_RULE = [1, -1, 1, 1, -1, 1, -1, -1, -1, 1, -1, 1, 1, -1, -1, 1, 1, 1, -1, -1, -1, 1, 1, -1, -1, -1, 1, 1, 1, -1, 1, -1, -1, -1, 1, 1, -1, 1, 1, 1, -1, -1, 1, -1, -1, -1, 1, 1, -1, 1]

这个位置偏移的意思是：下标0~49对应案件id 1~50，1表示simcourt在A位置，-1表示simcourt在B位置

所以你要借助这个位置偏移，来还原到底选项A代表的是simcourt好，还是另外一个好（当然选项C就不用管了，都一样，就是平手）

你的计算结果也是一个json，格式应该是：
{
    "法庭调查-审判长-引导结构清晰性":[30,5,15],  (三者之和应当为50)
    "法庭调查-审判长-中立性与流程控制":[30,5,15]   (三者之和应当为50)
    ...
}
这里面，[30,5,15]表示这个维度有30个案件是simcourt好，5个案子平手，15个案子是另外一个好。

保存的json直接保存到和当前summary.py同目录就行。

这个注释要保留。
'''

# ============================================================================
# 以下是实现的代码
# ============================================================================

import json
import os
from collections import defaultdict


# 位置偏移列表：下标0-49对应案件id 1-50
# 1表示simcourt在前（A位置），-1表示另一个在前（A位置）
POSITION_OFFSET_LIST = [1, -1, 1, 1, -1, -1, -1, 1, 1, -1, 1, -1, -1, 1, 1, -1, 1, -1, -1, 1,
                        1, -1, 1, -1, -1, 1, -1, 1, -1, 1, -1, -1, 1, -1, 1, -1, 1, 1, -1, 1,
                        -1, 1, -1, -1, 1, -1, 1, -1, 1, -1]

# sim_AgentCourt_compare和sim_AgentsCourt_compare的位置规则
POSITION_RULE = [1, -1, 1, 1, -1, 1, -1, -1, -1, 1, -1, 1, 1, -1, -1, 1, 1, 1, -1, -1, -1, 1, 1, -1, -1, -1, 1, 1, 1, -1, 1, -1, -1, -1, 1, 1, -1, 1, 1, 1, -1, -1, 1, -1, -1, -1, 1, 1, -1, 1]


def load_json_files(directory: str, file_prefix: str = "", file_suffix: str = ".json") -> dict:
    """
    加载目录中的所有JSON文件，按编号排序

    Args:
        directory: 目录路径
        file_prefix: 文件前缀（如"ref_"或""）
        file_suffix: 文件后缀（默认".json"）

    Returns:
        字典，key为文件编号（int），value为文件内容
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    full_dir = os.path.join(base_dir, directory)

    if not os.path.exists(full_dir):
        raise ValueError(f"目录不存在: {full_dir}")

    files = {}
    for filename in os.listdir(full_dir):
        if filename.startswith(file_prefix) and filename.endswith(file_suffix):
            # 提取文件编号
            name_without_prefix = filename[len(file_prefix):-len(file_suffix)]
            try:
                file_id = int(name_without_prefix)
                file_path = os.path.join(full_dir, filename)
                with open(file_path, 'r', encoding='utf-8') as f:
                    files[file_id] = json.load(f)
            except ValueError:
                continue

    # 按编号排序
    return dict(sorted(files.items()))


def get_item_key(stage: str, role: str, item_name: str) -> str:
    """
    生成评价项的唯一key

    Args:
        stage: 阶段名称
        role: 角色名称
        item_name: 评价项名称

    Returns:
        格式如 "法庭调查-审判长-引导结构清晰性" 的字符串
    """
    return f"{stage}-{role}-{item_name}"


def merge_results(files: dict) -> dict:
    """
    合并多个评价结果文件，将同一评价维度的结果合并到一个list中

    Args:
        files: 字典，key为文件编号，value为评价结果

    Returns:
        合并后的字典，格式为 {"评价维度key": [option1, option2, ...]}
    """
    merged = defaultdict(list)

    # 确保按文件编号顺序处理
    for file_id in sorted(files.keys()):
        result = files[file_id]
        data = result.get("data", {})

        # 遍历所有阶段、角色、评价项
        for stage in data:
            for role in data[stage]:
                for item_name in data[stage][role]:
                    key = get_item_key(stage, role, item_name)
                    option = data[stage][role][item_name].get("option", "C")
                    merged[key].append(option)

    return dict(merged)


def calculate_statistics(files: dict, position_list: list) -> dict:
    """
    计算统计信息：每个维度中simcourt胜/平/负的次数

    Args:
        files: 字典，key为文件编号，value为评价结果
        position_list: 位置列表，下标0-49对应案件id 1-50，1表示simcourt在A，-1表示在B

    Returns:
        统计字典，格式为 {"评价维度key": [simcourt_wins, ties, other_wins]}
    """
    stats = defaultdict(lambda: [0, 0, 0])  # [simcourt_wins, ties, other_wins]

    # 确保按文件编号顺序处理
    for file_id in sorted(files.keys()):
        result = files[file_id]
        data = result.get("data", {})

        # 获取该文件对应的位置偏移（file_id从1开始，列表下标从0开始）
        if 1 <= file_id <= len(position_list):
            position_offset = position_list[file_id - 1]
        else:
            # 如果超出范围，默认simcourt在A位置
            position_offset = 1

        # 遍历所有评价项
        for stage in data:
            for role in data[stage]:
                for item_name in data[stage][role]:
                    key = get_item_key(stage, role, item_name)
                    option = data[stage][role][item_name].get("option", "C")

                    if option == "C":
                        # 平手
                        stats[key][1] += 1
                    elif position_offset == 1:
                        # simcourt在A位置
                        if option == "A":
                            stats[key][0] += 1  # simcourt胜
                        elif option == "B":
                            stats[key][2] += 1  # 另一方胜
                    else:  # position_offset == -1
                        # simcourt在B位置
                        if option == "B":
                            stats[key][0] += 1  # simcourt胜
                        elif option == "A":
                            stats[key][2] += 1  # 另一方胜

    return dict(stats)


def save_json(data: dict, filename: str):
    """
    保存JSON文件到当前目录

    Args:
        data: 要保存的数据
        filename: 文件名
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(base_dir, filename)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"已保存: {filename}")


def process_directory(directory: str, file_prefix: str, position_list: list, output_prefix: str):
    """
    处理一个目录：生成合并结果和统计结果

    Args:
        directory: 目录名称
        file_prefix: 文件前缀
        position_list: 位置列表
        output_prefix: 输出文件前缀
    """
    print(f"\n处理目录: {directory}")

    # 加载所有文件
    files = load_json_files(directory, file_prefix)
    print(f"  加载了 {len(files)} 个文件")

    if len(files) == 0:
        print(f"  警告：目录 {directory} 中没有找到有效的文件")
        return

    # 1. 生成合并结果
    merged = merge_results(files)
    output_merged_file = f"{output_prefix}_merged.json"
    save_json(merged, output_merged_file)

    # 2. 生成统计结果
    stats = calculate_statistics(files, position_list)
    output_stats_file = f"{output_prefix}_stats.json"
    save_json(stats, output_stats_file)

    # 打印简要统计
    print(f"  评价维度数量: {len(merged)}")
    total_items = sum(len(v) for v in merged.values())
    print(f"  总评价项数: {total_items}")

    # 验证统计
    for key, counts in stats.items():
        if sum(counts) != 50:
            print(f"  警告：{key} 的统计总和不为50: {counts}")


def main():
    """
    主函数：处理所有三个目录
    """
    print("=" * 60)
    print("开始处理评价结果统计")
    print("=" * 60)

    # 处理 sim_human_compare
    process_directory(
        directory="sim_human_compare",
        file_prefix="ref_",
        position_list=POSITION_OFFSET_LIST,
        output_prefix="sim_human_compare"
    )

    # 处理 sim_AgentCourt_compare
    process_directory(
        directory="sim_AgentCourt_compare",
        file_prefix="",
        position_list=POSITION_RULE,
        output_prefix="sim_AgentCourt_compare"
    )

    # 处理 sim_AgentsCourt_compare
    process_directory(
        directory="sim_AgentsCourt_compare",
        file_prefix="",
        position_list=POSITION_RULE,
        output_prefix="sim_AgentsCourt_compare"
    )

    print("\n" + "=" * 60)
    print("所有处理完成！")
    print("=" * 60)
    print("\n生成的文件:")
    print("  - sim_human_compare_merged.json")
    print("  - sim_human_compare_stats.json")
    print("  - sim_AgentCourt_compare_merged.json")
    print("  - sim_AgentCourt_compare_stats.json")
    print("  - sim_AgentsCourt_compare_merged.json")
    print("  - sim_AgentsCourt_compare_stats.json")


if __name__ == "__main__":
    main()
