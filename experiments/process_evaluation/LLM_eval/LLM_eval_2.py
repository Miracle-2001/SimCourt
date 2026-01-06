# -*- coding: utf-8 -*-
"""
重新处理sim_human_compare中failed.txt记录的解析失败项
读取failed.txt，对失败的项重新调用大模型打分，成功则更新原文件，失败则记录到failed_2.txt
"""

import json
import os
import openai
from tqdm import tqdm
from datetime import datetime
import re


# ==================== 配置和常量 ====================

# 位置偏移列表
POSITION_OFFSET_LIST = [1, -1, 1, 1, -1, -1, -1, 1, 1, -1, 1, -1, -1, 1, 1, -1, 1, -1, -1, 1,
                        1, -1, 1, -1, -1, 1, -1, 1, -1, 1, -1, -1, 1, -1, 1, -1, 1, 1, -1, 1,
                        -1, 1, -1, -1, 1, -1, 1, -1, 1, -1]

# 30个评价维度定义（用于构建prompt）
EVALUATION_DIMENSIONS = [
    # 法庭调查 - 审判长
    {"stage": "法庭调查", "role": "审判长", "items": [
        ("引导结构清晰性", "法官是否以清晰、逻辑且循序渐进的方式构建法庭提问结构"),
        ("中立性与流程控制", "法官是否保持中立并确保程序流程顺畅"),
        ("证据审查是否专业", "法官是否以法律专业知识处理证据问题并遵守程序规范")
    ]},
    # 法庭调查 - 公诉人
    {"stage": "法庭调查", "role": "公诉人", "items": [
        ("讯问策略合理", "公诉人是否使用合法且有明确目标的讯问策略"),
        ("重点突出、语言专业", "公诉人在讯问中是否使用准确且专业的法律语言"),
        ("证据引导合法性", "公诉人的提问是否符合证据和程序规则")
    ]},
    # 法庭调查 - 辩护人
    {"stage": "法庭调查", "role": "辩护人", "items": [
        ("提问针对性强", "辩护人是否提出聚焦且与法律相关的问题"),
        ("合法程序敏感性高", "辩护人是否对程序合法性和司法规范表现出敏感度"),
        ("保护当事人权益意识", "辩护人是否积极维护和主张被告人的程序性和实质性权利")
    ]},
    # 举证质证环节 - 审判长
    {"stage": "举证质证环节", "role": "审判长", "items": [
        ("主持规范性", "法官是否按照法律标准和法庭礼仪主持庭审程序"),
        ("质证合法性控制", "法官是否确保交叉询问符合法律规则和证据边界"),
        ("公平保障意识", "法官是否维护公诉人和辩护人之间的公平和平等")
    ]},
    # 举证质证环节 - 公诉人
    {"stage": "举证质证环节", "role": "公诉人", "items": [
        ("证据叙述准确", "公诉人是否清晰、准确且无歪曲地呈现证据"),
        ("攻击力适度", "公诉人是否在没有不当敌意或不当压力的情况下保持说服力"),
        ("对异议回应得体", "公诉人是否以充分的法律依据和程序恰当性回应辩护人的异议")
    ]},
    # 举证质证环节 - 辩护人
    {"stage": "举证质证环节", "role": "辩护人", "items": [
        ("提出质疑抓住关键", "辩护人是否识别并质疑公诉方案件的核心问题"),
        ("证据辨析严谨", "辩护人是否对证据提供逻辑结构化且彻底的分析"),
        ("应对检方证据有效", "辩护人是否有说服力地驳斥、解释或中和公诉方的证据")
    ]},
    # 法庭辩论环节 - 审判长
    {"stage": "法庭辩论环节", "role": "审判长", "items": [
        ("引导对抗焦点清晰", "法官是否恰当地识别和界定法律争议的焦点"),
        ("不偏不倚发言介入", "法官的口头介入是否保持中立和程序公平"),
        ("控制节奏与秩序", "法官是否有效管理庭审的节奏和纪律")
    ]},
    # 法庭辩论环节 - 公诉人
    {"stage": "法庭辩论环节", "role": "公诉人", "items": [
        ("指控逻辑性强", "公诉方论证是否内部一致且具有法律结构"),
        ("法律引用精确", "是否正确且相关地引用法律权威来支持论证"),
        ("回应辩护有力", "公诉人是否以清晰和有力的方式回应并反驳辩护人的主张")
    ]},
    # 法庭辩论环节 - 辩护人
    {"stage": "法庭辩论环节", "role": "辩护人", "items": [
        ("辩点清晰", "辩护论点是否清晰表达且逻辑发展"),
        ("法律逻辑严密", "法律推理是否精确、内部一致且法律上合理"),
        ("情理表达得体", "论证是否平衡法理推理与适当的情感共鸣")
    ]},
    # 整体偏好
    {"stage": "整体偏好", "role": "审判长", "items": [("整体表现", "法官的整体表现")]},
    {"stage": "整体偏好", "role": "公诉人", "items": [("整体表现", "公诉人的整体表现")]},
    {"stage": "整体偏好", "role": "辩护人", "items": [("整体表现", "辩护人的整体表现")]}
]

