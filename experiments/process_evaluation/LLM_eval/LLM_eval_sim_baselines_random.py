'''
数据源输入输出：
庭审记录的来源是：
1. ../AgentCourt里面的final_1.json~final_50.json
2. ../AgentsCourt里面的final_1.json~final_50.json
3. ../simcourt_only_debate 里面的final_1.json~final_50.json

你要比较1和3的1~50，比较结果放到 ./LLM_eval下的sim_AgentCourt_compare
还要比较2和3的1~50，比较结果放到 ./LLM_eval下的sim_AgentsCourt_compare

仅关注法庭辩论阶段中，公诉人和辩护人的表现就可以了！（也就是只有2x3=6项，而不是30项）
你不需要特别提取这个阶段的庭审内容，给你的数据源里面的文件里面就只包含法庭辩论阶段的内容了。

【特别说明】
1.因为simcourt和另外一个（AgentCourt或AgentsCourt）总有一个要在A位置，另外一个在B位置，所以为了防止位置带来的影响，你要有时候把simcourt放在A，另一个放在B，有时候要把simcourt放在B，另一个放在A。
放置规则是：
[1, -1, 1, 1, -1, 1, -1, -1, -1, 1, -1, 1, 1, -1, -1, 1, 1, 1, -1, -1, -1, 1, 1, -1, -1, -1, 1, 1, 1, -1, 1, -1, -1, -1, 1, 1, -1, 1, 1, 1, -1, -1, 1, -1, -1, -1, 1, 1, -1, 1]
这个长度为50的list里面，下标从0~49，对应案件的id是1~50（偏移一位），如果某个位置是1，那么对应的两份庭审记录中，来自simcourt的放到a的位置（前一个的位置），来自另外一个的的放到b的位置（后一个的位置）；如果是-1，那么情况则反过来。

2.一次性评价太多维度会导致大模型评价失败，所以你要一个一个评价这些维度。（一共每个id也就6项，你要调用6次）。如果失败了的话再尝试一次，还是失败就保存到failed.txt里面（这个failed.txt放到和输出结果同目录中，也就是sim_AgentCourt_compare或者sim_AgentsCourt_compare）

3.注意编号代表庭审记录的编号，是对应的。所以应该是1号里面的final_1.json和2里面的final_1.json进行比较，而不是别的。

4.让大模型给的评价理由尽量详细一些。

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
ENABLE_REFLECTION_CHECK = True

# 评价维度定义：仅关注法庭辩论阶段的公诉人和辩护人（2x3=6项）
# 每个维度单独评价，items列表中每个元素是(item_name, item_explanation)的元组
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

# 【特别说明】位置随机化规则列表
# 下标0~49对应案件id 1~50，1表示simcourt在A位置，-1表示simcourt在B位置
POSITION_RULE = [1, -1, 1, 1, -1, 1, -1, -1, -1, 1, -1, 1, 1, -1, -1, 1, 1, 1, -1, -1, -1, 1, 1, -1, -1, -1, 1, 1, 1, -1, 1, -1, -1, -1, 1, 1, -1, 1, 1, 1, -1, -1, 1, -1, -1, -1, 1, 1, -1, 1]

# 数据源配置
DATA_SOURCES = [
    {
        "name": "AgentCourt",
        "dir": "../AgentCourt",
        "output_dir": "sim_AgentCourt_compare"
    },
    {
        "name": "AgentsCourt",
        "dir": "../AgentsCourt",
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
                           item_name: str, item_explanation: str, role_description: str) -> str:
    """
    构建评价prompt - 每次只评价一个维度

    Args:
        stage_content_a: 记录A的该阶段内容
        stage_content_b: 记录B的该阶段内容
        stage_name: 阶段名称
        role: 角色
        item_name: 评价项名称
        item_explanation: 评价项说明
        role_description: 角色描述

    Returns:
        完整的prompt字符串
    """
    prompt = f"""你是一个专业的庭审评价专家。现在需要你对两份庭审记录在【{stage_name}】阶段【{role}】的表现进行比较评价。

【{role}在{stage_name}中的职责说明】：
{role_description}

【当前评价维度】：
**{item_name}**：{item_explanation}

【评价要求】：
1. 请忽略语癖、小范围复读等习惯，多关注内容实质。
2. 请仔细对比两份记录，仅针对上述"【当前评价维度】"进行评价。
3. 评价结果说明：
   - 如果记录A（第一份记录）表现更好，请输出：A
   - 如果记录B（第二份记录）表现更好，请输出：B
   - 如果无法区分/两者相当，请输出：C
4. 特别地，如果某一个记录里面没有体现相应内容，而另一个记录里有相应内容，那么应该认为另外一个记录更优秀！
5. 特别地，如果两份记录里面都没有体现相应内容，那么应该输出C
6. 请详细说明评价理由，尽量多一些，从多个角度分析。

【两份庭审记录的{stage_name}阶段内容如下】：

===== 记录A =====
{stage_content_a[:5000]}

===== 记录B =====
{stage_content_b[:5000]}

【输出格式要求】：
请严格按照以下JSON格式输出，不要包含任何其他文字：
{{"{item_name}": {{"option": "A/B/C", "text": "详细的评价理由"}}}}

请直接输出JSON，不要有任何其他解释。
"""

    return prompt


def parse_model_response(response: str, item_name: str) -> dict:
    """
    解析模型返回的JSON响应 - 单项评价

    Args:
        response: 模型返回的字符串
        item_name: 评价项名称

    Returns:
        解析后的字典，格式: {item_name: {"option": "A/B/C", "text": "理由"}}
    """
    # 尝试提取JSON部分
    json_match = re.search(r'\{.*\}', response, re.DOTALL)
    if json_match:
        try:
            parsed = json.loads(json_match.group())
            if item_name in parsed:
                return parsed
        except json.JSONDecodeError:
            pass

    # 如果解析失败，返回默认值
    return {item_name: {"option": "C", "text": "解析失败，默认为C"}}


def reflect_and_correct_result(parsed_result: dict, item_name: str, instruction: str) -> dict:
    """
    反思检查：根据理由重新选择option，不依赖原始option

    Args:
        parsed_result: 解析后的评价结果字典
        item_name: 评价项名称
        instruction: 系统指令

    Returns:
        修正后的评价结果字典
    """
    if item_name not in parsed_result:
        return parsed_result

    text = parsed_result[item_name].get("text", "")

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
        # 调用模型进行反思检查
        new_option = query_model(instruction, reflection_prompt)

        # 清理结果，取第一个字符
        new_option = new_option.strip().upper()
        if new_option and new_option[0] in ["A", "B", "C"]:
            actual_option = new_option[0]
            old_option = parsed_result[item_name].get("option", "C")
            parsed_result[item_name]["option"] = actual_option
            if old_option != actual_option:
                print(f"    反思检查：修正选项 {old_option}->{actual_option}")
            else:
                print(f"    反思检查：选项一致 {actual_option}")
        else:
            print(f"    模型返回异常: {new_option}")
        return parsed_result

    except Exception as e:
        print(f"    反思检查出错: {e}，保持原结果")
        return parsed_result


def convert_result_to_final_format(result: dict, simcourt_is_a: bool) -> dict:
    """
    将评价结果转换为最终格式
    根据simcourt的位置，将结果转换为统一的格式（A=simcourt, B=baseline）

    Args:
        result: 原始评价结果
        simcourt_is_a: True表示simcourt在A位置，False表示simcourt在B位置

    Returns:
        转换后的结果（A=simcourt, B=baseline）
    """
    if simcourt_is_a:
        # simcourt已经在A位置，不需要转换
        return result

    # simcourt在B位置，需要将A/B对调
    for stage in result.get("data", {}):
        for role in result["data"][stage]:
            for item_name in result["data"][stage][role]:
                option = result["data"][stage][role][item_name].get("option", "C")
                # 对调A和B
                if option == "A":
                    result["data"][stage][role][item_name]["option"] = "B"
                elif option == "B":
                    result["data"][stage][role][item_name]["option"] = "A"
                # C保持不变

    return result


def evaluate_one_pair(record_simcourt: dict, record_baseline: dict, data_id: int,
                      baseline_name: str, output_dir: str, simcourt_is_a: bool) -> dict:
    """
    评价一对庭审记录
    根据POSITION_RULE决定simcourt的位置（A或B），然后逐个维度进行评价

    Args:
        record_simcourt: simcourt_only_debate的记录
        record_baseline: baseline（AgentCourt或AgentsCourt）的记录
        data_id: 数据编号
        baseline_name: baseline名称（"AgentCourt"或"AgentsCourt"）
        output_dir: 输出目录（用于存放failed.txt）
        simcourt_is_a: True表示simcourt在A位置，False表示simcourt在B位置

    Returns:
        完整的评价结果字典（A=simcourt, B=baseline）
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

    # 根据simcourt_is_a决定位置
    if simcourt_is_a:
        record_a = record_simcourt
        record_b = record_baseline
        pos_description = f"A=simcourt, B={baseline_name}"
    else:
        record_a = record_baseline
        record_b = record_simcourt
        pos_description = f"A={baseline_name}, B=simcourt"

    print(f"  位置配置: {pos_description}")

    # 提取辩论内容（数据源文件只包含辩论阶段）
    content_a = extract_debate_content(record_a)
    content_b = extract_debate_content(record_b)

    # 检查内容是否为空
    if not content_a:
        print(f"  警告：记录A的辩论内容为空")
    if not content_b:
        print(f"  警告：记录B的辩论内容为空")

    # 统计总评价项数量（每个阶段角色3个维度，共2个阶段角色=6项）
    total_items = sum(len(dim["items"]) for dim in EVALUATION_DIMENSIONS)
    current_item = 0

    # 遍历每个阶段和角色
    for dim in EVALUATION_DIMENSIONS:
        stage = dim["stage"]
        role = dim["role"]
        items = dim["items"]  # (item_name, item_explanation)的列表
        role_desc = dim["description"]

        # 初始化该阶段该角色的结果
        if stage not in result["data"]:
            result["data"][stage] = {}
        if role not in result["data"][stage]:
            result["data"][stage][role] = {}

        # 逐个评价每个维度（每次只调用一次模型）
        for item_name, item_explanation in items:
            current_item += 1
            print(f"  [{current_item}/{total_items}] 正在评价: {stage} - {role} - {item_name}")

            # 构建prompt（每次只评价一个维度）
            prompt = build_evaluation_prompt(content_a, content_b, stage, role,
                                            item_name, item_explanation, role_desc)

            # 重试机制：最多尝试2次（特别说明第2点）
            max_retries = 2
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

                    parsed_result = parse_model_response(response, item_name)

                    # 检查是否解析成功
                    if item_name in parsed_result:
                        break  # 解析成功，退出重试循环
                    else:
                        print(f"    第{retry_count + 1}次解析失败，未找到{item_name}")

                except Exception as e:
                    last_error = e
                    print(f"    第{retry_count + 1}次尝试出错: {e}")
                    parsed_result = None

            # 如果2次都失败，记录到failed.txt并填充默认值
            if parsed_result is None or item_name not in parsed_result:
                failed_log_path = os.path.join(output_dir, "failed.txt")
                with open(failed_log_path, 'a', encoding='utf-8') as f:
                    f.write(f"data_id={data_id}, baseline={baseline_name}, stage={stage}, role={role}, item={item_name}, error={str(last_error)}\n")
                print(f"    警告：{max_retries}次尝试均失败，已记录到failed.txt")

                # 填充默认值
                parsed_result = {item_name: {"option": "C", "text": f"解析失败（{max_retries}次重试）"}}

            # 反思检查：验证option和理由是否匹配（根据开关决定是否启用）
            if ENABLE_REFLECTION_CHECK:
                parsed_result = reflect_and_correct_result(parsed_result, item_name, instruction)

            # 将结果添加到总结果中
            result["data"][stage][role][item_name] = parsed_result.get(item_name, {"option": "C", "text": "模型未返回该维度"})

    # 转换为最终格式（A=simcourt, B=baseline）
    result = convert_result_to_final_format(result, simcourt_is_a)

    return result


def main():
    """
    主函数：执行批量评价
    对两个baseline（AgentCourt和AgentsCourt）分别与simcourt_only_debate进行比较
    根据POSITION_RULE随机化simcourt的位置（A或B）
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

            # 【特别说明】根据POSITION_RULE确定simcourt的位置
            # data_id从1开始，POSITION_RULE下标从0开始
            if 1 <= data_id <= len(POSITION_RULE):
                position_value = POSITION_RULE[data_id - 1]
                simcourt_is_a = (position_value == 1)
            else:
                # 如果超出范围，默认simcourt在A位置
                simcourt_is_a = True
                print(f"  警告：data_id={data_id}超出POSITION_RULE范围，使用默认位置（A=simcourt）")

            # 加载记录
            try:
                record_simcourt = load_trial_record(simcourt_path)
                record_baseline = load_trial_record(baseline_path)

                print(f"\n正在评价 data_id={data_id}...")
                if simcourt_is_a:
                    print(f"  位置规则：POSITION_RULE[{data_id-1}]={POSITION_RULE[data_id-1]} -> A=simcourt, B={baseline_name}")
                else:
                    print(f"  位置规则：POSITION_RULE[{data_id-1}]={POSITION_RULE[data_id-1]} -> A={baseline_name}, B=simcourt")

                # 进行评价（传递output_dir用于存放failed.txt）
                result = evaluate_one_pair(record_simcourt, record_baseline, data_id,
                                          baseline_name, output_dir, simcourt_is_a)

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
