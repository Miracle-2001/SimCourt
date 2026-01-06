
import json
import os
import openai
from tqdm import tqdm
from datetime import datetime
import re

POSITION_OFFSET_LIST = [1, -1, 1, 1, -1, -1, -1, 1, 1, -1, 1, -1, -1, 1, 1, -1, 1, -1, -1, 1,
                        1, -1, 1, -1, -1, 1, -1, 1, -1, 1, -1, -1, 1, -1, 1, -1, 1, 1, -1, 1,
                        -1, 1, -1, -1, 1, -1, 1, -1, 1, -1]

ENABLE_REFLECTION_CHECK = True

EVALUATION_DIMENSIONS = [

    {"stage": "法庭调查", "role": "审判长", "description": "是否合乎程序逻辑，引导顺畅，未偏袒任何一方", "items": [
        ("引导结构清晰性", "法官是否以清晰、逻辑且循序渐进的方式构建法庭提问结构"),
        ("中立性与流程控制", "法官是否保持中立并确保程序流程顺畅"),
        ("证据审查是否专业", "法官是否以法律专业知识处理证据问题并遵守程序规范")
    ]},

    {"stage": "法庭调查", "role": "公诉人", "description": "能否突出关键事实，问题设计是否合规", "items": [
        ("讯问策略合理", "公诉人是否使用合法且有明确目标的讯问策略"),
        ("重点突出、语言专业", "公诉人在讯问中是否使用准确且专业的法律语言"),
        ("证据引导合法性", "公诉人的提问是否符合证据和程序规则")
    ]},

    {"stage": "法庭调查", "role": "辩护人", "description": "是否积极为被告发声，避免走过场式辩护", "items": [
        ("提问针对性强", "辩护人是否提出聚焦且与法律相关的问题"),
        ("合法程序敏感性高", "辩护人是否对程序合法性和司法规范表现出敏感度"),
        ("保护当事人权益意识", "辩护人是否积极维护和主张被告人的程序性和实质性权利")
    ]},

    {"stage": "举证质证环节", "role": "审判长", "description": "能否保障双方有效开展质证", "items": [
        ("主持规范性", "法官是否按照法律标准和法庭礼仪主持庭审程序"),
        ("质证合法性控制", "法官是否确保交叉询问符合法律规则和证据边界"),
        ("公平保障意识", "法官是否维护公诉人和辩护人之间的公平和平等")
    ]},

    {"stage": "举证质证环节", "role": "公诉人", "description": "对辩方质疑反应是否有理有力", "items": [
        ("证据叙述准确", "公诉人是否清晰、准确且无歪曲地呈现证据"),
        ("攻击力适度", "公诉人是否在没有不当敌意或不当压力的情况下保持说服力"),
        ("对异议回应得体", "公诉人是否以充分的法律依据和程序恰当性回应辩护人的异议")
    ]},

    {"stage": "举证质证环节", "role": "辩护人", "description": "回应是否具体、专业、有影响力", "items": [
        ("提出质疑抓住关键", "辩护人是否识别并质疑公诉方案件的核心问题"),
        ("证据辨析严谨", "辩护人是否对证据提供逻辑结构化且彻底的分析"),
        ("应对检方证据有效", "辩护人是否有说服力地驳斥、解释或中和公诉方的证据")
    ]},

    {"stage": "法庭辩论环节", "role": "审判长", "description": "不偏袒，适时引导，维持理性气氛", "items": [
        ("引导对抗焦点清晰", "法官是否恰当地识别和界定法律争议的焦点"),
        ("不偏不倚发言介入", "法官的口头介入是否保持中立和程序公平"),
        ("控制节奏与秩序", "法官是否有效管理庭审的节奏和纪律")
    ]},

    {"stage": "法庭辩论环节", "role": "公诉人", "description": "说理是否充分，攻防是否聚焦", "items": [
        ("指控逻辑性强", "公诉方论证是否内部一致且具有法律结构"),
        ("法律引用精确", "是否正确且相关地引用法律权威来支持论证"),
        ("回应辩护有力", "公诉人是否以清晰和有力的方式回应并反驳辩护人的主张")
    ]},

    {"stage": "法庭辩论环节", "role": "辩护人", "description": "避免过度废话，兼顾法律与人性表达", "items": [
        ("辩点清晰", "辩护论点是否清晰表达且逻辑发展"),
        ("法律逻辑严密", "法律推理是否精确、内部一致且法律上合理"),
        ("情理表达得体", "论证是否平衡法理推理与适当的情感共鸣")
    ]},

    {"stage": "整体偏好", "role": "审判长", "description": "要确保庭审程序公正，应当保障犯罪嫌疑人和其他诉讼参与人依法享有的辩护权和其他诉讼权利。", "items": [
        ("整体表现", "法官的整体表现")
    ]},
    {"stage": "整体偏好", "role": "公诉人", "description": "保证准确、及时地查明犯罪事实，正确应用法律，惩罚犯罪分子，保障无罪的人不受刑事追究。", "items": [
        ("整体表现", "公诉人的整体表现")
    ]},
    {"stage": "整体偏好", "role": "辩护人", "description": "根据事实和法律，提出犯罪嫌疑人、被告人无罪、罪轻或者减轻、免除其刑事责任的材料和意见，维护犯罪嫌疑人、被告人的诉讼权利和其他合法权益。", "items": [
        ("整体表现", "辩护人的整体表现")
    ]}
]


