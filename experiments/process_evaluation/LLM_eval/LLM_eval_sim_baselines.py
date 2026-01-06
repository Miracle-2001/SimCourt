'''
数据源输入输出：
庭审记录的来源是：
1. ../AgentCourt里面的final_1.json~final_50.json
2. ../AgentCourts里面的final_1.json~final_50.json
3. ../simcourt_only_debate 里面的final_1.json~final_50.json

你要比较1和3的1~50，比较结果放到 ./LLM_eval下的sim_AgentCourt_compare
还要比较2和3的1~50，比较结果放到 ./LLM_eval下的sim_AgentsCourt_compare

仅关注法庭辩论阶段中，公诉人和辩护人的表现就可以了！（也就是只有2x3=6项，而不是30项）
你不需要特别提取这个阶段的庭审内容，给你的数据源里面的文件里面就只包含法庭辩论阶段的内容了。

不需要进行A，B位置的随机调换翻转，一直让simcourt_only_debate里面的在A，然后AgentCourt和AgentsCourt在B就行了。

注意编号代表庭审记录的编号，是对应的。所以应该是1号里面的final_1.json和2里面的final_1.json进行比较，而不是别的。

'''

# ============================================================================
# 以下是实现的代码
# ============================================================================

import json
import os
import openai
from tqdm import tqdm
from datetime import datetime
import re

# 反思检查开关：是否对评价结果进行反思检查（验证option和理由是否匹配）
# 默认为False，不开启反思检查
ENABLE_REFLECTION_CHECK = False

# 评价维度定义：仅关注法庭辩论阶段的公诉人和辩护人（2x3=6项）
EVALUATION_DIMENSIONS = [
    # 法庭辩论环节 - 公诉人
    {"stage": "法庭辩论环节", "role": "公诉人", "description": "说理是否充分，攻防是否聚焦", "items": [
        ("指控逻辑性强", "公诉方论证是否内部一致且具有法律结构"),
        ("法律引用精确", "是否正确且相关地引用法律权威来支持论证"),
        ("回应辩护有力", "公诉人是否以清晰和有力的方式回应并反驳辩护人的主张")
    ]},
    # 法庭辩论环节 - 辩护人
    {"stage": "法庭辩论环节", "role": "辩护人", "description": "避免过度废话，兼顾法律与人性表达", "items": [
        ("辩点清晰", "辩护论点是否清晰表达且逻辑发展"),
        ("法律逻辑严密", "法律推理是否精确、内部一致且法律上合理"),
        ("情理表达得体", "论证是否平衡法理推理与适当的情感共鸣")
    ]}
]

# 数据源配置
DATA_SOURCES = [
    {
        "name": "AgentCourt",
        "dir": "../AgentCourt",
        "output_dir": "sim_AgentCourt_compare"
    },
    {
        "name": "AgentsCourt",
        "dir": "../AgentCourts",
        "output_dir": "sim_AgentsCourt_compare"
    }
]


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