# 角色描述映射
ROLE_DESCRIPTIONS = {
    ("法庭调查", "审判长"): "是否合乎程序逻辑，引导顺畅，未偏袒任何一方",
    ("法庭调查", "公诉人"): "能否突出关键事实，问题设计是否合规",
    ("法庭调查", "辩护人"): "是否积极为被告发声，避免走过场式辩护",
    ("举证质证环节", "审判长"): "能否保障双方有效开展质证",
    ("举证质证环节", "公诉人"): "对辩方质疑反应是否有理有力",
    ("举证质证环节", "辩护人"): "回应是否具体、专业、有影响力",
    ("法庭辩论环节", "审判长"): "不偏袒，适时引导，维持理性气氛",
    ("法庭辩论环节", "公诉人"): "说理是否充分，攻防是否聚焦",
    ("法庭辩论环节", "辩护人"): "避免过度废话，兼顾法律与人性表达",
    ("整体偏好", "审判长"): "要确保庭审程序公正，应当保障犯罪嫌疑人和其他诉讼参与人依法享有的辩护权和其他诉讼权利。",
    ("整体偏好", "公诉人"): "保证准确、及时地查明犯罪事实，正确应用法律，惩罚犯罪分子，保障无罪的人不受刑事追究。",
    ("整体偏好", "辩护人"): "根据事实和法律，提出犯罪嫌疑人、被告人无罪、罪轻或者减轻、免除其刑事责任的材料和意见，维护犯罪嫌疑人、被告人的诉讼权利和其他合法权益。"
}

STAGE_MAPPING = {
    "trial_investigation": "法庭调查",
    "presentation_evidence": "举证质证环节",
    "trial_debate": "法庭辩论环节"
}


# ==================== 工具函数 ====================

def query_model(instruction: str, prompt: str) -> str:
    """调用大语言模型"""
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


def load_json(file_path: str) -> dict:
    """加载JSON文件"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(data: dict, file_path: str):
    """保存JSON文件"""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def extract_stage_content(trial_record: dict, stage_key: str) -> str:
    """从庭审记录中提取指定阶段的内容"""
    if stage_key not in trial_record:
        return ""
    speeches = trial_record[stage_key]
    return "\n".join(speech.get("content", "") for speech in speeches)


def parse_failed_txt(failed_path: str) -> list:
    """
    解析failed.txt文件

    Returns:
        失败项列表，每项格式: {"data_id": int, "stage": str, "role": str, "item": str, "text": str}
    """
    failed_items = []
    with open(failed_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # 解析格式: id=1, stage=法庭调查, role=辩护人, item=提问针对性强, text=解析失败，默认为C
            if line.startswith("id="):
                item = {}
                parts = line.split(", ")
                for part in parts:
                    if "=" in part:
                        key, value = part.split("=", 1)
                        if key == "id":
                            item["data_id"] = int(value)
                        else:
                            item[key] = value
                if "data_id" in item:
                    failed_items.append(item)
    return failed_items


def build_prompt_for_single_item(stage_content_a: str, stage_content_b: str,
                                 stage_name: str, role: str, item_name: str,
                                 item_explanation: str, role_description: str) -> str:
    """为单个评价项构建prompt"""
    prompt = f"""你是一个专业的庭审评价专家。现在需要你对两份庭审记录在【{stage_name}】阶段【{role}】的表现进行比较评价。

