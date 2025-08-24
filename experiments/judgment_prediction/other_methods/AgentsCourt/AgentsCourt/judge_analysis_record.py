# -*- coding: utf-8 -*-
import json
from openai import OpenAI
from tqdm import tqdm 
import httpx
import os
from role.deepseek_v3_0324 import call_deepseek_v3_0324

def DeepSeek(system_massage, prompt):
    messages=[
            {"role": "system", "content": system_massage},
            {"role": "user", "content": prompt}
        ]
    return call_deepseek_v3_0324(messages=messages)
    

# 数据集
case_dataset = "../../../data/data0417"


# 庭审记录
court_judge_path = './role/court_records.json'
with open(court_judge_path, 'r', encoding='utf-8') as file:
    court_record = json.load(file)

# prompt
# judge_analysis_record_path = '/system_prompt/judge_analysis_record2.txt'
# with open(judge_analysis_record_path, "r") as f:
#     judge_analysis_record_system = f.read()
# simu_list=[382 ,64 ,181 ,104, 353,62,214,241,262]
simu_list=[214]
judge_analysis_record_result = {}
with open("analysis_record.json","r",encoding='utf-8') as file:
    judge_analysis_record_result=json.load(file)
# for dict in res0:
#     if dict['id'] not in simu_list:
#         continue
#     judge_analysis_record_result.append(dict)

error_list = []
error_case_list = []
# 庭审记录 + 基本案情
ids = []
for i in range(40):  # 5组数字
    for j in range(5):
        # if i * 10+j<=163:
        #     continue
        ids.append(i * 10+j)
print(ids)

for id in tqdm(ids):
    if id not in simu_list:
        continue
    with open(os.path.join(case_dataset,f'example_{id}','data_anonymized.json'), 'r', encoding='utf-8') as file:
        case_test = json.load(file)
        # 庭审分析
    print(id)
    if str(id) in court_record:
        current_court_record = court_record[str(id)]
        if len(current_court_record) >= 2:
            record1 = current_court_record[0]
            record2 = current_court_record[1]
            current_court_record_text = record1 + "\n" + record2
        else:
            current_court_record_text = current_court_record[0]
    else:
        current_court_record_text = '无'

    CASE_TEMPLATE2 = """
    你正在参与一次模拟法庭的活动，请记住这是一场虚拟的过程，你现在扮演一位专业的法官，请根据以下指引进行发言：

    请注意以下几点：
    1、若当前案件为**刑事案件**：则需要首先明确被告人的具体罪名和犯罪事实。评估犯罪行为对受害者及社会造成的影响和危害。考虑被告人的认罪态度、悔罪表现及犯罪后的改正行为。
    
    不管什么情况下，你的每一次发言只能且必须遵守以下格式：
    [法官分析]：本院认为，<你的分析>
    [审判依据]：综上所述，依照：<你依据的法律条文（陈列出案件涉及的法律条款具体名称如第几条第几款第几项）>
    [最终判决]：判决如下：<你的判决（必须给出判决结果，且不可包含除判决结果外的内容）>

    你将收到当前案件的基本情况、上诉人请求、法庭辩论，请根据你作为一名法官的专业知识进行最终的判决。
    不管什么情况，你必须在[最终判决]中给出如示例中的明确的判决结果！
    上诉人：{case_plaintiff}，上诉人基本情况：{case_defendant_detail}
    被上述人：{case_defendant}
    案件类型: {case_type}
    庭审记录：{court_record}
    最终裁决："""

    # 基本案情
    task_prompt = CASE_TEMPLATE2.format(
        case_plaintiff="上诉人", 
        case_defendant="被上诉人",
        case_defendant_detail=case_test["defendant_information"],
        case_type='刑事案件',
        court_record=current_court_record_text
        )
    
    #print(task_prompt)
    try:
        judge_self_analysis = DeepSeek("", task_prompt)
        judge_analysis_record_result[id] = judge_self_analysis
        #print(judge_analysis)
    except:
        print('Error:', id)
        error_list.append(id)

    with open('analysis_record.json', 'w', encoding='utf-8') as file:
        json.dump(judge_analysis_record_result, file, ensure_ascii=False, indent=4)

print(error_list)



    