def extract_debate_content(trial_record: dict) -> str:
    """
    从庭审记录中提取法庭辩论阶段的内容
    注意：数据源文件里面就只包含法庭辩论阶段的内容

    Args:
        trial_record: 庭审记录字典

    Returns:
        该阶段所有发言内容的拼接字符串
    """
    # 数据源文件中的key可能是trial_debate，或者直接包含speeches列表
    if "trial_debate" in trial_record:
        speeches = trial_record["trial_debate"]
    elif isinstance(trial_record, list):
        speeches = trial_record
    elif "speeches" in trial_record:
        speeches = trial_record["speeches"]
    else:
        # 尝试直接使用整个记录
        speeches = trial_record if isinstance(trial_record, list) else []

    content_list = []
    for speech in speeches:
        if isinstance(speech, dict):
            content_list.append(speech.get("content", ""))
        elif isinstance(speech, str):
            content_list.append(speech)

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
    # 构建评价维度的详细说明
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

    # 构建输出格式示例
    if len(items) == 1:
        # 整体评价只有一个维度
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
    # 尝试提取JSON部分
    json_match = re.search(r'\{.*\}', response, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

    # 如果解析失败，返回默认值
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
    # 构建当前结果的总结
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
        # 调用模型进行反思检查
        reflection_response = query_model(instruction, reflection_prompt)

        # 解析反思结果
        json_match = re.search(r'\{.*\}', reflection_response, re.DOTALL)
        if json_match:
            reflection_result = json.loads(json_match.group())

            # 如果所有正确，直接返回原结果
            if reflection_result.get("all_correct") == True:
                print(f"    反思检查：所有项的选项和理由匹配一致")
                return parsed_result

            # 应用修正
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


def convert_result_to_final_format(result: dict) -> dict:
    """
    将评价结果转换为最终格式
    注意：不需要位置偏移转换，因为A始终是simcourt_only_debate，B始终是baseline

    Args:
        result: 原始评价结果

    Returns:
        转换后的结果（A=simcourt_only_debate, B=baseline）
    """
    # 不需要转换，直接返回
    return result


def evaluate_one_pair(record_a: dict, record_b: dict, data_id: int, baseline_name: str) -> dict:
    """
    评价一对庭审记录
    注意：A始终是simcourt_only_debate，B始终是baseline（AgentCourt或AgentsCourt）

    Args:
        record_a: 记录A（simcourt_only_debate）
        record_b: 记录B（baseline - AgentCourt或AgentsCourt）
        data_id: 数据编号
        baseline_name: baseline名称（"AgentCourt"或"AgentsCourt"）

    Returns:
        完整的评价结果字典（A=simcourt_only_debate, B=baseline）
    """
    result = {
        "data": {},
        "last_modified": datetime.now().isoformat(),
        "username": "llm_evaluator",
        "data_id": data_id
    }

    # 系统指令
    instruction = f"""你是一个专业的庭审评价专家，具有丰富的刑事诉讼庭审经验。
你需要客观、公正地评价两份庭审记录中公诉人和辩护人在法庭辩论阶段的表现。
请按照给定的评价维度，仔细对比分析，给出准确的偏好性判断和理由。"""

    # 提取辩论内容（数据源文件只包含辩论阶段）
    content_a = extract_debate_content(record_a)
    content_b = extract_debate_content(record_b)

    # 检查内容是否为空
    if not content_a:
        print(f"  警告：记录A的辩论内容为空")
    if not content_b:
        print(f"  警告：记录B的辩论内容为空")

    # 统计需要评价的阶段数量（只有法庭辩论环节的2个角色）
    total_stages = len(EVALUATION_DIMENSIONS)

    for idx, dim in enumerate(EVALUATION_DIMENSIONS, 1):
        stage = dim["stage"]
        role = dim["role"]
        items = dim["items"]  # 现在是(item_name, item_explanation)的列表
        role_desc = dim["description"]

        print(f"  [{idx}/{total_stages}] 正在评价: {stage} - {role}")

        # 初始化该阶段该角色的结果
        if stage not in result["data"]:
            result["data"][stage] = {}
        if role not in result["data"][stage]:
            result["data"][stage][role] = {}

        # 构建prompt并调用模型
        prompt = build_evaluation_prompt(content_a, content_b, stage, role, items, role_desc)

        # 重试机制：最多尝试3次
        max_retries = 3
        parsed_result = None
        last_error = None
        response = ""

        for retry_count in range(max_retries):
            try:
                if retry_count > 0:
                    # 重试时添加强调格式的提示
                    retry_prompt = prompt + "\n\n【重要提醒】：请务必严格按照JSON格式输出，不要包含任何其他文字说明！"
                    response = query_model(instruction, retry_prompt)
                    print(f"    第{retry_count + 1}次尝试（强调格式）...")
                else:
                    response = query_model(instruction, prompt)

                parsed_result = parse_model_response(response, items)

                # 检查是否解析成功（所有item都有返回）
                all_present = all(item_name in parsed_result for item_name, _ in items)
                if all_present:
                    break  # 解析成功，退出重试循环
                else:
                    # 有缺失项，继续重试
                    missing = [item_name for item_name, _ in items if item_name not in parsed_result]
                    print(f"    第{retry_count + 1}次解析不完整，缺失: {missing}")

            except Exception as e:
                last_error = e
                print(f"    第{retry_count + 1}次尝试出错: {e}")
                parsed_result = None

        # 如果3次都失败，记录到failed.txt并填充默认值
        if parsed_result is None or not all(item_name in parsed_result for item_name, _ in items):
            failed_log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "failed.txt")
            with open(failed_log_path, 'a', encoding='utf-8') as f:
                f.write(f"data_id={data_id}, baseline={baseline_name}, stage={stage}, role={role}, error={str(last_error)}\n")
            print(f"  警告：{max_retries}次尝试均失败，已记录到failed.txt")

            # 填充默认值
            parsed_result = {}
            for item_name, _ in items:
                if item_name not in parsed_result:
                    parsed_result[item_name] = {"option": "C", "text": f"解析失败（{max_retries}次重试）"}

        # 反思检查：验证option和理由是否匹配（根据开关决定是否启用）
        if ENABLE_REFLECTION_CHECK:
            parsed_result = reflect_and_correct_result(parsed_result, items, response, instruction, stage, role)

        # 将结果添加到总结果中
        for item_name, _ in items:
            if item_name in parsed_result:
                result["data"][stage][role][item_name] = parsed_result[item_name]
            else:
                result["data"][stage][role][item_name] = {"option": "C", "text": "模型未返回该维度"}

    # 转换为最终格式（A=simcourt_only_debate, B=baseline）
    result = convert_result_to_final_format(result)

    return result


