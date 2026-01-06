import json
import os
import random
import datetime
import time
from tqdm import tqdm
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from tqdm import trange
import re
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from LLM.apillm import APILLM
from agent import Agent

from EMDB.db import db
from LLM.offlinellm import OfflineLLM
from LLM.apillm import APILLM
from frontEnd import frontEnd,date
from datetime import datetime




def save_json(js,filepath,filename):
    if os.path.exists(filepath) == False:
        os.makedirs(filepath)
    # js=json.loads(js)
    with open(os.path.join(filepath,filename),"w", encoding="utf-8") as f:
        json.dump(js, f, ensure_ascii=False, indent=2)

def get_apillm(name):
    return APILLM(
            api_key="JWXGr1DMcAz4yGPzPtdqHs4G",
            api_secret="4J4sAHLH4H6VmyTu3PbGNeqIN8uqqF9Y",
            platform="proxy",
            model=name,
        )
    
    
if __name__=="__main__":
    pwd='../../data/data0417'
    
    agent=Agent(
        id=-1,
        name=-1,
        role='generator',
        description="",
        llm=get_apillm("llama3-8b")
    )
    agent2=Agent(
        id=-1,
        name=-1,
        role='generator',
        description="",
        llm=get_apillm("deepseek-v3-250324")
    )
    
    files=os.listdir(pwd)
    # simu_list=[382 ,64 ,181 ,104, 353,62,214,241,262]
    # simu_list=[i for i in range(400)]
    # simu_list=[214]
    judge=[]
    result=[]
    # with open('judge_04191239.json', 'r', encoding='utf-8') as file:
    #     judge0=json.load(file)
    # for dict in judge0:
    #     if dict["id"] not in simu_list:
    #         judge.append(dict)
    # with open('result_04191239.json', 'r', encoding='utf-8') as file:
    #     result0=json.load(file)    
    # for dict in result0:
    #     if dict["id"] not in simu_list:
    #         result.append(dict)
    files = sorted(files, key=lambda x: int(x.split('_')[1]))
    for id in tqdm(range(len(files))):
        file=files[id]
        cnt=int(file.split("_")[-1])
        # if cnt not in simu_list:
        #     continue
        try:
            print(file)
            with open(os.path.join(pwd,file,'data_anonymized.json')) as f:
                js=json.load(f)
            res=agent.speak(f"""
                            案件基本信息：
                            指控罪名：{js["charge"]}
                            被告人信息：{js["defendant_information"]}
                            起诉状：{js["prosecution_statement_sub"]}
                            公诉人出示的证据：{str(js["evidence"][0])} 
                            辩护人出示的证据：{str(js["evidence"][1])}
                            """,
                            """
                            你是本次案件的审判长，你要生成案件的判决结果。
                            判决结果包含刑期、罚款（以及赔偿等）
                            刑期包含实刑与缓刑
                            
                            特别地，定罪判刑时，应当包含实刑，可能会包含缓刑、罚金。
                            例如：
                            判决如下：被告人张某犯xxx罪，判处拘役x个月，缓刑x个月，并处罚金人民币二千元。

                            **注意！起诉书中提及实刑、缓刑、罚金等，但具体是否有罪，是否适用于缓刑，是否处以罚金等，需要你自己判断！**
                            **如果认为不需要处罚实刑，不适用缓刑，或不处罚罚金，则不提及实刑，缓刑或罚金。不必完全依照起诉书**
                            **注意，判决仅包含【最后判决结果】即可（仅包含判处内容），相关理由和法条不用涉及！**
                            
                            """)
            # agent.speak(f"""
            #                 案件基本信息：
            #                 指控罪名：{js["charge"]}
            #                 被告人信息：{js["defendant_information"]}
            #                 起诉状：{js["prosecution_statement_sub"]}
            #                 公诉人出示的证据：{str(js["evidence"][0])} 
            #                 辩护人出示的证据：{str(js["evidence"][1])}
            #                 """,
            #                 """
            #                 你是本次案件的审判长，作为审判长，你要根据庭审记录、证据、起诉书、被告人信息、辩论焦点和事实查明等给出公正的判罚。
                        
                            
            #                 #####
                            
            #                 【回复要求】
            #                 你的回复应当以‘判决如下’开头，随后声明判决。
            #                 （1）第一、定罪判刑的，表述为：
            #                 “一、被告人×××犯××罪，判处……（写明主刑、附加刑）；
            #                 二、被告人×××……（写明追缴、退赔或没收财物的决定，以及这些财物的种类和数额。没有的不写此项）。”
            #                 （2）第二、定罪免刑的表述为：
            #                 “被告人×××犯××罪，免予刑事处分（如有追缴、退赔或没收财物的，续写为第二项）。”
            #                 （3）第三、宣告无罪的，表述为：
            #                 “被告人×××无罪。”〕
                            
            #                 特别地，定罪判刑时，应当包含实刑，可能会包含缓刑、罚金。
            #                 例如：
            #                 判决如下：被告人张某犯xxx罪，判处拘役x个月，缓刑x个月，并处罚金人民币二千元。
                            
            #                 【注意事项】
            #                 1.要给出具体的罪名，随后给出刑期。如果需要，要包含缓刑和赔偿、罚款金额。
            #                 2.**注意！起诉书中提及实刑、缓刑、罚金等，但具体是否有罪，是否适用于缓刑，是否处以罚金等，需要你自己判断！**
            #                 **如果认为不需要处罚实刑，不适用缓刑，或不处罚罚金，则不提及实刑，缓刑或罚金。不必完全依照起诉书**
            #                 3.回复时直接给出你的判罚，不要说多余的话。
            #                 """)
            panjue=agent2.speak(res,
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

                                注意，都是以月份为单位！！而不是年
                                直接返回结果即可，不要说多余的话！
                            """    
                                    )
            panjue=panjue.split("#")
            tmp={"term":0,"fine":0,"reprieve":0}
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
            tmp.update({'id':cnt})
            
            result.append(tmp)
            print("res ",tmp)
            judge.append({'id':cnt,'judge':res})
        except Exception as e:
            with open("failed.txt", "a", encoding="utf-8") as file:
                file.write(str(cnt)+" "+str(e))   
            continue
            
        
    
    # 假设有一个列表 list_of_dicts，其中包含多个形如 {id: str} 的字典
    # list_of_dicts = [{'id': '3'}, {'id': '1'}, {'id': '2'}]

    # 使用 sorted() 函数进行排序，key 参数指定按照字典中的 'id' 键进行排序
    # 由于 'id' 的值是字符串类型，需要将其转换为整数以便正确排序
    judge = sorted(judge, key=lambda x: int(x['id']))
    result= sorted(result, key=lambda x: int(x['id']))
    
    # 打印排序后的列表
    print(result)
    
    
        # 获取当前日期时间
    current_datetime = datetime.now()

    # 格式化日期时间为指定的序列格式
    formatted_datetime = current_datetime.strftime('%m%d%H%M')


    save_json(judge,"./",f"judge_llama3-8b{formatted_datetime}.json")
    save_json(result,"./",f"result_llama3-8b{formatted_datetime}.json")
    