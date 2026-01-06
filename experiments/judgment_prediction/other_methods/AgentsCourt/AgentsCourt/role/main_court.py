from role_playing import RolePlaying
import json
import copy
from tqdm import tqdm
import os
import sys
import time 

def load_json(file_path):
    """
    加载JSON文件
    :param file_path: 文件路径
    :return: JSON数据
    """
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_court_log(js,file_path):
    """
    保存法庭日志
    :param file_path: 保存文件路径
    """
    # if os.path.exists(file_path)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(js, f, ensure_ascii=False, indent=2)

def court_interact(Task, chat_turn_limit):
    case_dict = Task
    case_name = case_dict["charge"]
    CASE_TEMPLATE = """基本案情: {case_details}\n案件类型: {case_type}"""
    task_prompt = CASE_TEMPLATE.format(case_details=case_dict["prosecution_statement_sub"]+"证据："+str(case_dict["evidence"]), 
                                       case_type=str(case_dict["charge"])+"案件")
    case_plaintiff = "公诉机关"
    case_defendant = case_dict['defendant_information'].split(",")[0][3:]
    case_defendant_detail = case_dict['defendant_information']

    plaintiff_prompt = case_dict['prosecution_statement_sub']
    defendant_prompt = '无'
    
        
    role_play_session = RolePlaying(
        ('plaintiff', plaintiff_prompt),
        ('defendant', defendant_prompt),
        case_plaintiff=case_plaintiff,
        case_defendant=case_defendant,
        case_defendant_detail=case_defendant_detail,
        task_prompt=task_prompt,
        #with_task_specify=True,
    )

    #print(Fore.YELLOW + f"\n当前案号: {case_name}\n{task_prompt}\n\nInteractive simulating...\n")
    
    n = 0
    assistant_msg, _ = role_play_session.init_chat()

    court_record = []
    while n < chat_turn_limit:
        n += 1
        assistant_return, user_return= role_play_session.step(assistant_msg)
            #######
        assistant_msg, assistant_terminated, assistant_info = assistant_return
        user_msg, user_terminated, user_info = user_return
        #print("user_msg:", user_msg)
        #print_text_animated(Fore.BLUE + f"Plaintiff:\n\n{user_msg.content}\n")
        #print_text_animated(Fore.GREEN + f"Defendant:\n\n{assistant_msg.content}\n")
        user_content = user_msg.content
        assistant_content = assistant_msg.content
        if user_content.startswith('[原告控诉]') or user_content.startswith('[原告发言]'):
            court_record.append(user_content)
        
        if assistant_content.startswith('[被告辩解]'):
            court_record.append(assistant_content)

    return court_record




if __name__ == "__main__":
    data_path="../../../../data/data0417"
    
    
    fail_id = []
    court_record_dict = {}
    ids = []
    for i in range(40):  # 5组数字
        for j in range(5):
            # if i * 10+j<=163:
            #     continue
            ids.append(i * 10+j)
    print(ids)        
    # simu_list=[382 ,64 ,181 ,104, 353,62,214,241,262]
    simu_list=[214]
    # case_data_to_run = self.case_data[:62]
    
    court_record_dict=load_json("./court_records.json")
    ran=[i for i in range(400)]
    for id in tqdm(ids):
        if id not in simu_list:
            continue
        case_dict=load_json(os.path.join(data_path,f'example_{id}','data_anonymized.json'))
        # try:
        case_num = id
        court_record = {}
        iter_num = 1
        # while len(court_record) < 7 and iter_num < 5:
        print('Simulating case ',id)
        court_record = court_interact(Task=case_dict, chat_turn_limit=3)
        # print("record ",court_record)
        court_record_dict[case_num] = court_record
        iter_num += 1
        
        print('Number of Court records: {}'.format(len(court_record)))
        print('{} Saved!'.format(case_num))
        # except Exception as e:
        #     case_num = id
        #     fail_id.append(case_num)
        with open("court_records_pro.json", "w", encoding='utf-8') as file:
            json.dump(court_record_dict, file, ensure_ascii=False, indent=4)
    print("fail_id ",fail_id)
    with open("court_records.json", "w", encoding='utf-8') as file:
        json.dump(court_record_dict, file, ensure_ascii=False, indent=4)

    