def main():
    """
    主函数：执行批量评价
    对两个baseline（AgentCourt和AgentsCourt）分别与simcourt_only_debate进行比较
    """
    # 定义路径
    base_dir = os.path.dirname(os.path.abspath(__file__))
    simcourt_debate_dir = os.path.join(base_dir, "..", "simcourt_only_debate")

    # 遍历每个数据源
    for source_config in DATA_SOURCES:
        baseline_name = source_config["name"]
        baseline_dir = os.path.join(base_dir, source_config["dir"])
        output_dir = os.path.join(base_dir, source_config["output_dir"])

        print(f"\n{'='*60}")
        print(f"开始处理: {baseline_name} vs simcourt_only_debate")
        print(f"{'='*60}\n")

        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)

        # 检查目录是否存在
        if not os.path.exists(simcourt_debate_dir):
            print(f"错误：目录不存在 {simcourt_debate_dir}")
            continue
        if not os.path.exists(baseline_dir):
            print(f"错误：目录不存在 {baseline_dir}")
            continue

        # 获取所有文件编号
        simcourt_files = sorted([f for f in os.listdir(simcourt_debate_dir) if f.startswith("final_") and f.endswith(".json")],
                                key=lambda x: int(x.replace("final_", "").replace(".json", "")))
        simcourt_ids = set(int(f.replace("final_", "").replace(".json", "")) for f in simcourt_files)

        baseline_files = sorted([f for f in os.listdir(baseline_dir) if f.startswith("final_") and f.endswith(".json")],
                               key=lambda x: int(x.replace("final_", "").replace(".json", "")))
        baseline_ids = set(int(f.replace("final_", "").replace(".json", "")) for f in baseline_files)

        print(f"找到 {len(simcourt_ids)} 个simcourt_only_debate文件")
        print(f"找到 {len(baseline_ids)} 个{baseline_name}文件")

        # 找出共同编号的文件
        common_ids = sorted([cid for cid in simcourt_ids if cid in baseline_ids])

        print(f"共有 {len(common_ids)} 对文件需要评价\n")

        # 遍历每对文件进行评价
        for data_id in tqdm(common_ids, desc=f"{baseline_name} 评价进度"):
            simcourt_path = os.path.join(simcourt_debate_dir, f"final_{data_id}.json")
            baseline_path = os.path.join(baseline_dir, f"final_{data_id}.json")

            # 加载记录
            try:
                record_simcourt = load_trial_record(simcourt_path)
                record_baseline = load_trial_record(baseline_path)

                print(f"\n正在评价 data_id={data_id}...")
                print(f"  A位置: simcourt_only_debate, B位置: {baseline_name}")

                # 进行评价（A=simcourt_only_debate, B=baseline）
                result = evaluate_one_pair(record_simcourt, record_baseline, data_id, baseline_name)

                # 保存结果
                output_path = os.path.join(output_dir, f"{data_id}.json")
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)

                print(f"已保存评价结果到 {output_path}")

            except Exception as e:
                print(f"处理 data_id={data_id} 时出错: {e}")
                import traceback
                traceback.print_exc()

        print(f"\n{baseline_name} 评价完成！结果保存在 {output_dir} 目录")

    print(f"\n{'='*60}")
    print("所有评价任务完成！")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