STAGE_MAPPING = {
    "trial_investigation": "法庭调查",
    "presentation_evidence": "举证质证环节",
    "trial_debate": "法庭辩论环节"
}


def query_model(instruction: str, prompt: str, temperature: float = 0.7, max_tokens: int = 64000) -> str:
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
    return response.choices[0].message.content


def load_trial_record(file_path: str) -> dict:
    """
    加载庭审记录JSON文件

    Args:
        file_path: 文件路径

    Returns:
        庭审记录字典
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def extract_stage_content(trial_record: dict, stage_key: str) -> str:
    """
    从庭审记录中提取指定阶段的内容

    Args:
        trial_record: 庭审记录字典
        stage_key: 阶段key（trial_investigation, presentation_evidence, trial_debate）

    Returns:
        该阶段所有发言内容的拼接字符串
    """
    if stage_key not in trial_record:
        return ""

    speeches = trial_record[stage_key]
    content_list = []
    for speech in speeches:
        content_list.append(speech.get("content", ""))

    return "\n".join(content_list)


def build_evaluation_prompt(stage_content_a: str, stage_content_b: str, stage_name: str, role: str,
                           items: list, role_description: str) -> str:
    """
    构建评价prompt

    Args:
        stage_content_a: 记录A的该阶段内容
        stage_content_b: 记录B的该阶段内容
        stage_name: 阶段名称
        role: 角色
        items: 评价项列表，每项是(item_name, item_explanation)的元组
        role_description: 角色描述

    Returns:
        完整的prompt字符串
    """

    items_description = ""
    for i, (item_name, item_explanation) in enumerate(items, 1):
        items_description += f"\n{i}. **{item_name}**：{item_explanation}"

    prompt = f"""你是一个专业的庭审评价专家。现在需要你对两份庭审记录在【{stage_name}】阶段【{role}】的表现进行比较评价。

【{role}在{stage_name}中的职责说明】：
{role_description}

【评价要求】：
1. 请忽略语癖、小范围复读等习惯，多关注内容实质。
2. 分要点评价，避免宏观评价。
3. 对于每个评价维度，请仔细对比两份记录，给出你认为表现更好的一方。
4. 评价结果说明：
   - 如果记录A（第一份记录）表现更好，请输出：A
   - 如果记录B（第二份记录）表现更好，请输出：B
   - 如果无法区分/两者相当，请输出：C
5. 特别地，如果某一个记录里面没有体现相应内容，而另一个记录里有相应内容，那么应该认为另外一个记录更优秀！
6. 特别地，如果两份记录里面都没有体现相应内容，那么应该输出C
6. 对每个评价维度，请详细说明理由！尽量稍微多一些。

【两份庭审记录的{stage_name}阶段内容如下】：

===== 记录A =====
{stage_content_a[:5000]}

