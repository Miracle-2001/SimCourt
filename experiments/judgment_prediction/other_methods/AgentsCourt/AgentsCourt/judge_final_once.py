import json
import openai
from tqdm import tqdm 
import tiktoken
import requests
import re
import os
from .role.deepseek_v3_0324 import call_deepseek_v3_0324
# 最终裁决

def num_tokens_from_string(string: str, encoding_name: str) -> int:
    """Returns the number of tokens in a text string."""
    encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
    num_tokens = len(encoding.encode(string))
    return num_tokens

def DeepSeek(system_massage, prompt):
    messages=[{"role": "system", "content": system_massage}, 
                {"role": "user", "content": prompt}]
    return call_deepseek_v3_0324(messages=messages)
    
# 数据集
case_dataset = "../../../data/data0417"

# 庭审记录
court_judge_path = './court_records.json'
with open(court_judge_path, 'r', encoding='utf-8') as file:
    court_judge = json.load(file)

# 案例
# candidate_cases_path = 'retrieve_candi_case/case_number_candi_laws_detail1.json'
# with open(candidate_cases_path, 'r', encoding='utf-8') as file:
#     candidate_cases_dict = json.load(file)
def extract_bracket_content(text):
    # 正则表达式匹配【】及其内部内容
    pattern = r'【(.*?)】'
    # 使用findall方法找到所有匹配的内容
    contents = re.findall(pattern, text)
    return contents
def yilvkezhi_retriever(prompt):
    url = "http://web.megatechai.com:33615/test_case_app/wenshu_search/search_and_answer"
    payload = json.dumps({
    "query": prompt
    })
    headers = {
    'Content-Type': 'application/json'
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    try:    
        response=json.loads(response.text)
    except:
        print("Error!",response.text)
        return None
    answer=response["data"]["answer"]
    sim_cases=extract_bracket_content(answer)
    anhao={}
    for js in response["data"]["wenshu_results"]:
        anhao[js['anhao']]=js
    sim_cases_text="类似案件为："
    fl=0
    for case in sim_cases:
        if case in anhao:
            if anhao[case]['caipanliyou']!="" or anhao[case]['caipanjieguo']!="":
                fl+=1
                sim_cases_text+="\n"+"【"+case+"】："+anhao[case]['caipanliyou']+anhao[case]['caipanjieguo']
            if fl==3: #only 3 cases
                break
    if fl!=0:
        answer+="\n\n#####\n"+sim_cases_text
    return answer

# prompt
judge_final_path = '/system_prompt/judge_final.txt'
with open(judge_final_path, "r") as f:
    judge_final_system = f.read()

judge_final_result = {}
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
    
    with open(os.path.join(case_dataset,f'example_{id}','data_anonymized.json'), 'r', encoding='utf-8') as file:
        case_test = json.load(file)
        # 相似案例
    candidate_cases = candidate_cases_dict[case_test['案号']][0]
    candidate1 = candidate_cases_dict[case_test['案号']][0]
    candidate1_laws = candidate1["审判依据"]
    if len(candidate_cases_dict[case_test['案号']]) > 1:
        candidate2 = candidate_cases_dict[case_test['案号']][1]
        
        candidate2_laws = candidate2["审判依据"]

        for k2, v2 in candidate2_laws.items():
            if k2 not in candidate1_laws:
                candidate1_laws[k2] = v2

    # 庭审分析
    court_judge_analysis = court_judge[case_test['案号']]

    CASE_TEMPLATE = """
    你将收到一个以往判例及当前案件基本信息，这个以往案件与当前案件非常相近，请以这个以往案件为标准判例，根据其中的审判依据（法律法规）及审判结果对当前案件进行分析和裁决。
    以往判例信息：
    判例案件基本案情分析：{previous_case_analysis}
    判例案件类型：{previous_case_type}
    判例审判结果：{previous_case_result}
    
    请借鉴以上判例（审判依据及结果）对以下的当前案件进行公正的裁决：
    当前案件信息：
    原告：{case_plaintiff}
    被告：{case_defendant}，{case_defendant_detail}
    基本案情: {case_details}
    原告诉请判令：{case_plaintiff_detail}
    案件类型: {case_type}
    庭审过程分析：{case_court_record}
    请仔细参考以下法律条文：{previous_case_laws}
    最终裁决："""

    # 基本案情
    task_prompt = CASE_TEMPLATE.format(
        previous_case_type=candidate_cases["案件类型"],
        previous_case_analysis=candidate_cases["content"],
        previous_case_laws=candidate1_laws,
        previous_case_result=candidate_cases["审判结果"],
        case_plaintiff=case_test["原告（公诉）"], 
        case_defendant=case_test["被告"],
        case_defendant_detail=case_test["被告基本情况"],
        case_details=case_test["基本案情"],
        case_plaintiff_detail=case_test["原告诉请判令（公诉机关指控）"],
        case_type=case_test["类别"] + '案件',
        case_court_record=court_judge_analysis
        )
    #print(task_prompt)
    try:
        judge_analysis = DeepSeek(judge_final_system, task_prompt)
        judge_final_result[case_test['案号']] = judge_analysis
        #print(judge_analysis)
    except:
        print('Error:', case_test['案号'])
        error_list.append(case_test['案号'])


    with open('judge_final_result.json', 'w', encoding='utf-8') as file:
        json.dump(judge_final_result, file, ensure_ascii=False, indent=4)

print(error_list)



    
