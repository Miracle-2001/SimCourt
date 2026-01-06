# -*- coding: utf-8 -*-
"""
反思检查脚本：逐项检查sim_human_compare中的评价结果，验证option和理由是否匹配
如果发现不匹配，则根据理由修正option，保存到ref_id.json文件
"""

import json
import os
import openai
from tqdm import tqdm
from datetime import datetime
import re


def query_model(instruction: str, prompt: str) -> str:
    """
    调用大语言模型进行推理

    Args:
        instruction: 系统指令
        prompt: 用户提示词

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
        temperature=0.7
    )
    return response.choices[0].message.content


def check_single_item(item_name: str, option: str, text: str, instruction: str) -> tuple:
    """
    检查单个评价项的option和text是否匹配

    Args:
        item_name: 评价项名称
        option: 原始选项 (A/B/C)
        text: 理由文本
        instruction: 系统指令

    Returns:
        (corrected_option, changed) - 修正后的选项和是否发生改变
    """
    # 如果text是解析失败的默认值，直接返回原值
    if "解析失败" in text or "模型未返回" in text:
        return option, False

    check_prompt = f"""请检查以下评价结果的"选项"和"理由"是否匹配。

【评价项】：{item_name}
【当前选项】：{option}
【理由】：{text}

【判断标准】：
- 如果理由明确说记录A更好（如提到"A更优秀"、"A表现更好"、"记录A的..."、"A的优势"等），选项应该是A
- 如果理由明确说记录B更好（如提到"B更优秀"、"B表现更好"、"记录B的..."、"B的优势"等），选项应该是B
- 如果理由认为两者相当（如提到"相当"、"差不多"、"各有优劣"、"无明显差异"等），选项应该是C
- 如果理由明显偏向某一方但选项错误，请指出正确的选项

【输出格式】：
请只输出一个字母（A、B或C），表示根据理由应该选择的正确选项。不要输出任何其他内容。"""

    try:
        response = query_model(instruction, check_prompt)
        # 提取字母
        match = re.search(r'[ABC]', response.upper())
        if match:
            corrected_option = match.group()
            if corrected_option != option:
                return corrected_option, True
        return option, False
    except Exception as e:
        print(f"      检查出错: {e}")
        return option, False


def reflect_and_save_json(input_dir: str, output_dir: str):
    """
    加载所有JSON文件，逐项检查，保存修正后的结果

    Args:
        input_dir: 输入目录（sim_human_compare）
        output_dir: 输出目录（保存ref_id.json）
    """
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)

    # 系统指令
    instruction = """你是一个专业的庭审评价质量检查专家。你需要仔细阅读评价理由，判断给出的选项是否与理由内容一致。"""

    # 获取所有json文件
    json_files = sorted([f for f in os.listdir(input_dir) if f.endswith(".json")],
                        key=lambda x: int(x.replace(".json", "")))

    print(f"找到 {len(json_files)} 个JSON文件需要检查\n")

    # 统计信息
    total_items = 0
    total_changed = 0
    failed_items = []  # 记录失败项

    for json_file in tqdm(json_files, desc="反思检查进度"):
        input_path = os.path.join(input_dir, json_file)
        data_id = json_file.replace(".json", "")
        output_path = os.path.join(output_dir, f"ref_{data_id}.json")

        # 加载JSON
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        print(f"\n检查 {json_file}...")

        # 遍历所有阶段、角色、评价项
        if "data" in data:
            for stage_name, stage_data in data["data"].items():
                for role_name, role_data in stage_data.items():
                    for item_name, item_data in role_data.items():
                        total_items += 1
                        original_option = item_data.get("option", "C")
                        text = item_data.get("text", "")

                        # 检查是否是解析失败项，记录到failed
                        if "解析失败" in text or "模型未返回" in text or "评价出错" in text:
                            failed_items.append(f"id={data_id}, stage={stage_name}, role={role_name}, item={item_name}, text={text}")
                            continue  # 跳过检查，保持原值

                        # 检查该项
                        corrected_option, changed = check_single_item(
                            item_name, original_option, text, instruction
                        )

                        if changed:
                            total_changed += 1
                            print(f"  修正: [{stage_name}][{role_name}]{item_name}: {original_option} -> {corrected_option}")
                            data["data"][stage_name][role_name][item_name]["option"] = corrected_option

        # 更新修改时间
        data["last_modified"] = datetime.now().isoformat()
        data["reflected"] = True

        # 保存修正后的结果
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # 保存失败记录到failed.txt
    if failed_items:
        failed_log_path = os.path.join(output_dir, "failed.txt")
        with open(failed_log_path, 'w', encoding='utf-8') as f:
            f.write(f"# 反思检查发现的解析失败项 - {datetime.now().isoformat()}\n")
            f.write(f"# 总计: {len(failed_items)} 项\n\n")
            for item in failed_items:
                f.write(item + "\n")
        print(f"\n发现 {len(failed_items)} 个失败项，已记录到 failed.txt")

    print(f"\n反思检查完成！")
    print(f"总检查项数: {total_items}")
    print(f"总修正项数: {total_changed}")
    print(f"失败项数: {len(failed_items)}")
    print(f"结果保存在 {output_dir} 目录")


def main():
    """主函数"""
    # 获取当前脚本所在目录
    base_dir = os.path.dirname(os.path.abspath(__file__))
    input_dir = os.path.join(base_dir, "sim_human_compare")
    output_dir = os.path.join(base_dir, "sim_human_compare")  # 保存在同一目录下

    reflect_and_save_json(input_dir, output_dir)


if __name__ == "__main__":
    main()
