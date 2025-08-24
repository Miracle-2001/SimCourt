# -*- coding: utf-8 -*-
import json
from openai import OpenAI
from tqdm import tqdm 
from role.deepseek_v3_0324 import call_deepseek_v3_0324
#from transformers import AutoTokenizer
import re
import time
import requests
import os
import httpx

# 先采用prompt生成[法官分析]、[审判依据]和最终[判决]

# 1、先解析出上一步的[法官分析]、[审判依据]和最终[判决]
# 2、把[审判依据]中的法律法规 与 相似案例的法律法规作对比，取并集
# 3、把庭审记录取出来
# 4、提示词：相似案例，法律法规

def DeepSeek(system_massage, prompt):
    messages=[{"role": "system", "content": system_massage}, 
                {"role": "user", "content": prompt}]
    return call_deepseek_v3_0324(messages=messages)

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
        "query": prompt,
        "need_answer": 1
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
    sim_cases_text=""
    fl=0
    for case in sim_cases:
        if case in anhao:
            if anhao[case]['caipanliyou']!="" or anhao[case]['caipanjieguo']!="":
                fl+=1
                sim_cases_text+="\n"+"【"+case+"】："+anhao[case]['caipanliyou']+anhao[case]['caipanjieguo']
            if fl==3: #only 3 cases
                break
    return answer+"类似案件："+sim_cases_text

laws_base_path = 'all_laws.json'
with open(laws_base_path, 'r', encoding='utf-8') as file:
    laws_base = json.load(file)

# 法律条文细节
def match_laws(laws_str):
    laws_list=laws_str.split("#")
    useful_laws_dict = {}
    for law_str in laws_list:
        try:
            law_str=law_str.split("|")
            law_name=None
            if len(law_str)==2:
                law_name=law_str[0]+law_str[1]
                law_detial = laws_base[law_str[0]][law_str[1]]
                useful_laws_dict[law_name] = law_detial
                
            elif len(law_str)==3:
                law_name=law_str[0]+law_str[2]
                law_detial = laws_base[law_str[0]][law_str[1]][law_str[2]]
                useful_laws_dict[law_name] = law_detial
        except:
            useful_laws_dict[law_name] = {}
        
    return useful_laws_dict

# 数据集
case_dataset = "../../../data/data0417"


# 案例
# candidate_cases_path = 'case.json'
# with open(candidate_cases_path, 'r', encoding='utf-8') as file:
#     candidate_cases_dict = json.load(file)

# analysis_record 结果
analysis_record_path = 'analysis_record.json'
with open(analysis_record_path, 'r', encoding='utf-8') as file:
    analysis_record_dict = json.load(file)

# prompt
# judge_final_path = '/system_prompt/judge_case_refine.txt'
# with open(judge_final_path, "r") as f:
#     judge_final_system = f.read()


# simu_list=[382 ,64 ,181 ,104,353,62,214,241,262]
simu_list=[214]

judge_analysis_revise_result = []
judge_analysis_revise_process=[]


with open('case_refine_result.json', 'r', encoding='utf-8') as file:
    res0=json.load(file)
    for dict in res0:
        if dict['id'] not in simu_list:
            judge_analysis_revise_result.append(dict)
with open('case_refine_process.json', 'r', encoding='utf-8') as file:
    res0=json.load(file)
    for dict in res0:
        if dict['id'] not in simu_list:
            judge_analysis_revise_process.append(dict)   
       
error_list = []
error_case_list = []
# 庭审记录 + 基本案情
ids = []
for i in range(40):  # 5组数字
    for j in range(5):
        # if i * 10+j<=163:
        #     continue
        # if i * 10+j<=351:
        #     continue
        ids.append(i * 10+j)
print(ids)