【{role}在{stage_name}中的职责说明】：
{role_description}

【评价要求】：
1. 请忽略语癖、小范围复读等习惯，多关注内容实质。
2. 分要点评价，避免宏观评价。
3. 仔细对比两份记录，给出你认为表现更好的一方。
4. 评价结果说明：
   - 如果记录A（第一份记录）表现更好，请输出：A
   - 如果记录B（第二份记录）表现更好，请输出：B
   - 如果无法区分/两者相当，请输出：C
5. 特别地，如果某一个记录里面没有体现相应内容，而另一个记录里有相应内容，那么应该认为另外一个记录更优秀！
6. 特别地，如果两份记录里面都没有体现相应内容，那么应该输出C
7. 请详细说明理由！

【两份庭审记录的{stage_name}阶段内容如下】：

===== 记录A =====
{stage_content_a[:5000]}

===== 记录B =====
{stage_content_b[:5000]}

===== 评价维度 =====
**{item_name}**：{item_explanation}

【输出格式要求】：
请严格按照以下JSON格式输出，不要包含任何其他文字：
{{"{item_name}": {{"option": "A/B/C", "text": "理由说明"}}}}

请直接输出JSON，不要有任何其他解释。"""
    return prompt


def evaluate_single_item(stage_content_a: str, stage_content_b: str,
                        stage_name: str, role: str, item_name: str,
                        item_explanation: str, role_description: str) -> dict:
    """
    对单个评价项进行评价，带重试机制

    Returns:
        {"option": str, "text": str} 或 None（表示失败）
    """
    instruction = """你是一个专业的庭审评价专家，具有丰富的刑事诉讼庭审经验。
