'''
检查并修正评价结果中option和text不匹配的问题

数据源：
- ./sim_AgentCourt_compare/*.json (50个文件)
- ./sim_AgentsCourt_compare/*.json (50个文件)

功能：
读取每个评价结果JSON文件，逐一检查每一项评价，确保option和text是对应的。
如果不匹配，调用大模型根据text重新确定正确的option。
'''

import json
import os
import openai
from tqdm import tqdm
from datetime import datetime


def query_model(instruction: str, prompt: str, temperature: float = 0.7, max_tokens: int = 2000) -> str:
    """
    调用大语言模型进行推理

    Args:
        instruction: 系统指令
        prompt: 用户提示词
        temperature: 温度参数
        max_tokens: 最大token数

    Returns:
        模型返回的内容
    """
    client = openai.OpenAI(
        api_key="sk-tF_JyVDc4Os3XxBOjtE9bg",
        base_url="https://llmapi.paratera.com/v1/"
    )

    response = client.chat.completions.create(
        model="DeepSeek-V3.2",
        messages=[{"role": "user", "content": instruction + "\n" + prompt}],
        temperature=temperature,
        max_tokens=max_tokens
    )
    return response.choices[0].message.content.strip()


def check_and_fix_option(text: str, instruction: str) -> str:
    """
    根据评价理由重新确定option

    Args:
        text: 评价理由
        instruction: 系统指令

    Returns:
        正确的option (A/B/C)
    """
    reflection_prompt = f"""你是一个专业的庭审评价质量检查专家。现在需要根据以下评价理由，判断应该选择哪个选项。

【评价理由】：
{text}

【选项说明】：
- A：记录A表现更好
- B：记录B表现更好
- C：两者相当或无法区分

【任务要求】：
请仅根据上述"评价理由"的实质内容，判断应该选择A、B还是C。

判断规则：
1. 如果理由明确指出记录A表现更好（如提到"A更..."、"A优势..."、"记录A的..."等），选A
2. 如果理由明确指出记录B表现更好（如提到"B更..."、"B优势..."、"记录B的..."等），选B
3. 如果理由认为两者相当或无法区分（如提到"相当"、"差不多"、"各有优劣"、"都不突出"等），选C

【输出格式要求】：
请直接输出A或者B或者C（仅输出这一个字符，不要输出别的任何其他字符！）
"""

    try:
        # 调用模型
        new_option = query_model(instruction, reflection_prompt)

        # 清理结果，取第一个字符
        new_option = new_option.strip().upper()
        if new_option and new_option[0] in ["A", "B", "C"]:
            return new_option[0]
        else:
            print(f"    模型返回异常: {new_option}")
            return None

    except Exception as e:
        print(f"    检查出错: {e}")
        return None


def check_and_fix_one_file(file_path: str, instruction: str, dry_run: bool = False) -> dict:
    """
    检查并修正一个评价结果文件

    Args:
        file_path: 文件路径
        instruction: 系统指令
        dry_run: 是否只是检查不修改

    Returns:
        修正后的结果字典，以及统计信息
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        result = json.load(f)

    stats = {
        "total": 0,
        "checked": 0,
        "fixed": 0,
        "failed": 0,
        "fixes": []  # 记录修正详情
    }

    # 系统指令
    instruction = f"""你是一个专业的庭审评价专家，具有丰富的刑事诉讼庭审经验。