===== 记录B =====
{stage_content_b[:5000]}

===== 评价维度及详细说明 =====
请对以下{len(items)}个维度分别进行评价：
{items_description}
"""


    if len(items) == 1:

        item_name = items[0][0]
        prompt += f"""

【输出格式要求】：
请严格按照以下JSON格式输出，不要包含任何其他文字：
{{"{item_name}": {{"option": "A/B/C", "text": "简要理由"}}}}

请直接输出JSON，不要有任何其他解释。
"""
    else:
        item_names = [item[0] for item in items]
        prompt += f"""

【输出格式要求】：
请严格按照以下JSON格式输出，不要包含任何其他文字：
{{"{item_names[0]}": {{"option": "A/B/C", "text": "简要理由"}}, "{item_names[1]}": {{"option": "A/B/C", "text": "简要理由"}}, "{item_names[2]}": {{"option": "A/B/C", "text": "简要理由"}}}}

请直接输出JSON，不要有任何其他解释。
"""

    return prompt


def parse_model_response(response: str, items: list) -> dict:
    """
    解析模型返回的JSON响应

    Args:
        response: 模型返回的字符串
        items: 评价项列表，每项是(item_name, item_explanation)的元组

    Returns:
        解析后的字典
    """

    json_match = re.search(r'\{.*\}', response, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass


    result = {}
    for item_name, _ in items:
        result[item_name] = {"option": "C", "text": "解析失败，默认为C"}
    return result


def reflect_and_correct_result(parsed_result: dict, items: list, original_response: str,
                               instruction: str, stage: str, role: str) -> dict:
    """
    反思检查：验证option和理由是否匹配，如果不匹配则修正

    Args:
        parsed_result: 解析后的评价结果字典
        items: 评价项列表，每项是(item_name, item_explanation)的元组
        original_response: 模型原始响应
        instruction: 系统指令
        stage: 阶段名称
        role: 角色名称

    Returns:
        修正后的评价结果字典
    """

    result_summary = []
    for item_name, _ in items:
        if item_name in parsed_result:
            option = parsed_result[item_name].get("option", "C")
            text = parsed_result[item_name].get("text", "")
            result_summary.append(f"- {item_name}: 选项={option}, 理由={text}")

    reflection_prompt = f"""你是一个专业的庭审评价质量检查专家。现在需要对刚才生成的评价结果进行反思检查。

【原始评价结果】：
{chr(10).join(result_summary)}

【检查要求】：
请仔细检查每个评价维度的"选项"和"理由"是否匹配一致：

1. 如果理由明确指出记录A表现更好（如提到"A更..."、"A优势..."、"记录A的..."等），但选项是B或C，则需要将选项改为A
2. 如果理由明确指出记录B表现更好（如提到"B更..."、"B优势..."、"记录B的..."等），但选项是A或C，则需要将选项改为B
3. 如果理由认为两者相当或无法区分（如提到"相当"、"差不多"、"各有优劣"、"都不突出"等），但选项是A或B，则需要将选项改为C
4. 如果理由模糊不清但给出了倾向性判断，请根据理由的实际倾向来修正选项

【重要说明】：
- 选项A表示记录A（第一份记录）更好
- 选项B表示记录B（第二份记录）更好
- 选项C表示两者相当或无法区分
- 请务必以"理由"的实际内容为准，而不是原"选项"为准

【输出格式要求】：
请严格按照以下JSON格式输出修正后的结果（仅输出有误需要修正的项，如果某项正确则不输出）：
{{"item1": {{"option": "修正后的选项", "text": "原理由保持不变"}}, "item2": {{"option": "修正后的选项", "text": "原理由保持不变"}}}}

如果所有项目的选项和理由都匹配一致，请输出：{{"all_correct": true}}

