import json
import os
import random
import logging
import argparse
import gradio as gr
import datetime
import time
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from tqdm import trange
import re
from typing import Literal, Optional
from LLM.offlinellm import OfflineLLM
from LLM.apillm import APILLM
from agent import Agent,Agent_litigants,Agent_Judge
from frontEnd import frontEnd,date,simplify
from agent import Context
from LLM.apillm import APILLM
from prompts import *

console = Console()

def prepare_history_context(history_list) -> str:
    formatted_history = ["当前庭审记录："]
    for entry in history_list:
        role = entry["role"]
        content = entry["content"].replace("\n", "\n  ")
        formatted_entry = f"\\role{{{role}}}\n  {content}"
        formatted_history.append(formatted_entry)
    return "\n\n".join(formatted_history)
                                         
class CourtSimulation(frontEnd):
    def __init__(self, config_path, stage_prompt, case_data_path, log_level, log_think,launch=False):
        """
        初始化法庭模拟类
        :param config_path: 配置文件路径
        :param stage_prompt: 各个阶段的prompt
        :param case_data_path: 案例数据（可以是单个文件路径或包含多个案例的目录路径）
        :param log_level: 日志级别
        :param log_think: 是否打印思考step
        """
        # 调用父类的初始化方法
        super().__init__()

        self.setup_logging(log_level)
        self.config = self.load_json(config_path)
        self.case_data_path = case_data_path
        self.stage_prompt=self.load_json(stage_prompt)
        self.log_think = log_think
        self.stages=['庭审准备','法庭调查','举证质证','法庭辩论','被告人陈述']
        
        if launch:
            self.launch()

    def create_agent(self, all_description, role_config, modelname, fact=None, log_think=False):
        """
        创建角色代理
        :param all_description: 
        :param role_config: 角色配置
        :return: Agent实例
        """
        # if role_config["llm_type"] == "offline":
        #     # todo 添加文心一言模型到web页面
        #     agentllm = OfflineLLM(role_config["model_path"])
        # elif role_config["llm_type"] == "apillm":
        print("creating agent ",role_config.get("role", None))
        agentllm = APILLM(
            api_key=role_config["api_key"],
            api_secret=role_config.get("api_secret", None),
            platform=role_config["model_platform"],
            model=modelname,
        )

        if role_config.get("role", None)=="审判长":
            nowAgent=Agent_Judge(
                id=role_config["id"],
                name=role_config["name"],
                role=role_config.get("role", None),
                description=all_description[0]+role_config["description"]+all_description[1],
                llm=agentllm,
                # db=db(role_config["name"]),
                # log_think=log_think,
            )
            nowAgent.preparation(self.case_data["prosecution_statement"],self.case_data["defendant_information"],"公诉人出示的："+str(self.case_data["evidence"][0])+"辩护人出示的："+str(self.case_data["evidence"][1]))
            return nowAgent
        else:
            nowAgent=Agent_litigants(
                id=role_config["id"],
                name=role_config["name"],
                role=role_config.get("role", None),
                description=all_description[0]+role_config["description"]+all_description[1],
                llm=agentllm,
                fact=fact,
                # db=db(role_config["name"]),
                # log_think=log_think,
            )
            if role_config.get("role", None)!="被告人":
                request=self.case_data['request'] if 'request' in self.case_data else ""
                if request!="": # and role_config.get("role", None)=="辩护人"
                    request="被告人诉求："+request

                # fact=""
                # if role_config.get("role", None)=="辩护人" and self.case_data["fact"]!="":
                #     fact="被告人认为的事实："+self.case_data["fact"]
                    
                nowAgent.preparation(self.case_data["prosecution_statement"],self.case_data["defendant_information"]+request,"公诉人出示的："+str(self.case_data["evidence"][0])+"辩护人出示的："+str(self.case_data["evidence"][1]))
            return nowAgent
            

    def add_to_history(self, role, content, interrupt_flag=0, now_stage="default"):
        """
        添加对话到历史记录
        :param role: 说话角色
        :param name: 说话人名字
        :param content: 对话内容
        :param interrupt_flag: 中断标志
        :param now_stage: 当前阶段
        """
        self.agent_speak(role, content)
        time.sleep(1)
        # 添加中断标志和阶段标志

        # interrupt_flag = 0: 审判长，不具备打断选项
        # interrupt_flag = 1: 审判长，具备打断选项，且这句话是审判长正在打断
        # interrupt_flag = 2: 非审判长，这句话可能被打断但是审判长没有打断，所以正常说出来了
        # interrupt_flag = 3: 非审判长，没有被打断的可能

        # TODO: if content contains \\role, consider using the following code to truncate \\role and following content
        # if len(re.findall(r'\\role', content)) > 0:
        #     print("WARNING: should not have \\role in content")
        #     content = content.split("\\role")[0]

        self.global_history.append({"role": role, 
                                    "content": content,
                                    "interrupt": interrupt_flag,
                                    "stage": now_stage})
        self.all_pure_content.append(content)
        color = self.role_colors.get(role, "white")
        console.print(
            Panel(content, title=f"{role} ", border_style=color, expand=False)
        )
    
    def set_instruction(self, now_stage):
        self.judge.set_instruction(self.stage_prompt[now_stage]["judge"])
        self.prosecution.set_instruction(self.stage_prompt[now_stage]["prosecution"])
        self.defendant.set_instruction(self.stage_prompt[now_stage]["defendant"])
        # self.stenographer.set_instruction(self.stage_prompt[now_stage]["stenographer"])
        self.advocate.set_instruction(self.stage_prompt[now_stage]["advocate"])
        
    def get_response(self, now_agent, prompt, simple=0):
        # 注意，这里给每个prompt后面又加了补充说明
        alert="再次注意：1.不要说多余的话，直接说你的内容。2.不用带说话人的名字，请直接说话。3.保持自己的身份，说符合自己身份的话。4.注意你是在法庭上发言，不要把自己的心里话或者策略说出来，你是在法庭上进行发言！5.必须实事求是，不要无中生有！不要涉及本案没有提到的内容！6.注意案件当前的时间，这一点在起诉状中有所体现。"
        alert2="必须注意！你的发言内容不能脱离你的进攻策略和防御策略，绝对不能编造策略中没有出现过的事实！【尤其对于自首、赔偿情况等关键问题，必须根据事实发言！】目前事实已经都确定了，你只需要对逻辑进行探讨，而不要对事实做出过多联想！"
        
        if now_agent.role!='审判长' and self.current_stage==3: #法庭辩论，额外强调不能出现幻觉
            alert+=alert2
        content = now_agent.execute(
            None,
            history_list=self.global_history,
            prompt=prompt+alert,
            simple=simple
        )
        # print("CONTENT",content)
        if isinstance(content, tuple): # 非常奇怪，不知道为什么在询问质证意见的时候回复会变成tuple，而其他时候就没事。
            # print("before",content)
            content=content[0]
            # print("after",content)
        
        return content

    def repeat(self,response):
        
        if response in self.all_pure_content:
            print("REPEAT!")
            return True
        # agent=Agent(
        #     id=-1,
        #     name=-1,
        #     role='generator',
        #     description="",
        #     llm=get_apillm("deepseek-v3-250324")
        # )
        # res=agent.speak("之前的发言内容："+str(self.all_pure_content)+"当前准备询问的问题："+str(response),"你要仔细检查之前的发言中，有没有和当前准备询问的问题【从意义上十分相近】的，比如之前已经询问过相似的问题了，或者之前的记录中已经明显出现了当前发言问题的答案。如果有，则回复一个字‘有’，如果没有，则回复‘没有’。你只要回复有或者没有，不要说多余的话！")
        
        # if res[0]=='有':
        #     return True
        return False
    
    def preparation_stage(self):
        # self.update_stage_backend(0)
        court_rules = self.config["court_rules"]
        self.set_instruction("Preparation")

        # * 书记员宣读法庭纪律
        self.add_to_history("书记员", court_rules, interrupt_flag = 3, now_stage="Preparation")
        self.add_to_history("书记员", "全体起立！请审判长入庭。", interrupt_flag = 3, now_stage="Preparation")
        self.add_to_history("审判长", "全体坐下！", interrupt_flag = 0, now_stage="Preparation")
        self.add_to_history("书记员", "报告审判长，庭前准备工作已经就绪，可以开庭。", interrupt_flag = 3, now_stage="Preparation")
        self.add_to_history("审判长", "现在开庭！传被告人到庭。", interrupt_flag = 0, now_stage="Preparation")
        self.add_to_history("审判长", "请执勤法警给被告人打开戒俱。", interrupt_flag = 0, now_stage="Preparation")

        # * 审判长查明身份
        self.add_to_history("审判长", self.case_data['defendant_information']+"被告人，刚才所宣读的你的身份情况属实吗？", interrupt_flag = 0, now_stage="Preparation")
        self.add_to_history("被告人", "属实。", interrupt_flag = 3, now_stage="Preparation")
        self.add_to_history("审判长", "你是否是中共党员、人大代表、政协委员或国家公职人员？或其他政治身份？", interrupt_flag = 0, now_stage="Preparation")
        self.add_to_history("被告人", self.get_response(self.defendant, self.case_data['defendant_information']+"\n这是你的身份信息，你要回答审判长最后的一个问题，即关于你的身份。回答‘不是’，或者‘我是[]’，其中[]里面是你的身份。"), interrupt_flag = 3, now_stage="Preparation")
        self.add_to_history("审判长", "被告人，你历史上是否受过其他法律处分？", interrupt_flag = 0, now_stage="Preparation")
        self.add_to_history("被告人", self.get_response(self.defendant, self.case_data['defendant_information']+"\n这是你的身份信息，你要回答审判长最后的一个问题，即你受到的其他法律处分。注意是之前已经受到的处分，而本次庭审还未结案。如果没有，回复‘我没有受过其他法律处分。’，如果有，则说出收到的处分。这个问题你必须要诚实回答。",simple=5), interrupt_flag = 3, now_stage="Preparation")

        
        self.add_to_history("审判长", "被告人，检察院的起诉书副本你收到了吗？", interrupt_flag = 0, now_stage="Preparation")
        self.add_to_history("被告人", "收到了。", interrupt_flag = 3, now_stage="Preparation")
        
        # 宣读法庭开庭
        self.add_to_history("审判长",self.get_response(self.judge,"起诉书："+self.case_data['prosecution_statement']+"""
                                                    请根据起诉书，介绍本次法庭庭审内容与出庭人员。
                                                    【示例】：
                                                    依照中华人民共和国刑事诉讼法的有关规定，本院今天依照公诉案件第一审普通程序，依法公开开庭审理由海口市人民检察院提起公诉，指控的被告人潘XX犯走私普通货物罪一案。本案由曾XX就是我本人担任审判长，书记员吴XX负责本案的程序性工作和法庭记录，海口市人民检察院指派检察官胡XX出庭支持公诉。被告人潘XX及其辩护人周XX到庭参加诉讼。
                                                    
                                                    
                                                    【注意】
                                                    1.按照示例中的结构进行表述。
                                                    2.人名从起诉书中提取，如果没有提及，则用XXX代替。检察院，法院的名称也从起诉书中提取，如果没有提及，则用XXX代替。
                                                    3.当前你在法庭上发言，所以直接返回类似示例中的表述，不要说多余的话。
                                                    4.如果没有明确表明是简易程序,则使用普通程序审理.
                                                    """,simple=5),interrupt_flag = 0, now_stage="Preparation")
        
        # * 审判长宣布诉讼权利
        self.add_to_history("审判长", self.config["defendant_rights"]+"被告人，以上本庭宣布的各项诉讼权利，你都听清楚了吗？", interrupt_flag = 0, now_stage="Preparation")
        self.add_to_history("被告人", "听清楚了。", interrupt_flag = 3, now_stage="Preparation")
        
        # * 审判长询问被告人是否申请回避
        self.add_to_history("审判长", "你是否申请审判长、书记员、公诉人回避？", interrupt_flag = 0, now_stage="Preparation")
        self.add_to_history("被告人", "不申请。", interrupt_flag = 3, now_stage="Preparation")

        self.add_to_history("审判长", "辩护人，你是否申请回避？", interrupt_flag = 0, now_stage="Preparation")
        self.add_to_history("辩护人", "不申请。", interrupt_flag = 3, now_stage="Preparation")
        
        self.add_to_history("审判长", "公诉人，你对庭前准备有没有意见？", interrupt_flag = 0, now_stage="Preparation")
        self.add_to_history("公诉人", "无意见。", interrupt_flag = 3, now_stage="Preparation")
        
        
        # self.add_to_history("审判长", "被告人，公诉人向本庭提供了你与公诉机关签署的认罪认罚具结书。根据认罪认罚从宽制度的有关规定，人民法院对认罪认罚的被告人可依法从宽处理。该认罪认罚具结书是不是你在值班律师在场的情况下自愿签署的？", interrupt_flag = 0, now_stage="Preparation")
        # self.add_to_history("被告人", "是。", interrupt_flag = 3, now_stage="Preparation")
        # self.add_to_history("审判长", "你是否知悉认罪认罚的法律后果？", interrupt_flag = 0, now_stage="Preparation")
        # self.add_to_history("被告人", "是。", interrupt_flag = 3, now_stage="Preparation")
        
    def investigation_stage(self):
        # self.update_stage_backend(1)
        self.set_instruction("Court_investigation")
        # * 公诉人宣读起诉书
        self.add_to_history("审判长", "现在开始法庭调查。由公诉人宣读起诉书。", interrupt_flag = 0, now_stage="Court_investigation")
        self.add_to_history("公诉人", self.case_data['prosecution_statement']+"审判长，起诉书宣读完毕。", interrupt_flag = 3, now_stage="Court_investigation")
        self.add_to_history("审判长", "被告人，公诉人刚才宣读的起诉书你听清楚了吗？", interrupt_flag = 0, now_stage="Court_investigation")
        self.add_to_history("被告人", "听清楚了。", interrupt_flag = 3, now_stage="Court_investigation")

        # * 审判长询问被告人是否对起诉书有异议
        # self.add_to_history("审判长", "你对起诉指控的犯罪事实有无异议？", interrupt_flag = 0, now_stage="Court_investigation")
        # self.add_to_history("被告人", "无异议。", interrupt_flag = 3, now_stage="Court_investigation")
        
        renfa=self.get_response(self.judge,"请判断证据材料和起诉书中，是否表明被告人签署了认罪认罚具结书（写明了被告人认罪认罚也是签署了），如果签署了，返回一个字‘是’，否则返回一个字‘否’")
        
        renfa_final=True
        if renfa[0]=='是':
            self.add_to_history("审判长","本院受理本案时，公诉机关同时向本院移送了关于被告人的认罪认罚具结书。被告人，你是否是自愿签署的认罪认罚具结书？",interrupt_flag = 0, now_stage="Court_investigation")
            self.add_to_history("被告人","是自愿的。",interrupt_flag = 3, now_stage="Court_investigation")
            self.add_to_history("审判长","有没有因受到暴力威胁、引诱等非法方法而违背意愿认罪认罚？",interrupt_flag = 0, now_stage="Court_investigation")
            self.add_to_history("被告人","没有。",interrupt_flag = 0, now_stage="Court_investigation")
            self.add_to_history("审判长","你签署具结书时，是否有律师在场为你提供法律帮助？",interrupt_flag = 0, now_stage="Court_investigation")
            self.add_to_history("被告人","有的。",interrupt_flag = 3, now_stage="Court_investigation")
            self.add_to_history("审判长","我院是否向你告知认罪认罚的权利和义务以及可能导致的法律后果？",interrupt_flag = 0, now_stage="Court_investigation")
            self.add_to_history("被告人","告知了。",interrupt_flag = 3, now_stage="Court_investigation")
        else:
            self.add_to_history("审判长","你对起诉指控的犯罪事实有无异议？是否认罪认罚？",interrupt_flag = 0, now_stage="Court_investigation")
            self.add_to_history("被告人",self.get_response(self.defendant, "结合你的个人信息、诉求、防御策略，回答审判长的问题，即你是否认罪认罚。"), interrupt_flag = 3, now_stage="Court_investigation")
            reply=self.get_response(self.judge, "如果被告人刚才表示认罪认罚，则询问被告人为何没有在开庭前签署认罪认罚具结书；如果被告人没有认罪认罚，则返回一个字‘否’。")
            if reply[0]!='否':
                self.add_to_history("审判长",reply,interrupt_flag = 0, now_stage="Court_investigation")
                self.add_to_history("被告人", self.get_response(self.defendant, "结合你的个人信息、诉求、防御策略，回答审判长的问题。"), interrupt_flag = 3, now_stage="Court_investigation")
            else:
                renfa_final=False
        
        if renfa_final:
            self.add_to_history("审判长", "被告人，你可以对起诉指控的犯罪事实及量刑事实向法庭进行陈述。你有没有需要陈述的？", interrupt_flag = 0, now_stage="Court_investigation")
            self.add_to_history("被告人", self.get_response(self.defendant, self.case_data['prosecution_statement']+"这是针对你的起诉书，你要直接回答，有没有需要陈述的。如果有要陈述的，可以进行陈述，包括翻供，或者认罪悔改等。如果没有要陈述的，就回复‘没有要陈述的’。注意，你的陈述要符合被告人的身份，不要把自己的策略直接说出来。"), interrupt_flag = 3, now_stage="Court_investigation")

        self.add_to_history("审判长", "辩护人，对起诉书有没有意见？", interrupt_flag = 0, now_stage="Court_investigation")
        self.add_to_history("辩护人", self.get_response(self.advocate, self.case_data['prosecution_statement']+"这是针对辩护人的起诉书，法官在问你有没有意见，请回复。你可以选择此时叙述你的意见，也可以等后面再叙述。如果没有意见，回复‘没有意见。’即可。"), interrupt_flag = 3, now_stage="Court_investigation")

        
        # * 公诉人讯问被告
        self.add_to_history("审判长", "公诉人对被告人有无讯问？", interrupt_flag = 0, now_stage="Court_investigation")
        response=self.get_response(self.prosecution, 
                                   """
                                   你是公诉人，在讯问环节中，你可以选择是否进入讯问环节来讯问被告。
                                   **注意！提供的备选问题仅供参考，请结合当前庭审情况决定当前要提问的问题。一次提出一个问题，其他问题可以等到后面再问。**
                                   **注意！提问的问题不要和之前自己提问的问题重复!**
                                   **注意！提问的问题不要和之前自己提问的问题重复!没有需要问的，就回复‘否’即可。**
                                   如果选择讯问，回复“是，”后提出1个要讯问的问题；如果选择停止讯问，回复一个字‘否’。"""
                                   ,simple=3)
            
        if response[0]=='是':
            self.add_to_history("公诉人", response[2:], interrupt_flag = 2, now_stage="Court_investigation")
            flag = 0
            while True:
                response_judge=self.get_response(self.judge, "目前是讯问环节，你是审判长，目前公诉人问了1个问题，请判断这个问题是否合适，比如是否和本案相关，或者是否与之前问题重复。不相关或者重复的问题都不合适。非特殊情况可以认为问题是合适的。如果合适，回复“是，”，如果明显不合适，回复‘否，’后说明理由。",simple=4)
                # 审判长检查问题是否明显不合适
                if response_judge[0]=='否':
                    if flag == 1:
                        self.add_to_history("审判长", response_judge[2:]+"公诉人不用再问了。", interrupt_flag = 1, now_stage="Court_investigation")
                        break
                    flag = 1
                    self.add_to_history("审判长", response_judge[2:]+"请公诉人重新提问。", interrupt_flag = 1, now_stage="Court_investigation")
                    # 重新提问
                    response=self.get_response(self.prosecution, "你是公诉人，你的问题被审判长认为不合适，请重新提问。直接给出你的提问即可。")
                    self.add_to_history("公诉人", response, interrupt_flag = 2, now_stage="Court_investigation")
                    continue
                
                # 被告回答问题
                self.add_to_history("被告人", self.get_response(self.defendant, "目前是讯问环节，你是被告，现在你需要回复公诉人刚才向你提出的问题。"), interrupt_flag = 2, now_stage="Court_investigation")
                
                # 审判长判断是否需要进一步讯问
                # response=self.get_response(self.judge, "目前是讯问环节，你是审判长，目前公诉人已经问了一些问题，你认为公诉人是否还有必要继续询问。如果当公诉人已经多次提问实质重复的问题的时候，就应当打断；否则可以让公诉人继续问下去。原则上不需要打断公诉人。如果你认为公诉人可以继续问，回复“是，”；如果你认为公诉人没有必要再问了，回复“否，公诉人不用再问了，”后简要说明理由。",simple=4)                  
                # if response[0]=='否':
                #     self.add_to_history("审判长", response[2:], interrupt_flag = 1, now_stage="Court_investigation")
                #     break
                
                # 公诉人提出下一个问题
                response = self.get_response(self.prosecution, 
                                             """
                                   你是公诉人，在法庭调查环节，你已经问了一些问题，是否还要问其他的问题？
                                   **注意！提供的备选问题仅供参考，请结合当前庭审情况决定当前要提问的问题。一次提出一个问题，其他问题可以等到后面再问。**
                                   **注意！提问的问题不要和之前自己提问的问题重复!**
                                   **注意！根据被告人的回答，如果有新的疑点问题，一定要问!!!!**
                                   **注意！提问的问题不要和之前自己提问的问题重复!没有需要问的，就回复‘否’即可。**
                                   如果选择讯问，回复“是，”后提出1个要讯问的问题；如果选择停止讯问，回复一个字‘否’。""",simple=3)
                
                if response[0]=='是':
                    response=response[2:]
                    if self.repeat(response)==True:
                        response='否'
                    
                if response[0]=='否':
                    self.add_to_history("公诉人", "审判长，我没有需要讯问的问题了。", interrupt_flag = 0, now_stage="Court_investigation")
                    self.add_to_history("审判长", "好的，公诉人讯问结束。", interrupt_flag = 0, now_stage="Court_investigation")
                    break
                
                self.add_to_history("公诉人", response, interrupt_flag = 2, now_stage="Court_investigation")
        else:
            self.add_to_history("公诉人", "没有需要讯问的。", interrupt_flag = 3, now_stage="Court_investigation")
        
        # * 辩护人讯问被告
        self.add_to_history("审判长", "辩护人对被告人有无讯问？", interrupt_flag = 0, now_stage="Court_investigation")
        response=self.get_response(self.advocate, """
                                   你是辩护人，在讯问环节中，你可以选择是否进入讯问环节来讯问被告。
                                   **注意！提供的备选问题仅供参考，请结合当前庭审情况决定当前要提问的问题。一次提出一个问题，其他问题可以等到后面再问。**
                                   **注意！提问的问题不要和之前自己提问的问题重复!也不要和公诉人提问的问题重复！**
                                   **注意！根据被告人的回答，如果有新的疑点问题，一定要问!!!!**
                                   如果选择讯问，回复“是，”后提出1个要讯问的问题；如果选择停止讯问，回复一个字‘否’。""",simple=3) 
        if response[0]=='是':
            self.add_to_history("辩护人", response[2:], interrupt_flag = 2, now_stage="Court_investigation")
            flag = 0
            while True:
                response_judge=self.get_response(self.judge, "目前是讯问环节，你是审判长，目前辩护人问了1个问题，请判断这个问题是否合适，比如是否和本案相关，或者是否与之前问题重复。不相关或者重复的问题都不合适。非特殊情况可以认为问题是合适的。如果合适，回复‘是，’，如果明显不合适，回复‘否，’后说明理由。",simple=4)
                # 审判长检查问题是否明显不合适
                if response_judge[0]=='否':
                    if flag == 1:
                        self.add_to_history("审判长", response_judge[2:]+"辩护人不用再问了。", interrupt_flag = 1, now_stage="Court_investigation")
                        break
                    flag = 1
                    self.add_to_history("审判长", response_judge[2:]+"请辩护人重新提问。", interrupt_flag = 1, now_stage="Court_investigation")
                    # 重新提问
                    response=self.get_response(self.advocate, "你是辩护人，你的问题被审判长认为不合适，请重新提问。直接给出你的提问即可。")
                    self.add_to_history("辩护人", response, interrupt_flag = 2, now_stage="Court_investigation")
                    continue
                
                # 被告回答问题
                self.add_to_history("被告人", self.get_response(self.defendant, "目前是讯问环节，你是被告，现在你需要回复辩护人刚才向你提出的问题。",simple=4), interrupt_flag = 2, now_stage="Court_investigation")
                
                # 审判长判断是否需要进一步讯问
                # response=self.get_response(self.judge, "目前是讯问环节，你是审判长，目前辩护人已经问了一些问题，你认为辩护人是否还有必要继续询问。如果当辩护人已经多次提问实质重复的问题的时候，就应当打断；否则可以让辩护人继续问下去。原则上不需要打断辩护人。如果你认为辩护人可以继续问，回复“是，”；如果你认为辩护人没有必要再问了，回复“否，辩护人不用再问了，”后简要说明理由。",simple=4)                  
                # if response[0]=='否':
                #     self.add_to_history("审判长", response[2:], interrupt_flag = 1, now_stage="Court_investigation")
                #     break
                
                # 辩护人提出下一个问题
                response = self.get_response(self.advocate, """
                                   你是辩护人，你已经问了一些问题，是否要继续进行询问？
                                   **注意！提供的备选问题仅供参考，请结合当前庭审情况决定当前要提问的问题。一次提出一个问题，其他问题可以等到后面再问。**
                                   **注意！提问的问题不要和之前自己提问的问题重复!也不要和公诉人提问的问题重复！**
                                   **注意！根据被告人的回答，如果有新的疑点问题，一定要问!!!!**
                                   如果选择讯问，回复“是，”后提出1个要讯问的问题；如果选择停止讯问，回复一个字‘否’。""",simple=3)
                if response[0]=='是':
                    response=response[2:]
                    if self.repeat(response)==True:
                        response='否'
                        
                if response[0]=='否':
                    self.add_to_history("辩护人", "审判长，我没有需要讯问的问题了。", interrupt_flag = 0, now_stage="Court_investigation")
                    self.add_to_history("审判长", "好的，辩护人讯问结束。", interrupt_flag = 0, now_stage="Court_investigation")
                    break
                
                self.add_to_history("辩护人", response, interrupt_flag = 2, now_stage="Court_investigation")
        else:
            self.add_to_history("辩护人", "没有需要讯问的。", interrupt_flag = 3, now_stage="Court_investigation")

        #--------------------------------审判长提问
        response=self.get_response(self.judge, 
                                   """你是审判长，你要查明案件事实。在讯问环节中，如果你认为公诉人和辩护人有问题没有问清楚，可以选择进入讯问环节来讯问被告。
                                   **注意！提问的问题不要和之前自己提问的问题重复!也不要和公诉人、辩护人提问的问题重复！**
                                   **注意！根据被告人的回答，如果有新的疑点问题，一定要问!!!!**
                                   请结合当前庭审记录、拟定的辩论焦点以及当前的查明情况来决定是否询问。如果选择讯问，回复‘是，’后提出1个要讯问的问题；如果不询问，回复一个字‘否’。""",simple=3) 
        if response[0]=='是':
            if response[2:] in self.all_pure_content:
                response='否'
        if response[0]=='是':
            self.add_to_history("审判长", response[2:], interrupt_flag = 0, now_stage="Court_investigation")
            flag = 0
            round=0
            while True:
                # 被告回答问题
                self.add_to_history("被告人", self.get_response(self.defendant, "目前是讯问环节，你是被告，现在你需要回复审判长刚才向你提出的问题。"), interrupt_flag = 2, now_stage="Court_investigation")
                round+=1
                if round==5:
                    break
                # 审判长判断是否需要进一步讯问
                response=self.get_response(self.judge, "目前是讯问环节，你是审判长，目前你已经问了一些问题，你是否还有要继续询问的？**注意！提问的问题不要和之前自己提问的问题重复!!也不要和公诉人、辩护人提问的问题重复！!****查明即可，不要问太多问题！****注意！根据被告人的回答，如果有新的疑点问题，一定要问!!!!**如果你想继续询问，回复‘是，’后提出1个要讯问的问题；如果选择停止讯问，回复一个字‘否’。",simple=3)                  
                if response[0]=='是':
                    response=response[2:]
                    if self.repeat(response)==True:
                        response='否'
                if response[0]=='否':
                    break
                
                self.add_to_history("审判长", response, interrupt_flag = 2, now_stage="Court_investigation")
            self.add_to_history("审判长", "好的，法庭调查环节结束。", interrupt_flag = 0, now_stage="Court_investigation")
        else:
            self.add_to_history("审判长", "法庭调查环节结束。", interrupt_flag = 0, now_stage="Court_investigation")
                    

    def Presentation_of_evidence(self):
        # self.update_stage_backend(2)
        self.set_instruction("Presentation_of_evidence")
        
        # * 公诉人举证环节
        self.add_to_history("审判长", "下面进入举证质证环节，首先由公诉人就案件事实向法庭综合举证，可以仅就证据的名称及所证明的事项作出说明。对于控辩双方有异议，或者法庭认为有必要调查核实的证据，可以当庭进行质证。质证请围绕证据的真实性，关联性，合法性进行论证。", interrupt_flag = 0, now_stage="Presentation_of_evidence")
        
        # case_data["evidence"][0] 是公诉人的证据
        evidence=[self.case_data["evidence"][0]]
        # * 公诉人宣读证据
        if len(evidence)>0:
            self.add_to_history("公诉人", "审判长，公诉人要求出示以下证据：", interrupt_flag = 3, now_stage="Presentation_of_evidence")
            for index in range(len(evidence)):
                self.add_to_history("公诉人",evidence[index]+"请法庭组织质证。", interrupt_flag = 3, now_stage="Presentation_of_evidence")
                # response=self.get_response(self.prosecution,f"目前是举证质证环节，你要出示的证据是'{evidence[index]}'，请把它念出来，并指出所证实的事实。（如果证据里本身就说明了证实内容，就不用再说了）")
                self.update_evidence(evidence[index],0)
                # self.add_to_history("公诉人",response, interrupt_flag = 3, now_stage="Presentation_of_evidence")
                # * 被告人质证
                self.add_to_history("审判长", "被告人，对公诉人出示的上述证据有无异议？", interrupt_flag = 0, now_stage="Presentation_of_evidence")
                self.add_to_history("被告人", 
                                    self.get_response(self.defendant,
                                    "你是被告人，公诉人刚才出示了证据，现在你要对公诉人刚才出示的证据表达自己的看法。你可以发表异议，也可以表示‘没有异议’。如果要发表异议，那么尽可能围绕证据表述的事实、和自己眼中的事实展开。通常情况下，可以表示‘没有异议’，让辩护人代为质证。"),
                                    interrupt_flag = 3, 
                                    now_stage="Presentation_of_evidence")
                # self.get_response(self.defendant, "你是被告人，对公诉人出示的上述证据有无异议？请根据证据的关联性质证，即如果你认为该证据与本案无关，则可以提出异议。如果有异议，回复“有”后继续提出对证据的质疑；如果没有，回复‘没有’"), 
                
                # * 辩护人质证
                self.add_to_history("审判长", "辩护人，对公诉人出示的上述证据有无异议？", interrupt_flag = 0, now_stage="Presentation_of_evidence")
                response=self.get_response(self.advocate, 
                                           """
                                           你是辩护人，对公诉人出示的上述证据有无异议？请根据证据的关联性质证，
                                           即如果你认为该证据与本案无关，则可以提出异议；或者如果认为该证据证明效力不够，无法证明相应的结论，则可以提出异议。
                                           
                                           注意！！
                                           **1.所有的证据检查机关都查证了，所有证据的取得都是合理合法的，都具备有关部门的公章，取得流程符合规定，真实性、合法性无需质证！**
                                           **2.所有的监控、图文资料的取得也都是合法的，并且足够清楚，其内容完全符合公诉人的描述，对这一点不需要质疑。**
                                           **3.对于关联性，只要质疑证据本身和公诉人提出的证明内容是否有关即可，一条证据本身也许无法证明被告人的犯罪事实，但只要证据和公诉人的证明内容有关，就不需要质证。**
                                           **4.注意，某些证据可能和案件并非直接相关，只是描述一些背景信息，这些也不需要质证！**
                                           **5.你也可以表示对证据的三性没有异议，但对证据的证明效力做出质疑，或者发表你对于法庭证据采信的建议。**
                                           
                                           通常情况下，证据在庭前都经过了充分讨论，你无需质证。
                                           
                                           如果有异议，回复“有，”后继续提出对证据的质疑；如果没有，回复‘没有’。
                                           
                                           """
                                           ), 
                # print("RESPONSE",response,type(response),response[0])
                if isinstance(response, tuple): # 非常奇怪，不知道为什么在询问质证意见的时候回复会变成tuple，而其他时候就没事。
                    print("HIT")
                    response=response[0] 
                if response[0]=='有':                 
                    self.add_to_history("辩护人", response[2:],
                                        interrupt_flag = 3, 
                                     now_stage="Presentation_of_evidence")
                    
                    
                    self.add_to_history("审判长", "公诉人，辩护人对证据提出了异议，你是否要进行回复？", interrupt_flag = 0, now_stage="Presentation_of_evidence")
                    response=self.get_response(self.prosecution, "你是公诉人，辩护人对你最新提出的证据有异议，你是否要进行回复？如果要回复，回复“有，”后继续提出你的回复；如果没有，回复‘没有’")
                    if response[0]=='有':
                        self.add_to_history("公诉人", response[2:],
                                        interrupt_flag = 3, 
                                     now_stage="Presentation_of_evidence")
                        while True:
                            response=self.get_response(self.judge, "你是审判长，这条证据控辩双方已经进行了一些辩论，你认为是否还需要进行辩论？当事情观点已经表达清楚，为了避免重复，就不用说了，否则可以继续说。如果还需要辩论，回复“是，”；如果没有，回复‘否，’后对这次打断的原因做一个简单的解释。不要说多余的话！",simple=4) #，比如'可以了，这条证据已经讨论地足够清楚了。'
                            if response[0]=='是':
                                pass
                            else:
                                if response[0]=='否':
                                    response=response[2:]
                                self.add_to_history("审判长", response,
                                        interrupt_flag = 1, 
                                     now_stage="Presentation_of_evidence")
                                break
                            
                            self.add_to_history("审判长", "辩护人还有什么想说的？", interrupt_flag = 0, now_stage="Presentation_of_evidence")
                            response=self.get_response(self.advocate, "你是辩护人，对于这条证据以及公诉人的回复，你还有什么想说的？当事情观点已经表达清楚，为了避免重复，就不用说了，否则可以继续说。如果有，回复“有，”后继续提出你的回复；如果没有，回复‘没有想说的了，’后继续对该证据简单做一个自己观点上的总结。"), 
                            if response[0]=='有':
                                self.add_to_history("辩护人", response[2:],
                                        interrupt_flag = 3, 
                                     now_stage="Presentation_of_evidence")
                            else:
                                self.add_to_history("辩护人", response,
                                        interrupt_flag = 3, 
                                     now_stage="Presentation_of_evidence")
                                break
                            
                            self.add_to_history("审判长", "公诉人还有什么想说的？", interrupt_flag = 0, now_stage="Presentation_of_evidence")
                            response=self.get_response(self.prosecution, "你是公诉人，对于这条证据以及辩护人的回复，你还有什么想说的？当事情观点已经表达清楚，为了避免重复，就不用说了，否则可以继续说。如果有，回复“有，”后继续提出你的回复；如果没有，回复‘没有想说的了，’后继续对该证据简单做一个自己观点上的总结。"), 
                            if response[0]=='有':
                                self.add_to_history("公诉人", response[2:],
                                        interrupt_flag = 3, 
                                     now_stage="Presentation_of_evidence")
                            else:
                                self.add_to_history("公诉人", response,
                                        interrupt_flag = 3, 
                                     now_stage="Presentation_of_evidence")
                                break
                            
                    else:
                        self.add_to_history("公诉人","我没有要回复的。", interrupt_flag = 3, now_stage="Presentation_of_evidence")
                else:
                    self.add_to_history("辩护人","没有异议。", interrupt_flag = 3, now_stage="Presentation_of_evidence")
                
                self.add_to_history("审判长","公诉人请出示下一条证据。", interrupt_flag = 0, now_stage="Presentation_of_evidence") 
                # * 公诉人存在下一条证据？
                if index >= len(evidence)-1:
                    self.add_to_history("公诉人", "证据出示完毕。", interrupt_flag = 3, now_stage="Presentation_of_evidence")
        else:
            self.add_to_history("公诉人", "公诉人没有证据需要出示。", interrupt_flag = 3, now_stage="Presentation_of_evidence")

        # * 辩护人举证环节
        self.add_to_history("审判长", "下面由辩护人就案件事实向法庭综合举证，可以仅就证据的名称及所证明的事项作出说明，对控辩双方有异议，或者法庭认为有必要调查核实的证据，应当出示并进行质证。", interrupt_flag = 0, now_stage="Presentation_of_evidence")
        # * 辩护人宣读证据
        # ["evidence"][1]是辩护人的证据
        evidence=[self.case_data["evidence"][1]]
        if len(evidence)>0:
            self.add_to_history("辩护人", "审判长，辩护人要求出示以下证据予以证实：", interrupt_flag = 3, now_stage="Presentation_of_evidence")
            for index in range(len(evidence)):
                self.add_to_history("辩护人",
                                    self.get_response(self.advocate, "当前你打算出示的证据内容为："+evidence[index]+"你要把这份证据【在法庭上念出来】，并指出证据【所证实的事实、出示这份证据的理由、证明的目的】。即，解释这个证据是如何体现被告人罪轻或无罪或可以酌情减轻处罚之处。（如果证据里本身就说明了证实内容，就不用再说了）如果有多条内容，则念出每一条内容后，都要说明一下证明了什么，便于更好地阐述观点。")
                                    , interrupt_flag = 3, now_stage="Presentation_of_evidence")
                # response=self.get_response(self.advocate,f"目前是举证质证环节，你要出示的证据是'{evidence[index]}'，请把它念出来，并指出所证实的事实。（如果证据里本身就说明了证实内容，就不用再说了）")
                self.update_evidence(evidence[index],1)
                # self.add_to_history("辩护人",response, interrupt_flag = 3, now_stage="Presentation_of_evidence")
                # * 公诉人质证
                self.add_to_history("审判长", "公诉人，对辩护人出示的上述证据有无异议？", interrupt_flag = 0, now_stage="Presentation_of_evidence")
                
                response=self.get_response(self.prosecution, 
                                           """
                                           你是公诉人，对辩护人出示的上述证据有无异议？请根据证据的关联性质证，
                                           即如果你认为该证据与本案无关，则可以提出异议；或者如果认为该证据证明效力不够，无法证明相应的结论，则可以提出异议。
                                           
                                           注意！！
                                           **1.所有的证据检查机关都查证了，所有证据的取得都是合理合法的，都具备有关部门的公章，取得流程符合规定，真实性、合法性无需质证！**
                                           **2.所有的监控、图文资料的取得也都是合法的，并且足够清楚，其内容完全符合公诉人的描述，对这一点不需要质疑。**
                                           如果有异议，回复“有，”后继续提出对证据的质疑；如果没有，回复‘没有’
                                           **3.注意，某些证据可能和案件并非直接相关，只是描述一些背景信息，这些也不需要质证！**
                                           **4.你也可以表示对证据的三性没有异议，但对证据的证明效力做出质疑，或者发表你对于法庭证据采信的建议。**
                                           
                                           
                                           通常情况下，证据在庭前都经过了充分讨论，你无需质证。
                                           如果有异议，回复“有，”后继续提出对证据的质疑；如果没有，回复‘没有’
                                           """), 
                if isinstance(response, tuple): # 非常奇怪，不知道为什么在询问质证意见的时候回复会变成tuple，而其他时候就没事。
                    print("HIT")
                    response=response[0] 
                if response[0]=='有':                 
                    self.add_to_history("公诉人", response[2:],
                        interrupt_flag = 3, now_stage="Presentation_of_evidence")
                    
                    self.add_to_history("审判长", "辩护人，公诉人对证据提出了异议，你是否要进行回复？", interrupt_flag = 0, now_stage="Presentation_of_evidence")
                    response=self.get_response(self.advocate, "你是辩护人，公诉人对你最新提出的证据有异议，你是否要进行回复？如果要回复，回复“有，”后继续提出你的回复；如果没有，回复‘没有’")
                    if response[0]=='有':
                        self.add_to_history("辩护人", response[2:],
                                        interrupt_flag = 3, 
                                     now_stage="Presentation_of_evidence")
                        while True:
                            response=self.get_response(self.judge, "你是审判长，这条证据控辩双方已经进行了一些辩论，你认为是否还需要进行辩论？当事情观点已经表达清楚，为了避免重复，就不用说了，否则可以继续说。如果还需要辩论，回复“是，”；如果没有，回复‘否，’后对这次打断的原因做一个简单的解释。不要说多余的话！",simple=4) #，比如'可以了，这条证据已经讨论地足够清楚了。'
                            if response[0]=='是':
                                pass
                            else:
                                if response[0]=='否':
                                    response=response[2:]
                                self.add_to_history("审判长", response,
                                        interrupt_flag = 1, 
                                     now_stage="Presentation_of_evidence")
                                break
                            
                            self.add_to_history("审判长", "公诉人还有什么想说的？", interrupt_flag = 0, now_stage="Presentation_of_evidence")
                            response=self.get_response(self.prosecution, "你是公诉人，对于这条证据以及辩护人的回复，你还有什么想说的？当事情观点已经表达清楚，为了避免重复，就不用说了，否则可以继续说。如果有，回复“有，”后继续提出你的回复；如果没有，回复‘没有想说的了，’后继续对该证据简单做一个自己观点上的总结。"), 
                            if response[0]=='有':
                                self.add_to_history("公诉人", response[2:],
                                        interrupt_flag = 2, 
                                     now_stage="Presentation_of_evidence")
                            else:
                                self.add_to_history("公诉人", response,
                                        interrupt_flag = 2, 
                                     now_stage="Presentation_of_evidence")
                                break
                            
                            self.add_to_history("审判长", "辩护人还有什么想说的？", interrupt_flag = 0, now_stage="Presentation_of_evidence")
                            response=self.get_response(self.advocate, "你是辩护人，对于这条证据以及公诉人的回复，你还有什么想说的？当事情观点已经表达清楚，为了避免重复，就不用说了，否则可以继续说。如果有，回复“有，”后继续提出你的回复；如果没有，回复‘没有想说的了，’后继续对该证据简单做一个自己观点上的总结。"), 
                            if response[0]=='有':
                                self.add_to_history("辩护人", response[2:],
                                        interrupt_flag = 2, 
                                     now_stage="Presentation_of_evidence")
                            else:
                                self.add_to_history("辩护人", response,
                                        interrupt_flag = 2, 
                                     now_stage="Presentation_of_evidence")
                                break
                            
                    else:
                        self.add_to_history("辩护人","我没有要回复的。", interrupt_flag = 3, now_stage="Presentation_of_evidence")
                else:
                    self.add_to_history("公诉人","没有异议。", interrupt_flag = 3, now_stage="Presentation_of_evidence")
                
                self.add_to_history("审判长","辩护人请出示下一条证据。", interrupt_flag = 0, now_stage="Presentation_of_evidence") 
                # * 辩护人存在下一条证据？
                if index >= len(evidence)-1:
                    self.add_to_history("辩护人", "证据出示完毕。", interrupt_flag = 3, now_stage="Presentation_of_evidence")
        else:
            self.add_to_history("辩护人", "辩护人没有证据需要出示。", interrupt_flag = 3, now_stage="Presentation_of_evidence")

        # * 被告人是否申请调取新的证据、通知新的证人到庭或申请法庭重新鉴定或勘验、检查？
        self.add_to_history("审判长", "被告人是否申请调取新的证据、通知新的证人到庭或申请法庭重新鉴定或勘验、检查？", interrupt_flag = 0, now_stage="Presentation_of_evidence")
        self.add_to_history("被告人", "不申请。", interrupt_flag = 3, now_stage="Presentation_of_evidence")

        
        
        #--------------------------------审判长提问
        response=self.get_response(self.judge, 
                                   """你是审判长，你要查明案件事实。
                                   在举证质证阶段，你也可以对被告人进行发问。
                                   【注意】
                                   1.你问的问题不要和法庭调查阶段重复！
                                   2.你问的问题不要和公诉人、辩护人提出的问题重复！
                                   3.你问的问题不要和自己之前的问题重复！
                                   
                                   请结合当前庭审记录、拟定的辩论焦点以及当前的查明情况来决定是否询问。如果选择讯问，回复‘是，’后提出1个要讯问的问题；如果不询问，回复一个字‘否’。""",simple=3) 
        if response[0]=='是':
            if response[2:] in self.all_pure_content:
                response='否'
        if response[0]=='是':
            self.add_to_history("审判长", response[2:], interrupt_flag = 0, now_stage="Presentation_of_evidence")
            flag = 0
            round=0
            while True:
                # 被告回答问题
                self.add_to_history("被告人", self.get_response(self.defendant, "目前是讯问环节，你是被告，现在你需要回复审判长刚才向你提出的问题。"), interrupt_flag = 2, now_stage="Presentation_of_evidence")
                round+=1
                if round==5:
                    break
                # 审判长判断是否需要进一步讯问
                response=self.get_response(self.judge, "目前是讯问环节，你是审判长，目前你已经问了一些问题，你是否还有要继续询问的？**注意！提问的问题不要和之前自己提问的问题重复!!也不要和公诉人、辩护人提问的问题重复！!****查明即可，不要问太多问题！****注意！根据被告人的回答，如果有新的疑点问题，一定要问!!!!**如果你想继续询问，回复‘是，’后提出1个要讯问的问题；如果选择停止讯问，回复一个字‘否’。",simple=3)                  
                if response[0]=='是':
                    response=response[2:]
                    if self.repeat(response)==True:
                        response='否'
                if response[0]=='否':
                    break
                
                self.add_to_history("审判长", response, interrupt_flag = 2, now_stage="Presentation_of_evidence")
            self.add_to_history("审判长", "通过刚才的举证和质证，对于控辩双方无异议的证据，本院予以认可。对有异议的证据待合议庭评议后综合进行评判。举证质证环节结束。", interrupt_flag = 0, now_stage="Presentation_of_evidence")
        else:
            self.add_to_history("审判长", "通过刚才的举证和质证，对于控辩双方无异议的证据，本院予以认可。对有异议的证据待合议庭评议后综合进行评判。举证质证环节结束。", interrupt_flag = 0, now_stage="Presentation_of_evidence")
        # * 举证阶段结束

    def debate_stage(self, ):
        # self.update_stage_backend(3)
        # （删掉了量刑建议）可以加公诉人量刑建议，暂时没有加。 "2.讨论量刑建议。是否应当按照起诉状中的刑期进行判决还是使用其他判决结果。这需要综合考虑"
        self.set_instruction("Court_debate")
        self.add_to_history("审判长", "现在进行法庭辩论。控辩双方应当围绕案件事实，证据，定罪量刑，法律适用进行辩论。首先由公诉人发表公诉意见。", interrupt_flag = 0, now_stage="Court_debate")

        # * 公诉人先发言
        self.add_to_history("公诉人", self.get_response(self.prosecution, "作为公诉人，你需要根据已展示的庭审记录、起诉状、证据、被告人信息等，对本案进行总体论述，力求公正定罪。直接返回你的发言内容。"
                                                     +"""【注意】：
                                                     1.开头先做一下简要介绍。例如：审判长，根据中华人民共和国刑事诉讼法第一百八十九条、第一百九十八条和第二百零九条的规定，我们受本院检察长的指派，代表本院以国家公诉人的身份出席本次法庭，支持公诉，并依法对刑事诉讼实行法律监督。
                                                     2.你的公诉意见应当至少包含【犯罪事实】、【定性罪名】、【量刑建议】，缺一不可，其中量刑建议可以是一个范围。
                                                     3.你的意见也应当融入前文的一些总结，对前文争议异议内容的回应。
                                                     4.你的意见还要包含你认可的被告人从重处罚、从轻处罚的情节。保持客观，你的目的是公正判罚被告人，有些从轻处罚情节是可以认可的。
                                                     5.你的公诉意见应当【全面】，且有理有据，发表观点的同时应当引用本案的证据、以及法庭中的发言内容。所有要说的指控观点一并论述出来。
                                                     6.在量刑建议方面，还要引用法律条文，这一点可以从起诉书中摘取。
                                                     7.最后你也可以对被告人进行适当的叮嘱与法庭教育，但不要说太多。
                                                     
                                                     你的内容分点不要用阿拉伯数字，用自然语言描述即可。例如第一、第二、首先、其次、最后，等等
                                                     
                                                     """), interrupt_flag = 3, now_stage="Court_debate")
        # 被告人发言
        self.add_to_history("审判长", "下面由被告人发表自行辩护意见。被告人，你有要发表的意见吗？", interrupt_flag = 0, now_stage="Court_debate")
        
        self.add_to_history("被告人", self.get_response(self.defendant, "现在是法庭辩论，你可以发表自行辩护意见，也可以不发表意见。"), interrupt_flag = 3, now_stage="Court_debate")
        
        
        # * 辩护人发言
        self.add_to_history("审判长", "下面由辩护人发表辩护意见。", interrupt_flag = 0, now_stage="Court_debate")
        
        self.add_to_history("辩护人", self.get_response(self.advocate, 
                                                     """作为辩护人，你需要根据已展示的庭审记录、起诉状、证据、被告人信息等，对本案进行总体论述，力求减轻罪情。直接返回你的发言内容。
                                                     
                                                     【注意】：
                                                     1.开头先做一下简要介绍。例如：尊敬的审判长、公诉人、书记员，XX律师事务所受本案被告人的委托，指派我担任XXX（被告人姓名）XXX罪一案的辩护人，现就本案事实依法作罪轻辩护。 或者如果是法院委托的例如：尊敬的审判长、公诉人、书记员，XX律师事务所受法院的委托，指派我担任XXX（被告人姓名）XXX罪一案的辩护人，现就本案事实依法作罪轻辩护。（也可以是做无罪辩护，取决于策略）
                                                     2.你的辩护意见应当至少包含【犯罪事实】、【定性罪名】、【量刑建议】，缺一不可，其中量刑建议可以是一个范围，或者简单的一个建议，如希望从轻，希望减少罚金，希望适用缓刑等。并且要注意逻辑，回应公诉人的意见。
                                                     3.你的意见也应当融入前文的一些总结，对前文争议异议内容的回应。
                                                     4.你的辩护意见应当全面，且有理有据，发表观点的同时应当引用本案的证据、以及法庭中的发言内容。所有要说的辩护观点一并论述出来。
                                                     5.在量刑建议方面，还要引用法律条文，这一点可以从起诉书中摘取。
                                                     6.不要仅自顾自地发言，要回应公诉人的意见。
                                                     
                                                     你的内容分点不要用阿拉伯数字，用自然语言描述即可。例如第一、第二、首先、其次、最后，等等
                                                     
                                                     """), interrupt_flag = 3, now_stage="Court_debate")

        # * 双方交替发言k轮
        epoch_num = 1  # 设定交替发言轮数
        for i in range(epoch_num):
            self.add_to_history("审判长", "公诉人是否还有补充的意见？", interrupt_flag = 0, now_stage="Court_debate")
            
            self.add_to_history("公诉人", self.get_response(self.prosecution, 
                                                         prompt_debate_prosecutor), interrupt_flag = 3, now_stage="Court_debate")
            
            self.add_to_history("审判长", "被告人是否还有补充的意见？", interrupt_flag = 0, now_stage="Court_debate")
            
            self.add_to_history("被告人", self.get_response(self.defendant, "现在是法庭辩论，你可以发表自行辩护意见，也可以不发表意见。注意，为了避免重复，如果你的意见都已经发表完毕了，直接回复没有其他意见即可。通常情况下，你可以不发表意见。"), interrupt_flag = 3, now_stage="Court_debate")
        
            
            self.add_to_history("审判长", "辩护人是否还有补充的意见？",interrupt_flag = 0, now_stage="Court_debate")
            self.add_to_history("辩护人", self.get_response(self.advocate, prompt_debate_advocate
                                                         ), interrupt_flag = 3, now_stage="Court_debate")

        # * 审判长检查辩论要点是否都已讨论
        additional_rounds = 5
        for _ in range(additional_rounds):
            response = self.get_response(self.judge, """作为审判长，法庭辩论环节是你【最后】查清案件事实的机会。请你根据【辩论焦点】、【查明情况】、【以及当前辩论中双方没有达成一致看法的要点】，思考是否还存在**关键的**、未查明的、且和案件有关的事实。
            如果有，你应当组织新的辩论焦点，以便查清案件事实。特别是你本来就认为需要进一步讨论的焦点，应当组织双方进行辩论。
            
            如果你认为还需要进行针对新的要点进行辩论，**请回复'是，'，并紧接着提出具体要点**；如果你认为不需要了（比如双方已经达成共识，或者你心里已有答案），请回复'否'。
            
            例如：
            （当你发现被告人是否自首是关键问题，但双方还没有达成一致）
            是，双方对被告人自首的认定还存在异议，请双方针对被告人是否自首进行进一步讨论。
            
            注意：
            1.法庭辩论环节是你【最后】查清案件事实的机会！对关键的且双方仍然有争议的部分一定要组织进一步的辩论！
            2.你当前要辩论的要点不能和之前辩论的要点重复！
            
            """)
            if response[0] == '是':
                new_focus = response[2:]
                self.add_to_history("审判长", self.get_response(self.judge,f"当前要讨论的焦点是‘{new_focus}’，请承上启下地引出这一个焦点，并让公诉人先发言。注意要说一句通顺的话。例如：方才控辩双方针对xxx已经发表了一些意见，接下来的辩论请围绕xxxx进行展开，由公诉人先发言。",simple=1), interrupt_flag = 0, now_stage="Court_debate")
                
                self.add_to_history("公诉人", self.get_response(self.prosecution, f"作为公诉人，请针对{new_focus}这一要点及辩护人的论述进行论述或回应。"), interrupt_flag = 3, now_stage="Court_debate")
                
                self.add_to_history("审判长", "下面由被告人发表自行辩护意见。被告人，你有要发表的意见吗？", interrupt_flag = 0, now_stage="Court_debate")
        
                self.add_to_history("被告人", self.get_response(self.defendant, f"现在是法庭辩论，你可以发表自行辩护意见，也可以不发表意见。请针对{new_focus}这一要点发表意见。"), interrupt_flag = 3, now_stage="Court_debate")
                    
                self.add_to_history("审判长", "下面由辩护人发表辩护意见。", interrupt_flag = 0, now_stage="Court_debate")
                
                self.add_to_history("辩护人", self.get_response(self.advocate, f"作为辩护人，请针对{new_focus}这一要点及公诉人的论述进行论述或回应。"), interrupt_flag = 3, now_stage="Court_debate")
                while True:
                    response = self.get_response(self.judge, f"目前讨论的焦点是：{new_focus}。作为审判长，请你根据最近的庭审记录，裁定该辩论焦点是否还需要继续讨论。如果已经讨论清楚，或者控辩双方的发言明显重复或没有进展，则不必继续讨论了。如果还需要讨论，请回复'是，'；如果不需要讨论，请回复'否'。",simple=4)
                    if response[0] == '否':
                        break
                        
                    self.add_to_history("审判长", "公诉人是否还有补充的意见？", interrupt_flag = 0, now_stage="Court_debate")
                    
                    self.add_to_history("公诉人", self.get_response(self.prosecution, f"作为公诉人，请针对{new_focus}这一要点及辩护人的论述进行论述或回应。"+prompt_debate_prosecutor), interrupt_flag = 3, now_stage="Court_debate")
                    
                    self.add_to_history("审判长", "被告人是否还有补充的意见？", interrupt_flag = 0, now_stage="Court_debate")
            
                    self.add_to_history("被告人", self.get_response(self.defendant, f"现在是法庭辩论，你可以发表自行辩护意见，也可以不发表意见。请针对{new_focus}这一要点发表意见。注意，为了避免重复，如果你的意见都已经发表完毕了，直接回复没有其他意见即可。通常情况下，你可以不发表意见。"), interrupt_flag = 3, now_stage="Court_debate")
                    
                    self.add_to_history("审判长", "辩护人是否还有补充的意见？",interrupt_flag = 0, now_stage="Court_debate")
                    
                    self.add_to_history("辩护人", self.get_response(self.advocate, f"作为辩护人，请针对{new_focus}这一要点及公诉人的论述进行论述或回应。"+prompt_debate_advocate), interrupt_flag = 3, now_stage="Court_debate")
            else:
                break
        
        # * 辩论阶段结束
        self.add_to_history("审判长", "经过法庭辩论，控辩双方均已充分发表意见，本庭已经听清并记录在案，合议庭在评议时会充分考虑。法庭辩论结束。", interrupt_flag = 0, now_stage="Court_debate")

    def statement_stage(self):
        # self.update_stage_backend(4)
        self.set_instruction("Defendant_statement")

        # * 被告人最后陈述
        self.add_to_history("审判长", "被告人，根据《刑事诉讼法》的有关规定，在法庭上你有权利就案件的事实，证据，罪情轻重做出最后的陈述。现在你可以进行陈述。", interrupt_flag = 0, now_stage="Defendant_statement")
        self.add_to_history("被告人", self.get_response(self.defendant, "当前是被告人陈述阶段，作为被告人，你要做出你的最后陈述，在你陈述后，审判长将给出最后的判决。请给出你的陈述，不要说多余的话。如果没有想说的，可以说‘我没有需要陈述的’。"), interrupt_flag = 3, now_stage="Defendant_statement")

        self.add_to_history("审判长", "本次庭审需要审理的全部事项已经完成。现对本案判决如下：", interrupt_flag = 0, now_stage="Defendant_statement")
        self.add_to_history("书记员", "全体起立！", interrupt_flag = 3, now_stage="Defendant_statement")
        
        # * 审判长给出判决
        judge_prompt=f"""
            案件基本信息：
            被告人信息：{self.case_data["defendant_information"]}
            起诉状：{self.case_data["prosecution_statement"]}
            公诉人出示的证据：{str(self.case_data["evidence"][0])} 
            辩护人出示的证据：{str(self.case_data["evidence"][1])}
            
            庭审即将结束，作为审判长，你要根据庭审记录、证据、起诉书、被告人信息、辩论焦点和事实查明等给出公正的判罚。
            **请你密切关注辩论焦点和事实查明的结果！**
            **请自行辨别被告人、公诉人、辩护人发言内容与案件真实情况的相关性与适用程度。**
            **注意，证据中未提及的赔偿、自首、谅解等内容，都应当视为不成立！无论双方是如何争执的**
            **注意，证据中未提及的犯罪情节内容，都应当视为不成立！无论双方是如何争执的**
            **请仔细思考，谨慎判罚！**
            
            #####
            
            【回复要求】
            你的回复应当以‘判决如下’开头，随后声明判决。
            （1）第一、定罪判刑的，表述为：
            “一、被告人×××犯××罪，判处……（写明主刑、附加刑）；
            二、被告人×××……（写明追缴、退赔或没收财物的决定，以及这些财物的种类和数额。没有的不写此项）。”
            （2）第二、定罪免刑的表述为：
            “被告人×××犯××罪，免予刑事处分（如有追缴、退赔或没收财物的，续写为第二项）。”
            （3）第三、宣告无罪的，表述为：
            “被告人×××无罪。”〕
            
            特别地，定罪判刑时，应当包含实刑，可能会包含缓刑、罚金。
            例如：
            判决如下：被告人张某犯xxx罪，判处拘役x个月，缓刑x个月，并处罚金人民币二千元。
            
            【注意事项】
            1.要给出具体的罪名，随后给出刑期。如果需要，要包含缓刑和赔偿、罚款金额。
            2.**注意！起诉书中提及实刑、缓刑、罚金等，但具体是否有罪，是否适用于缓刑，是否处以罚金等，需要你自己判断！**
              **如果认为不需要处罚实刑，不适用缓刑，或不处罚罚金，则不提及实刑，缓刑或罚金。不必完全依照起诉书**
            3.回复时直接给出你的判罚，不要说多余的话。
            """
        result=self.get_response(self.judge, judge_prompt,simple=2)
        self.result=result
        # self.panjue=format_panjue(result)
        
        book_prompt=f"""
            案件基本信息：
            被告人信息：{self.case_data["defendant_information"]}
            起诉状：{self.case_data["prosecution_statement"]}
            公诉人出示的证据：{str(self.case_data["evidence"][0])} 
            辩护人出示的证据：{str(self.case_data["evidence"][1])}

            【任务】
            请写出案件的判决书。
            
            判决书整体分为如下5个部分：
            ①法官查明信息项。包括被告，辩护人，起诉原因，程序性事实。包括姓名性别年龄学历。
            ②公诉机关指控。是起诉书中的起诉内容。（法官应当引导公诉人完整阐述指控事实和证据）
            ③法官应当引导被告人。最后使得他对指控犯罪事实、罪名及量刑建议没有异议，自愿认罪认罚且签字具结，在开庭审理过程中亦无异议。
            ④总结控辩双方发言中关于事实的共性部分（查明事实），控辩发言中法律适用的部分，（本院认为）（最后定论）
            ⑤最后判决。
            
            **其中，最后判决结果已经确定。**
            **判决结果是：{result}**
            
            【判决书格式】
            ××××人民法院
            刑事判决书
            （一审公诉案件用）
            （××××）×刑初字第××号
            公诉机关××××人民检察院。
            被告人……（写明姓名、性别、出生年月日、民族、籍贯、职业或工作单位和职务、住址和因本案所受强制措施情况等，现在何处）。
            辩护人……（写明姓名、性别、工作单位和职务）。
            ××××人民检察院于××××年××月××日以被告人×××犯××罪，向本院提起公诉。本院受理后，依法组成合议庭（或依法由审判员×××独任审判），公开（或不公开）开庭审理了本案。××××人民检察院检察长（或员）×××出庭支持公诉，被告人×××及其辩护人×××、证人×××等到庭参加诉讼。本案现已审理终结。
            ……（首先概述检察院指控的基本内容，其次写明被告人的供述、辩解和辩护人辩护的要点）。
            经审理查明，……（详写法院认定的事实、情节和证据。如果控、辩双方对事实、情节、证据有异议，应予分析否定。在这里，不仅要列举证据，而且要通过对主要证据的分析论证，来说明本判决认定的事实是正确无误的。必须坚决改变用空洞的“证据确凿”几个字来代替认定犯罪事实的具体证据的公式化的写法）。
            本院认为，……〔根据查证属实的事实、情节和法律规定，论证被告人是否犯罪，犯什么罪（一案多人的还应分清各被告人的地位、作用和刑事责任），应否从宽或从严处理。对于控、辩双方关于适用法律方面的意见和理由，应当有分析地表示采纳或予以批驳〕。依照……（写明判决所依据的法律条款项）的规定，判决如下：
            ……〔写明判决结果。分三种情况：
            第一、定罪判刑的，表述为：
            “一、被告人×××犯××罪，判处……（写明主刑、附加刑）；
            二、被告人×××……（写明追缴、退赔或没收财物的决定，以及这些财物的种类和数额。没有的不写此项）。”
            第二、定罪免刑的表述为：
            “被告人×××犯××罪，免予刑事处分（如有追缴、退赔或没收财物的，续写为第二项）。”
            第三、宣告无罪的，表述为：
            “被告人×××无罪。”〕
            如不服本判决，可在接到判决书的第二日起××日内，通过本院或者直接向××××人民法院提出上诉。书面上诉的，应交上诉状正本一份，副本×份。
            审判长×××
            ××××年××月××日
            书记员 ×××
            
            【注意事项】
            1.要给出具体的罪名，随后给出刑期（如果有），缓刑（如果有），罚金（如果有）。刑期精确到几个月。如果需要，要包含赔偿金额。
            2.判决书要包含经庭审查明的案件事实，证明这些案件事实的证据，对于事实认定和法律适用的理由。以及最后的判决。
            3.格式中，部分xx处，如果根据已有信息能确定内容，就补全，否则保留xx的格式。
            4.回复时直接以判决书的格式给出你的判罚，不要说多余的话。
            """
        self.add_to_history("审判长", self.get_response(self.judge, book_prompt,simple=6), interrupt_flag = 0, now_stage="Defendant_statement")
        self.add_to_history("书记员", "请坐下。", interrupt_flag = 3, now_stage="Defendant_statement")
        
        
        #--------------------------------审判长最后叮嘱/法庭教育
        response=self.get_response(self.judge, 
                                   """你是审判长，在案件结束、休庭之前，你可以再对被告人做最后的叮嘱和教育，体现人文关怀。
                                   例如叮嘱被告人在狱中好好表现争取减刑，如果被告人有缓刑，则可以叮嘱被告人日后要好好表现，不要犯错，否则会进监狱服刑。
                                   特别地，如果被告人有家庭困难，有身体残疾，有精神疾病等，应当对被告人给予安慰，或耐心嘱咐。
                                   
                                   你也可以严肃警告被告人，督促其日后改过自新等。
                                   
                                   如果被告人穷凶极恶，或者案件本身极为严肃，则无需进行叮嘱、教育等。
                                   
                                   注意，【你发言后被告人还要说话】，所以不要衔接“现在闭庭”等表述。
                                   
                                   请结合当前庭审记录、最后判决书中的判决结果，决定是否要发言。如果选择发言，回复‘是，’后提出1个要发言的内容；如果不发言，回复一个字‘否’。
                                   """,simple=3) 
        if response[0]=='是':
            if response[2:] in self.all_pure_content:
                response='否'
        if response[0]=='是':
            self.add_to_history("审判长", response[2:], interrupt_flag = 0, now_stage="Defendant_statement")
            self.add_to_history("被告人", self.get_response(self.defendant, "你是被告人，现在你需要回复审判长。"), interrupt_flag = 2, now_stage="Defendant_statement")
            
        # * 审判长宣布休庭
        self.add_to_history("审判长", "本次庭审结束，现在闭庭。请法警将被告人带出法庭。", interrupt_flag = 0, now_stage="Defendant_statement")
        self.add_to_history("书记员", "全体起立！请审判长退庭。", interrupt_flag = 3, now_stage="Defendant_statement")
        self.add_to_history("书记员", "请公诉人、辩护人退庭。", interrupt_flag = 3, now_stage="Defendant_statement")
        self.add_to_history("书记员", "请旁听人员退庭。", interrupt_flag = 3, now_stage="Defendant_statement")
    
    def update_evidence(self,content,speaker):
        context=Context("")
        if speaker==0:
            context.add_prosecution_evidence(content)
        else:
            context.add_advocate_evidence(content)
        self.judge.update_evidence(context)
        self.advocate.update_evidence(context)
        self.prosecution.update_evidence(context)
        self.defendant.update_evidence(context)
        
    def reflect_and_summary(self,save_only=False):
        return
        """
        反思和总结
        """
        if save_only==False:
            tmp=prepare_history_context(self.global_history)
            context=Context(tmp)
            if self.current_stage <3: #法庭辩论之后公诉人辩护人不需要再反思了，用不到了
                summary=True
                if self.current_stage ==2: #举证质证阶段之后不用总结了，用不到了
                    summary=False
                self.prosecution.reflect_and_update(context,summary=summary)
                self.advocate.reflect_and_update(context,summary=summary)
            # self.defendant.reflect_and_update(context)
            if self.current_stage <4: #被告人陈述之后不用反思了
                self.judge.reflect_and_update(context)
        
        if simplify:
            self.prosecution.memory=self.judge.memory
            self.advocate.memory=self.judge.memory
        
        if save_only==True:
            self.thoughts.append(
                {"庭审之前":{
                    "审判长":self.judge.call_thought(save_only=True),
                    "公诉人":self.prosecution.call_thought(save_only=True),
                    "辩护人":self.advocate.call_thought(save_only=True),
                    "被告人":self.defendant.call_thought(save_only=True),
                }}
            )
        elif self.current_stage <3: # 庭前，法庭调查，举证质证之后都可以记录。法庭辩论之后就不用记录这么多了。
            self.thoughts.append(
                {f"{self.stages[self.current_stage]}之后":{
                    "审判长":self.judge.call_thought(),
                    "公诉人":self.prosecution.call_thought(),
                    "辩护人":self.advocate.call_thought(),
                    "被告人":self.defendant.call_thought(),
                }}
            )
        else: #法庭辩论之后，以及被告人陈述之后
            self.thoughts.append(
                {f"{self.stages[self.current_stage]}之后":{
                    "审判长":self.judge.call_thought(),
                # "被告人":self.defendant.call_thought(),
                }}
            )

    def save_progress(self, index):
        """
        记录运行状态
        :param index: 当前案例索引
        """
        progress = {"current_case_index": index}
        with open("progress.json", "w") as f:
            json.dump(progress, f)

    def load_progress(self):
        """
        加载运行状态
        :return: 运行状态字典或None
        """
        if os.path.exists("progress.json"):
            with open("progress.json", "r") as f:
                return json.load(f)
        return None

    def run_simulation(self, defendant_info=None, prosecution_statement=None, evidence_prosecution=None, evidence_defendant=None,simulation_id=None,source: Optional[Literal["LJP", "video"]] = None):
        """
        运行整个法庭模拟过程
        """
        # initialize court
        if simulation_id is not None:
            self.case_data=self.load_json(os.path.join(self.case_data_path,f"data_{source}/{simulation_id}", "data_anonymized.json"))
        else:
            self.case_data = {
                'defendant_information': defendant_info,
                'prosecution_statement': prosecution_statement,
                'evidence': [evidence_prosecution, evidence_defendant]
            }
        
        prosecution_statement = self.case_data["prosecution_statement"]
        evidence=self.case_data["evidence"]
        self.global_history = []
        self.full_history=[]
        self.thoughts=[]
        console.print("除审判长外的其他人员入场", style="bold")

        # self.defendant.think_answer(self.advocate.questions)
        self.all_pure_content=[]
        
        self.role_colors = {
            "书记员": "cyan",
            "审判长": "yellow",
            "公诉人": "green",
            "被告人": "red",
            "辩护人": "blue"
        }
        self.role_name = {
            "书记员": self.config["stenographer"]["name"],
            "审判长": self.config["judge"]["name"],
            "公诉人": self.config["prosecution"]["name"],
            "被告人": self.config["defendant"]["name"],
            "辩护人": self.config["advocate"]["name"]
        }
        # initialize agent
        self.judge = self.create_agent(self.config["all_description"], self.config["judge"], self.judge_model, log_think=self.log_think)
        self.prosecution =self.create_agent(self.config["all_description"], self.config["prosecution"], self.prosecutor_model, log_think=self.log_think)
        # self.stenographer=self.create_agent(self.config["all_description"] , self.config["stenographer"], self.clerk_model, log_think=self.log_think)
        self.advocate=self.create_agent(self.config['all_description'], self.config['advocate'], self.advocate_model, log_think=self.log_think)
        self.defendant=self.create_agent(self.config["all_description"], self.config["defendant"], self.defendant_model, log_think=self.log_think)
        
        request=self.case_data['request'] if 'request' in self.case_data else ""
        if request!="":
            request="被告人诉求："+request
        # fact=self.case_data["fact"]
        # if fact!="":
        #     fact="被告人认为的事实："+fact
        strategy_prompt,goal,strategy=self.advocate.for_defendant(self.case_data["prosecution_statement"],self.case_data["defendant_information"]+request,"公诉人出示的："+str(self.case_data["evidence"][0])+"辩护人出示的："+str(self.case_data["evidence"][1]))
        # self.defendant.set_strategy(strategy_prompt,goal,strategy)
        self.defendant.set_strategy(strategy_prompt,goal,strategy,self.case_data["prosecution_statement"],self.case_data["defendant_information"]+request,"公诉人出示的："+str(self.case_data["evidence"][0])+"辩护人出示的："+str(self.case_data["evidence"][1]))
       
        self.reflect_and_summary(save_only=True)
        #preparation stage
        self.preparation_stage()
        # self.reflect_and_summary()
        self.full_history+=self.global_history
        self.global_history = []
        #investigation stage
        self.investigation_stage()
        self.reflect_and_summary()
        self.full_history+=self.global_history
        self.global_history = []
        #Presentation_of_evidence stage
        self.Presentation_of_evidence()
        self.reflect_and_summary()
        self.full_history+=self.global_history
        self.global_history = []
        # #Court_debate stage
        self.debate_stage()
        self.reflect_and_summary()
        self.full_history+=self.global_history
        self.global_history = []
        #Defendant_statement stage
        self.statement_stage()
        self.full_history+=self.global_history
        self.reflect_and_summary()
        
        #end and save
        console.print(f"案例庭审结束", style="bold")
        timestamp = datetime.datetime.now().strftime("%m%d_%H%M")
        
        save_dir = f"test_result/{date}/test_result_json/judge_{self.judge_model}_clerk_{self.clerk_model}_prosecutor_{self.prosecutor_model}_defendant_{self.defendant_model}_advocate_{self.advocate_model}"
        
        os.makedirs(save_dir, exist_ok=True)
        
        # save json log
        self.save_court_log(
            f"{save_dir}/case_{simulation_id}_{timestamp}.json"
        )
        
        # save txt file
        self.save_history(simulation_id)

    def save_court_log(self, file_path):
        """
        保存法庭日志
        :param file_path: 保存文件路径
        """
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.full_history+self.thoughts, f, ensure_ascii=False, indent=2)
        logging.info(f"Court session log saved to {file_path}")
        

def parse_arguments(): 
    """
    解析命令行参数
    :return: 解析后的参数
    """
    parser = argparse.ArgumentParser(description="Run a simulated court session.")
    parser.add_argument(
        "--init_config",
        default="settings/example_role_config.json",
        help="Path to the role configuration file",
    )
    parser.add_argument(
        "--stage_prompt",
        default="settings/stage_prompt.json",
        help="Path to the stage prompt file",
    )
    parser.add_argument(
        "--case",
        default="data",
        help="Path to the case data file in JSON format",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the logging level",
    )
    parser.add_argument(
        "--log_think", action="store_true", help="Log the agent think step"
    )
    return parser.parse_args()

def main():
    """
    主函数
    """
    args = parse_arguments()
    simulation = CourtSimulation(args.init_config, args.stage_prompt, args.case,  args.log_level, args.log_think,launch=True)

if __name__ == "__main__":
    main()