你需要客观、公正地根据评价理由判断哪个记录表现更好。"""

    data = result.get("data", {})
    data_id = result.get("data_id", "?")

    print(f"\n检查 data_id={data_id}...")

    # 遍历所有阶段、角色、评价项
    for stage_name in data:
        for role_name in data[stage_name]:
            for item_name in data[stage_name][role_name]:
                stats["total"] += 1
                item_data = data[stage_name][role_name][item_name]

                original_option = item_data.get("option", "C")
                text = item_data.get("text", "")

                if not text or text == "解析失败，默认为C":
                    # 跳过没有有效理由的项
                    print(f"  [{stats['total']}] {stage_name} - {role_name} - {item_name}: 跳过（无有效理由）")
                    continue

                print(f"  [{stats['total']}] {stage_name} - {role_name} - {item_name}: 原选项={original_option}")

                # 调用模型检查
                stats["checked"] += 1
                new_option = check_and_fix_option(text, instruction)

                if new_option is None:
                    stats["failed"] += 1
                    print(f"      检查失败，保持原值")
                    continue

                if new_option != original_option:
                    stats["fixed"] += 1
                    fix_info = {
                        "stage": stage_name,
                        "role": role_name,
                        "item": item_name,
                        "old_option": original_option,
                        "new_option": new_option,
                        "text": text[:100] + "..." if len(text) > 100 else text
                    }
                    stats["fixes"].append(fix_info)
                    print(f"      修正: {original_option} -> {new_option}")

                    if not dry_run:
                        item_data["option"] = new_option
                else:
                    print(f"      一致: {new_option}")

    # 更新修改时间
    if not dry_run and stats["fixed"] > 0:
        result["last_modified"] = datetime.now().isoformat()

    return result, stats


def main():
    """
    主函数：检查并修正所有评价结果文件
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # 需要检查的目录
    check_dirs = [
        ("sim_AgentCourt_compare", "AgentCourt"),
        ("sim_AgentsCourt_compare", "AgentsCourt")
    ]

    # 系统指令
    instruction = f"""你是一个专业的庭审评价专家，具有丰富的刑事诉讼庭审经验。
你需要客观、公正地根据评价理由判断哪个记录表现更好。"""

    # 是否只是检查不实际修改（设为False则实际修改文件）
    DRY_RUN = False

    if DRY_RUN:
        print("=" * 60)
        print("【DRY RUN模式】只检查不修改文件")
        print("=" * 60)
    else:
        print("=" * 60)
        print("【正式模式】将直接修改文件")
        print("=" * 60)

    # 总体统计
    total_stats = {
        "files": 0,
        "total_items": 0,
        "checked_items": 0,
        "fixed_items": 0,
        "failed_items": 0
    }

    for dir_name, baseline_name in check_dirs:
        check_dir = os.path.join(base_dir, dir_name)

        print(f"\n{'='*60}")
        print(f"开始检查: {dir_name} ({baseline_name})")
        print(f"{'='*60}\n")

        if not os.path.exists(check_dir):
            print(f"警告：目录不存在 {check_dir}")
            continue

        # 获取所有JSON文件
        json_files = sorted([f for f in os.listdir(check_dir) if f.endswith(".json")],
                           key=lambda x: int(x.replace(".json", "")) if x.replace(".json", "").isdigit() else 0)

        print(f"找到 {len(json_files)} 个文件\n")

        # 遍历每个文件
        for filename in tqdm(json_files, desc=f"{baseline_name} 检查进度"):
            file_path = os.path.join(check_dir, filename)

            try:
                result, stats = check_and_fix_one_file(file_path, instruction, DRY_RUN)

                # 保存修正后的结果
                if not DRY_RUN and stats["fixed"] > 0:
                    # 备份原文件
                    backup_path = file_path + ".backup"
                    with open(backup_path, 'w', encoding='utf-8') as f:
                        json.dump(json.load(open(file_path, 'r', encoding='utf-8')), f, ensure_ascii=False, indent=2)

                    # 保存修正后的文件
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(result, f, ensure_ascii=False, indent=2)
                    print(f"    已保存修正，原文件备份为 {filename}.backup")

                # 累计统计
                total_stats["files"] += 1
                total_stats["total_items"] += stats["total"]
                total_stats["checked_items"] += stats["checked"]
                total_stats["fixed_items"] += stats["fixed"]
                total_stats["failed_items"] += stats["failed"]

            except Exception as e:
                print(f"处理文件 {filename} 时出错: {e}")
                import traceback
                traceback.print_exc()

        print(f"\n{baseline_name} 检查完成！")

    # 打印总体统计
    print(f"\n{'='*60}")
    print("总体统计")
    print(f"{'='*60}")
    print(f"处理文件数: {total_stats['files']}")
    print(f"总评价项数: {total_stats['total_items']}")
    print(f"实际检查数: {total_stats['checked_items']}")
    print(f"修正项数:   {total_stats['fixed_items']}")
    print(f"失败项数:   {total_stats['failed_items']}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