请直接输出JSON，不要有任何其他解释。"""

    try:

        reflection_response = query_model(instruction, reflection_prompt)


        json_match = re.search(r'\{.*\}', reflection_response, re.DOTALL)
        if json_match:
            reflection_result = json.loads(json_match.group())


            if reflection_result.get("all_correct") == True:
                print(f"    反思检查：所有项的选项和理由匹配一致")
                return parsed_result


            corrected_items = []
            for item_name, _ in items:
                if item_name in reflection_result:
                    old_option = parsed_result[item_name].get("option", "C")
                    new_option = reflection_result[item_name].get("option", "C")
                    if old_option != new_option:
                        parsed_result[item_name]["option"] = new_option
                        corrected_items.append(f"{item_name}: {old_option}->{new_option}")

            if corrected_items:
                print(f"    反思检查：修正了{len(corrected_items)}项 - {', '.join(corrected_items)}")
            else:
                print(f"    反思检查：无需修正")

        return parsed_result

    except Exception as e:
        print(f"    反思检查出错: {e}，保持原结果")
        return parsed_result


def convert_result_to_final_format(result: dict, position_offset: int) -> dict:
    """
    将评价结果转换为最终格式（考虑位置偏移）

    Args:
        result: 原始评价结果
        position_offset: 位置偏移，1表示simcourt在前(A)，-1表示real_human在前(A)

    Returns:
        转换后的结果
    """


    if position_offset == -1:

        for stage in result.get("data", {}):
            for role in result["data"][stage]:
                for item in result["data"][stage][role]:
                    option = result["data"][stage][role][item]["option"]
                    if option == "A":
                        result["data"][stage][role][item]["option"] = "B"
                    elif option == "B":
                        result["data"][stage][role][item]["option"] = "A"

    return result


def evaluate_one_pair(record_a: dict, record_b: dict, data_id: int, position_offset: int) -> dict:
    """
    评价一对庭审记录

    Args:
        record_a: 记录A（根据position_offset决定是simcourt还是real_human）
        record_b: 记录B（根据position_offset决定是simcourt还是real_human）
        data_id: 数据编号
        position_offset: 位置偏移，1表示simcourt在A位置，-1表示real_human在A位置

    Returns:
        完整的评价结果字典（已转换为最终格式，A=simcourt, B=real_human）
    """
    result = {
        "data": {},
        "last_modified": datetime.now().isoformat(),
        "username": "llm_evaluator",
        "data_id": data_id
    }


    instruction = """你是一个专业的庭审评价专家，具有丰富的刑事诉讼庭审经验。