你需要客观、公正地评价两份庭审记录的表现，请按照给定的评价维度，仔细对比分析，给出准确的偏好性判断和理由。"""

    prompt = build_prompt_for_single_item(
        stage_content_a, stage_content_b, stage_name, role,
        item_name, item_explanation, role_description
    )

    max_retries = 3
    last_error = None

    for retry_count in range(max_retries):
        try:
            if retry_count > 0:
                # 重试时添加失败原因
                retry_prompt = prompt + f"\n\n【重要提醒】：前{retry_count}次解析失败，错误信息：{last_error}\n请务必严格按照JSON格式输出，不要包含任何其他文字说明！"
                response = query_model(instruction, retry_prompt)
                print(f"      第{retry_count + 1}次尝试（错误提醒）...")
            else:
                response = query_model(instruction, prompt)

            # 尝试解析JSON
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                try:
                    result = json.loads(json_match.group())
                    if item_name in result:
                        return result[item_name]
                    else:
                        last_error = f"JSON中缺少{item_name}字段"
                except json.JSONDecodeError as e:
                    last_error = f"JSON解析失败: {str(e)}"
            else:
                last_error = "未找到JSON格式输出"

        except Exception as e:
            last_error = str(e)

        print(f"      第{retry_count + 1}次失败: {last_error}")

    return None


def reevaluate_failed_items(failed_items: list, base_dir: str) -> list:
    """
    重新评估失败项

    Args:
        failed_items: 失败项列表
        base_dir: 基础目录

    Returns:
        仍然失败的项列表
    """
    # 按data_id分组，减少文件重复加载
    from collections import defaultdict
    items_by_id = defaultdict(list)
    for item in failed_items:
        items_by_id[item["data_id"]].append(item)

    # 路径设置
    simcourt_dir = os.path.join(base_dir, "..", "simcourt")
    real_human_dir = os.path.join(base_dir, "..", "real_human", "output")
    compare_dir = os.path.join(base_dir, "sim_human_compare")

    still_failed = []

    # 处理每个data_id
    for data_id, items in tqdm(sorted(items_by_id.items()), desc="重新处理进度"):
        print(f"\n处理 data_id={data_id}, 共{len(items)}个失败项")

        try:
            # 加载庭审记录
            simcourt_record = load_json(os.path.join(simcourt_dir, f"final_{data_id}.json"))
            real_human_record = load_json(os.path.join(real_human_dir, f"final_{data_id}.json"))
            compare_data = load_json(os.path.join(compare_dir, f"{data_id}.json"))

            position_offset = POSITION_OFFSET_LIST[data_id - 1]

            # 根据位置偏移决定A、B
            if position_offset == 1:
                record_a, record_b = simcourt_record, real_human_record
            else:
                record_a, record_b = real_human_record, simcourt_record

            # 处理该id的每个失败项
            for failed_item in items:
                stage = failed_item["stage"]
                role = failed_item["role"]
                item_name = failed_item["item"]

                print(f"  重新评估: [{stage}][{role}]{item_name}")

                # 获取item的explanation
                item_explanation = None
                for dim in EVALUATION_DIMENSIONS:
                    if dim["stage"] == stage and dim["role"] == role:
                        for name, expl in dim["items"]:
                            if name == item_name:
                                item_explanation = expl
                                break
                        break

                if item_explanation is None:
                    print(f"    警告：未找到{item_name}的解释，跳过")
                    still_failed.append(failed_item)
                    continue

                # 获取该阶段内容
                if stage == "整体偏好":
                    stage_key_list = ["trial_investigation", "presentation_evidence", "trial_debate"]
                    content_a = "\n\n".join(extract_stage_content(record_a, sk) for sk in stage_key_list)
                    content_b = "\n\n".join(extract_stage_content(record_b, sk) for sk in stage_key_list)
                else:
                    stage_key = None
                    for k, v in STAGE_MAPPING.items():
                        if v == stage:
                            stage_key = k
                            break
                    if stage_key is None:
                        print(f"    警告：未找到阶段{stage}对应的key")
                        still_failed.append(failed_item)
                        continue
                    content_a = extract_stage_content(record_a, stage_key)
                    content_b = extract_stage_content(record_b, stage_key)

                # 检查内容是否为空
                if not content_a or not content_b:
                    print(f"    警告：阶段内容为空，跳过")
                    still_failed.append(failed_item)
                    continue

                role_description = ROLE_DESCRIPTIONS.get((stage, role), "")

                # 重新评估
                result = evaluate_single_item(
                    content_a, content_b, stage, role, item_name,
                    item_explanation, role_description
                )

                if result is not None:
                    # 成功：更新compare_data
                    compare_data["data"][stage][role][item_name] = result
                    print(f"    成功: option={result['option']}")
                else:
                    # 失败：记录到still_failed
                    still_failed.append(failed_item)
                    print(f"    失败：3次重试后仍无法解析")

            # 保存更新后的compare_data
            compare_data["last_modified"] = datetime.now().isoformat()
            save_json(compare_data, os.path.join(compare_dir, f"{data_id}.json"))
            print(f"  已保存更新后的 {data_id}.json")

        except Exception as e:
            print(f"  处理data_id={data_id}时出错: {e}")
            import traceback
            traceback.print_exc()
            # 所有该项都失败
            still_failed.extend(items)

    return still_failed


def main():
    """主函数"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    failed_path = os.path.join(base_dir, "sim_human_compare", "failed.txt")
    failed_2_path = os.path.join(base_dir, "sim_human_compare", "failed_2.txt")

    if not os.path.exists(failed_path):
        print(f"错误：未找到 {failed_path}")
        return

    # 解析failed.txt
    print("解析 failed.txt...")
    failed_items = parse_failed_txt(failed_path)
    print(f"找到 {len(failed_items)} 个失败项\n")

    # 重新评估
    still_failed = reevaluate_failed_items(failed_items, base_dir)

    # 保存仍然失败的项
    if still_failed:
        with open(failed_2_path, 'w', encoding='utf-8') as f:
            f.write(f"# 重新处理后仍然失败的项 - {datetime.now().isoformat()}\n")
            f.write(f"# 总计: {len(still_failed)} 项\n\n")
            for item in still_failed:
                f.write(f"id={item['data_id']}, stage={item['stage']}, role={item['role']}, item={item['item']}, text={item.get('text', '')}\n")
        print(f"\n有 {len(still_failed)} 项仍然失败，已保存到 failed_2.txt")
    else:
        print("\n所有失败项都已成功处理！")

    print(f"\n处理完成！")
    print(f"总处理项数: {len(failed_items)}")
    print(f"成功项数: {len(failed_items) - len(still_failed)}")
    print(f"仍失败项数: {len(still_failed)}")


if __name__ == "__main__":
    main()
