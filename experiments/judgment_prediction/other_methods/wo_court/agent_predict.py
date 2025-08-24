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
from agent import Agent
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
        llm=get_apillm("deepseek-v3-250324")
    )
    # simu_list=[i for i in range(400)]
    simu_list=[214]
    #[382 ,64 ,181 ,104, 353,62,214,241,262]
    files=os.listdir(pwd)
    judge=[]
    result=[]
    # with open('judge_04191844.json', 'r', encoding='utf-8') as file:
    #     judge0=json.load(file)
    # for dict in judge0:
    #     if dict["id"] not in simu_list:
    #         judge.append(dict)
    # with open('result_04191844.json', 'r', encoding='utf-8') as file:
    #     result0=json.load(file)    
    # for dict in result0:
    #     if dict["id"] not in simu_list:
    #         result.append(dict)
    
    files = sorted(files, key=lambda x: int(x.split('_')[1]))
    print(files)
    for id in tqdm(range(len(files))):
        file=files[id]
        cnt=int(file.split("_")[-1])
        if cnt not in simu_list:
            continue
        try:
            print(file)
            
            # if cnt!=21:
            #     continue
            with open(os.path.join(pwd,file,'data_anonymized.json')) as f:
                js=json.load(f)
            res=agent.pure_final_judge(f"""
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

                            1.**注意！起诉书中提及实刑、缓刑、罚金等，但具体是否有罪，是否适用于缓刑，是否处以罚金等，需要你自己判断！**
                            2.**如果认为不需要处罚实刑，不适用缓刑，或不处罚罚金，则不提及实刑，缓刑或罚金。不必完全依照起诉书**
                            3.**注意，判决仅包含【最后判决结果】即可（仅包含判处内容），相关理由和法条不用涉及！**
                            """)
            # book_prompt=f"""
            #     案件基本信息：
            #     指控罪名：{js["charge"]}
            #     被告人信息：{js["defendant_information"]}
            #     起诉状：{js["prosecution_statement_sub"]}
            #     公诉人出示的证据：{js["evidence"][0]} 
            #     辩护人出示的证据：{js["evidence"][1]}

            #     【任务】
            #     请写出案件的判决书。
                
            #     判决书整体分为如下5个部分：
            #     ①法官查明信息项。包括被告，辩护人，起诉原因，程序性事实。包括姓名性别年龄学历。
            #     ②公诉机关指控。是起诉书中的起诉内容。（法官应当引导公诉人完整阐述指控事实和证据）
            #     ③法官应当引导被告人。最后使得他对指控犯罪事实、罪名及量刑建议没有异议，自愿认罪认罚且签字具结，在开庭审理过程中亦无异议。
            #     ④总结控辩双方发言中关于事实的共性部分（查明事实），控辩发言中法律适用的部分，（本院认为）（最后定论）
            #     ⑤最后判决。
                
            #     **其中，最后判决结果已经确定。**
            #     **判决结果是：{res}**
                
            #     【判决书格式】
            #     ××××人民法院
            #     刑事判决书
            #     （一审公诉案件用）
            #     （××××）×刑初字第××号
            #     公诉机关××××人民检察院。
            #     被告人……（写明姓名、性别、出生年月日、民族、籍贯、职业或工作单位和职务、住址和因本案所受强制措施情况等，现在何处）。
            #     辩护人……（写明姓名、性别、工作单位和职务）。
            #     ××××人民检察院于××××年××月××日以被告人×××犯××罪，向本院提起公诉。本院受理后，依法组成合议庭（或依法由审判员×××独任审判），公开（或不公开）开庭审理了本案。××××人民检察院检察长（或员）×××出庭支持公诉，被告人×××及其辩护人×××、证人×××等到庭参加诉讼。本案现已审理终结。
            #     ……（首先概述检察院指控的基本内容，其次写明被告人的供述、辩解和辩护人辩护的要点）。
            #     经审理查明，……（详写法院认定的事实、情节和证据。如果控、辩双方对事实、情节、证据有异议，应予分析否定。在这里，不仅要列举证据，而且要通过对主要证据的分析论证，来说明本判决认定的事实是正确无误的。必须坚决改变用空洞的“证据确凿”几个字来代替认定犯罪事实的具体证据的公式化的写法）。
            #     本院认为，……〔根据查证属实的事实、情节和法律规定，论证被告人是否犯罪，犯什么罪（一案多人的还应分清各被告人的地位、作用和刑事责任），应否从宽或从严处理。对于控、辩双方关于适用法律方面的意见和理由，应当有分析地表示采纳或予以批驳〕。依照……（写明判决所依据的法律条款项）的规定，判决如下：
            #     ……〔写明判决结果。分三种情况：
            #     第一、定罪判刑的，表述为：
            #     “一、被告人×××犯××罪，判处……（写明主刑、附加刑）；
            #     二、被告人×××……（写明追缴、退赔或没收财物的决定，以及这些财物的种类和数额。没有的不写此项）。”
            #     第二、定罪免刑的表述为：
            #     “被告人×××犯××罪，免予刑事处分（如有追缴、退赔或没收财物的，续写为第二项）。”
            #     第三、宣告无罪的，表述为：
            #     “被告人×××无罪。”〕
            #     如不服本判决，可在接到判决书的第二日起××日内，通过本院或者直接向××××人民法院提出上诉。书面上诉的，应交上诉状正本一份，副本×份。
            #     审判长×××
            #     ××××年××月××日
            #     书记员 ×××
                
            #     【注意事项】
            #     1.要给出具体的罪名，随后给出刑期，精确到几个月。如果需要，要包含赔偿金额。
            #     2.判决书要包含经庭审查明的案件事实，证明这些案件事实的证据，对于事实认定和法律适用的理由。以及最后的判决。
            #     3.格式中，部分xx处，如果根据已有信息能确定内容，就补全，否则保留xx的格式。
            #     4.回复时直接以判决书的格式给出你的判罚，不要说多余的话。
            #     5.**注意！起诉书中提及实刑、缓刑、罚金等，但具体是否有罪，是否适用于缓刑，是否处以罚金等，需要你自己判断！**
            #       **如果认为不适用缓刑，或不处罚罚金，则不提及缓刑和罚金。不必完全依照起诉书**
            #     """
            # document=agent.speak(book_prompt,"")
            
            
            
            panjue=agent.speak(res,
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
            judge.append({'id':cnt,'judge':res,'plan':agent.current_plan})#,'doc':document})
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


    save_json(judge,"./",f"judge_{formatted_datetime}.json")
    save_json(result,"./",f"result_{formatted_datetime}.json")
    