你需要客观、公正地评价两份庭审记录中法官、公诉人、辩护人在各个阶段的表现。
请按照给定的评价维度，仔细对比分析，给出准确的偏好性判断和理由。"""


    total_stages = len(EVALUATION_DIMENSIONS)

    for idx, dim in enumerate(EVALUATION_DIMENSIONS, 1):
        stage = dim["stage"]
        role = dim["role"]
        items = dim["items"]  
        role_desc = dim["description"]

        print(f"  [{idx}/{total_stages}] 正在评价: {stage} - {role}")


        if stage not in result["data"]:
            result["data"][stage] = {}
        if role not in result["data"][stage]:
            result["data"][stage][role] = {}


        if stage == "整体偏好":

            stage_key_list = ["trial_investigation", "presentation_evidence", "trial_debate"]
            content_a_parts = []
            content_b_parts = []
            for sk in stage_key_list:
                content_a_parts.append(extract_stage_content(record_a, sk))
                content_b_parts.append(extract_stage_content(record_b, sk))
            content_a = "\n\n".join(content_a_parts)
            content_b = "\n\n".join(content_b_parts)
        else:

            stage_key = None
            for k, v in STAGE_MAPPING.items():
                if v == stage:
                    stage_key = k
                    break

            if stage_key is None:
                print(f"  警告：未找到阶段 {stage} 对应的key")
                continue

            content_a = extract_stage_content(record_a, stage_key)
            content_b = extract_stage_content(record_b, stage_key)


        prompt = build_evaluation_prompt(content_a, content_b, stage, role, items, role_desc)


        max_retries = 3
        parsed_result = None
        last_error = None

        for retry_count in range(max_retries):
            try:
                if retry_count > 0:

                    retry_prompt = prompt + "\n\n【重要提醒】：请务必严格按照JSON格式输出，不要包含任何其他文字说明！"
                    response = query_model(instruction, retry_prompt)
                    print(f"    第{retry_count + 1}次尝试（强调格式）...")
                else:
                    response = query_model(instruction, prompt)

                parsed_result = parse_model_response(response, items)


                all_present = all(item_name in parsed_result for item_name, _ in items)
                if all_present:
                    break  
                else:

                    missing = [item_name for item_name, _ in items if item_name not in parsed_result]
                    print(f"    第{retry_count + 1}次解析不完整，缺失: {missing}")

            except Exception as e:
                last_error = e
                print(f"    第{retry_count + 1}次尝试出错: {e}")
                parsed_result = None


        if parsed_result is None or not all(item_name in parsed_result for item_name, _ in items):
            failed_log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "failed.txt")
            with open(failed_log_path, 'a', encoding='utf-8') as f:
                f.write(f"data_id={data_id}, stage={stage}, role={role}, error={str(last_error)}\n")
            print(f"  警告：{max_retries}次尝试均失败，已记录到failed.txt")


            parsed_result = {}
            for item_name, _ in items:
                if item_name not in parsed_result:
                    parsed_result[item_name] = {"option": "C", "text": f"解析失败（{max_retries}次重试）"}


        if ENABLE_REFLECTION_CHECK:
            parsed_result = reflect_and_correct_result(parsed_result, items, response, instruction, stage, role)


        for item_name, _ in items:
            if item_name in parsed_result:
                result["data"][stage][role][item_name] = parsed_result[item_name]
            else:
                result["data"][stage][role][item_name] = {"option": "C", "text": "模型未返回该维度"}


    result = convert_result_to_final_format(result, position_offset)

    return result


def main():
    """
    主函数：执行批量评价
    """

    base_dir = os.path.dirname(os.path.abspath(__file__))
    simcourt_dir = os.path.join(base_dir, "..", "simcourt")
    real_human_dir = os.path.join(base_dir, "..", "real_human", "output")
    output_dir = os.path.join(base_dir, "sim_human_compare")


    os.makedirs(output_dir, exist_ok=True)



    simcourt_files = sorted([f for f in os.listdir(simcourt_dir) if f.startswith("final_") and f.endswith(".json")],
                            key=lambda x: int(x.replace("final_", "").replace(".json", "")))
    simcourt_ids = set(int(f.replace("final_", "").replace(".json", "")) for f in simcourt_files)

    real_human_files = sorted([f for f in os.listdir(real_human_dir) if f.startswith("final_") and f.endswith(".json")],
                             key=lambda x: int(x.replace("final_", "").replace(".json", "")))
    real_human_ids = set(int(f.replace("final_", "").replace(".json", "")) for f in real_human_files)

    print(f"找到 {len(simcourt_ids)} 个simcourt文件")
    print(f"找到 {len(real_human_ids)} 个real_human文件")


    common_ids = sorted([cid for cid in simcourt_ids if cid in real_human_ids])

    print(f"共有 {len(common_ids)} 对文件需要评价\n")


    for data_id in tqdm(common_ids, desc="评价进度"):
        simcourt_path = os.path.join(simcourt_dir, f"final_{data_id}.json")
        real_human_path = os.path.join(real_human_dir, f"final_{data_id}.json")


        position_offset = POSITION_OFFSET_LIST[data_id - 1]


        try:
            record_simcourt = load_trial_record(simcourt_path)
            record_real_human = load_trial_record(real_human_path)

            print(f"\n正在评价 data_id={data_id}... (位置偏移: {position_offset})")


            if position_offset == 1:

                record_a = record_simcourt
                record_b = record_real_human
                print(f"  A位置: simcourt, B位置: real_human")
            else:

                record_a = record_real_human
                record_b = record_simcourt
                print(f"  A位置: real_human, B位置: simcourt")


            result = evaluate_one_pair(record_a, record_b, data_id, position_offset)


            output_path = os.path.join(output_dir, f"{data_id}.json")
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)

            print(f"已保存评价结果到 {data_id}.json")

        except Exception as e:
            print(f"处理 data_id={data_id} 时出错: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n评价完成！结果保存在 {output_dir} 目录")


if __name__ == "__main__":
    main()