for id in tqdm(ids):
    
    if id not in simu_list:
        continue
    print(id)
    
    with open(os.path.join(case_dataset,f'example_{id}','data_anonymized.json'), 'r', encoding='utf-8') as file:
        case_test = json.load(file)
        # 庭审分析
    
    
    # analysis_record 得到的法律法规
    analysis_record = analysis_record_dict[str(id)]
    # (case_details=case_dict["prosecution_statement_sub"]+"证据："+str(case_dict["evidence"]), 
    #                                    case_type=str(case_dict["charge"])+"案件")
    # analysis_record_laws_detial 
    
    
    

    
    case_information="起诉书："+case_test["prosecution_statement_sub"]+"证据："+str(case_test["evidence"])
    previous_case = yilvkezhi_retriever(case_test["prosecution_statement_sub"]) 
    print(previous_case)
    # case_initial_result
    s1=analysis_record.split('[最终判决]：')
    case_initial_result=s1[1]
    tmp=s1[0]
    # case_initial_laws
    s2=tmp.split('[审判依据]：')
    case_initial_laws=s2[1]
    case_initial_laws=DeepSeek(case_initial_laws,
                               """
                               请把其中的每一个法条格式化返回；
                               每一个法条的格式要求为（相邻条目用|分隔）：部门法|第x条|第x条第x款
                               或者（相邻条目用|分隔）：部门法|第x条
                               （取决于法条有没有精确到第x款如果第x款的描述）
                               
                               相邻的法条之间用#隔开
                               
                               例如：
                               输入：
                               综上所述，依照：《中华人民共和国刑法》第二百八十条第一款、第七十三条第二款、第三款、第五十二条，《中华人民共和国专利法》第一条
                               则你应当回复：
                               中华人民共和国刑法|第二百八十条|第二百八十条第一款#中华人民共和国刑法|第七十三条|第七十三条第二款#中华人民共和国刑法|第七十三条|第七十三条第三款#中华人民共和国刑法|第五十二条#中华人民共和国专利法|第一条
                               
                               注意：
                               1.你只要格式化法条即可，不需要返回法条具体内容。
                               2.不要丢掉|和#，分隔符不要丢掉
                               3.按照格式要求返回，不要说任何多余的话。
                            
                               """
                               )
    
    case_initial_laws= match_laws(case_initial_laws)
    # case_initial_judge
    tmp=s2[0]
    s3=tmp.split('[法官分析]：')
    case_initial_judge=s3[1]
    
    
    
    
    CASE_TEMPLATE2 = """
    你将收到一个以往判例及当前案件基本信息，这个以往案件与当前案件非常相近，请以这个以往案件为标准判例，根据其中的审判依据（法律法规）及审判结果对当前案件进行分析和裁决。
    以往判例信息：
    判例案件：{previous_case}
    判例案件类型：{previous_case_type}
    
    请借鉴以上判例（案情分析、审判依据及审判结果）对以下的当前案件的审判意见、依据和结果进行进一步的改进（可能存在依据错误、结果错误等），并做出更加公正、严谨的最终裁决。
    当前案件信息：
    原告：{case_plaintiff}
    被告：{case_defendant}，被告基本情况：{case_defendant_detail}
    基本案情：{case_information}
    案件类型: {case_type}
    法院初步审判意见：{case_initial_judge}
    法院初步审判依据：{case_initial_laws}
    法院初步审判结果：{case_initial_result}
    最终裁决：
    
    注意，你只要输出最终判决即可！不需要添加分析过程和其他理由。
    最终判决包含刑期，缓刑，罚金（如果不适用于缓刑和罚金，则无需涉及）
    """

    
    # if len(candidate_cases["content"]) > 1500:
    #     previous_case_analysis = candidate_cases["content"][:1500]
    # else:
    #     previous_case_analysis = candidate_cases["content"]
    
    # if len(str(candidate1_laws)) >  2200:
    #     candidate1_laws = str(candidate1_laws)[:2200]
    # else:
    #     candidate1_laws = candidate1_laws

    
    # 基本案情
    task_prompt2 = CASE_TEMPLATE2.format(
        previous_case_type="刑事案件",
        previous_case=previous_case,
        case_plaintiff="上诉人", 
        case_defendant="被上诉人",
        case_defendant_detail=case_test["defendant_information"],
        case_information=case_information,
        case_type='刑事案件',
        case_initial_judge=case_initial_judge,
        case_initial_laws=case_initial_laws, 
        case_initial_result=case_initial_result,
        )
    
    # 基本案情
    
    try:
        judge_slef_analysis = DeepSeek("", task_prompt2)
        panjue=DeepSeek(judge_slef_analysis,
                    """
                    返回输入中的刑期，罚金，缓刑结果。
                    
                    你的返回结果应当为：
                    刑期#缓刑#罚金
                    其中刑期、缓刑换算到以月为单位，罚金单位为元，返回阿拉伯数字。两两之间用#分隔。
                    如果刑期不可计算，比如无期徒刑，死缓等，则直接保留刑期本身即可，不必再换算。
                    如果没有罚金，则罚金部分为0
                    如果没有缓刑，则缓刑部分为0
                    
                    例如：
                    ...判处有期徒刑二年六个月，缓刑三年，罚金四千元。...
                    返回：
                    30#36#4000
                
                    直接返回结果即可，不要说多余的话！
                    """    
                        )
        panjue=panjue.split("#")
        tmp={"term":0,"fine":0,"reprieve":0,"res":judge_slef_analysis}
        if panjue[0].isdigit():
            tmp["term"]=float(panjue[0])
        else:
            tmp["term"]=panjue[0]
            
        if panjue[1]=="":
            panjue[1]=0
        if panjue[2]=="":
            panjue[2]=0    
        tmp["reprieve"]=float(panjue[1])
        tmp["fine"]=float(panjue[2])
        
        tmp.update({'id':id})
        
        judge_analysis_revise_result.append(tmp)
        judge_analysis_revise_process.append(
            {'id':id,'origin_judge':judge_slef_analysis,'task_prompt':task_prompt2}
            )

    except:
        print('Error:', str(id))
        error_list.append(str(id))

    with open('case_refine_result.json', 'w', encoding='utf-8') as file:
        json.dump(judge_analysis_revise_result, file, ensure_ascii=False, indent=4)
    with open('case_refine_process.json', 'w', encoding='utf-8') as file:
            json.dump(judge_analysis_revise_process, file, ensure_ascii=False, indent=4)

print(error_list)



    
