from typing import List, Dict, Any, Tuple
import re
import json
from LLM.deli_client import search_law
import uuid
import logging
import requests
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from frontEnd import simplify
import sys
import os

# sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

law_repository={}
with open(os.path.abspath(os.path.join(os.path.dirname(__file__),"resource/law.json")), 'r', encoding='utf-8') as f:
    law_repository=json.load(f)
    

def extract_bracket_content(text):
    # 正则表达式匹配【】及其内部内容
    pattern = r'【(.*?)】'
    # 使用findall方法找到所有匹配的内容
    contents = re.findall(pattern, text)
    return contents

class Context:
    def __init__(self,content):
        self.content=content
        self.evidence={
            "公诉方":"",
            "辩护方":""
        }
    def add_prosecution_evidence(self,item:str):
        self.evidence["公诉方"]+=item
    def add_advocate_evidence(self,item:str):
        self.evidence["辩护方"]+=item
    
class Agent:
    def __init__(
        self,
        id: int,
        name: str,
        role: str,
        description: str,
        llm: Any,
        # db: Any,
        # log_think=False,
    ):
        self.id = id
        self.name = name
        self.role = role
        self.basic_description = description
        self.instruction=description
        self.llm = llm
        self.goal=""
        CHROMA_PATH = "./resource/chroma"
        # embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-mpnet-base-v2")

        # self.db= Chroma(persist_directory=CHROMA_PATH, embedding_function=embeddings)
        
        self.evidence_pool={
            "公诉方出示的":"",
            "辩护方出示的":""
        }
        self.memory=""
        # {
        #     "审判长":"",
        #     "公诉人":"",
        #     "辩护人":"",
        #     "被告人":""
        # }
        self.search_pool=None
        self.crime3aspect="""
            判断被告人是否犯罪要考虑如下三个角度：
            **只有当三个角度都成立，且具有直接因果关系时，罪名才真正成立**
            
            一、构成要件符合性:
            行为主体：1、三阶层理论不要求区分其年龄、责任能力；2、身份犯的概念。真正身份犯：身份是犯罪构成条件，例如贪污罪。不真正身份犯，身份是影响量刑的条件，例如非法拘禁罪。3、单位：主观：整体意志；客观：是为·整体谋利益，例如私分国有财产
            行为：（1）作为（2）不作为：义务来源:1.对危险源有监管义务，如负责管理的危险物，监管义务的人的举动。自己的先行行为。2.对法益有保护义务的特定关系。法律规定的特定关系，合同关系，职务业务建立，自愿接受行为。（德国排除被害人自陷风险）3、特定领域，管理人和产生依赖关系。
            结果：故意犯罪：产生危险是成立条件，产生结果是既遂条件。过失犯罪实害结果是犯罪成立条件
            因果关系：1.制造了法律不允许的危险；2.刑法要防止发生的结果；3.危险的实现：如果存在介入因素，应该分析介入因素与先行行为关系，叠加关系还是独立关系？

            二、违法性
            正当防卫：（1)正当防卫的条件：1.起因条件:必须是不法的，”现实的“，紧迫的不法侵害。2、针对不法侵害者实施。认识到不法侵害正在发生，并有意识地对不发侵害进行反击。3不能明显超过必要限度。（2）特殊防卫：行为限制是正在进行的行凶、抢劫、强奸、绑架以及其他严重危机人身安全的暴力犯罪，造成不法侵害人伤亡的，不属于防卫过当。
            紧急避险：（1)条件：1.起因条件:客观具体的法益危险，也可以是国家、公共利益；具有现在性：紧迫即刻发生的危险，以及在一定时间内，随时具有发生可能的持续性危险。行为条件：牺牲其他法益的行为是避免危险所需要以及补充性要件。避险意识：客观违法论：不考虑避险意识，偶然避险属于紧急避险。主观违法论：要求对危险及通过避险能够避免法益损失的事实存在认识。
            其他：（1）自救行为（2）正当业务行为（3）义务冲突（4）被害人承诺

            三、有责性
            主观要件: (1) 犯罪故意：明知自己的行为会发生危害社会的结果，并且希望或者放任这种结果发生。 (2) 犯罪过失：应当预见自己的行为可能发生危害社会的结果，因而疏忽大意而没有预见，或者已经预见而轻言能够避免，以致发生这种结果。
            责任阻却事由:(1)责任年龄：【年龄对责任能力的影响】已满十六周岁的人犯罪，应当负刑事责任。
            已满十四周岁不满十六周岁的人，犯故意杀人、故意伤害致人重伤或者死亡、强奸、抢劫、贩卖毒品、放火、爆炸、投放危险物质罪的，应当负刑事责任。已满十四不满十八周岁的人犯罪，应当从轻或者减轻处罚。因不满十六周岁不予刑事处罚的，责令他的家长或者监护人加以管教:在必要的时候，也可以由政府收容教养。
            >第十七条之一【年龄对老年人责任能力的影响】已满七十五周岁的人故意犯罪的，可以从轻或者减轻处罚:过失犯罪的，应当从轻或者减轻处罚。(2)责任能力：第十八条 【精神障碍对责任能力的影响】精神病人在不能辨认或者不能控制自己行为的时候造成危害结果，经法定程序鉴定确认的，不负刑事责任，但是应当责令他的家属或者监护人严加看管和医疗;在必要的时候，由政府强制医疗。间歇性的精神病人在精神正常的时候犯罪，应当负刑事责任。尚未完全丧失辨认或者控制自己行为能力的精神病人犯罪的，应当负刑事责任，但是可以从轻或者减轻处罚。醉酒的人犯罪，应当负刑事责任。第十九条 【听说、视觉机能对责任能力的影响】又聋又哑的人或者盲人犯罪，可以从轻、减轻或者免除处罚。(3)违法性认识错误：行为人具有认识违法的能力，行为人具有考察法律属性的机会；可以期待行为人利用其提供认识违法性的可能性。(4)期待可能性：根据社会通常人的情况，在当时的环境下，能否做出与行为人同样行为作为判断标准，是相对较为合理。
        """
        self.current_plan=None
        self.current_answer=None
        # self.db = db
        # self.log_think = log_think
        # self.instruction=None
        # self.logger = logging.getLogger(__name__)

    def set_instruction(self,text):
        self.instruction=self.basic_description+text
    
    def __str__(self):
        return f"{self.name} ({self.role})"
    
    def update_evidence(self,context:Context):
        return
        self.evidence_pool["公诉方出示的"]+=context.evidence["公诉方"]
        self.evidence_pool["辩护方出示的"]+=context.evidence["辩护方"]
    
    def check_hallucination(self,context:Context):
        self.strategy=self.speak("最新的庭审记录:"+context.content+"法庭人员发言记录总结："+str(self.memory)+"目前的证据："+str(self.evidence_pool)+"目前的策略："+str(self.strategy),
                        """
                        法庭上要实事求是！不能无中生有！没有提及的内容不能作为证据，不能作为策略!
                        请根据最新庭审记录、发言记录总结、证据，检查【目前的策略】中，是否出现了无中生有、捏造事实的言论。
                        例如，如果没有信息表明被告人赔偿损失、征得谅解，则不应该有相应的策略！
                        如果有，把相关内容直接删掉。
                        如果某条策略的相关不实内容删掉后，该条目没有实质性内容，则把该条目一同删掉。
                        如果没有发现无中生有、捏造事实的言论，则无需修改。
                        不要保留修改痕迹！不用额外说明/注释！
                        
                        请回复经过修改之后的策略。（依然分条目）
                        保持原始的格式不变，即：
                        攻击策略：1.xxx2.xxx3.xxx
                        防御策略：1.xxx2.xxx3.xxx
                        """
                        )
    
    def check_speak_hallucination(self,context,response):
        res=self.speak("最新的庭审记录:"+context+"法庭人员发言记录总结："+str(self.memory)+"目前的证据："+str(self.evidence_pool)+"拟进行的发言内容："+response,
                        """
                        法庭上要实事求是！不能无中生有！没有论证的内容，不能当作发言内容！
                        请根据最新庭审记录、发言记录总结、证据，检查【拟进行的发言内容】中，是否出现了无中生有、捏造事实的言论（即幻觉）。
                        例如，如果没有信息表明被告人赔偿损失、征得谅解，但【拟进行的发言内容】中却出现了相应的文字，则表明出现了幻觉
                        或者数额和证据及前文讨论内容对应不上，则表明出现了幻觉
                        如果有幻觉，返回一个字‘有’，如果没有，返回一个字‘无’（不要带引号）
                        
                        不要说多余的话！
                        """,check=False
                        )
        return res
        
    # --- Plan Phase --- #
    def reflect_and_update(self,context:Context,summary=True):
        if self.role=="审判长":
            # res=self.speak("最新的庭审记录:"+context.content+"法庭人员发言记录总结："+str(self.memory)+"目前的证据："+str(self.evidence_pool)+"目前的辩论焦点："+str(self.debate_focus),
            #             """
            #             你要根据输入的信息，进一步调整/更新辩论焦点。
            #             """+self.strategy_prompt+
            #             """
            #             辩论焦点从1开始编号
            #             请严格按照以下格式回复：
            #             1.法庭辩论焦点2.法庭辩论焦点3.法庭辩论焦点
            #             """
            #             )
            info="起诉书："+self.prosecution_statement+"被告人信息："+self.defendant_information+"法庭人员发言记录总结："+str(self.memory)+"最新的庭审记录:"+context.content+"目前的证据："+str(self.evidence_pool)+"目前的辩论焦点与查明情况："+str(self.debate_focus)
            task="""
            作为审判长，你要查明案件的事实。你的任务如下：
            （1）你要根据输入的信息，以及当前的辩论焦点和查明情况，进一步调整/更新辩论焦点。
            """+self.strategy_prompt+"""
            （2）除了调整/更新辩论焦点外，你还要根据输入的信息、更新后的辩论焦点、先前的查明情况，总结现在的每一个焦点的**查明情况。**
            """
            QA_pair=self.plan(info+task)
            self.init_QA_pair.update(QA_pair)
            res=self.speak(info+"参考资料："+str(self.init_QA_pair),
                        """
                        作为审判长，你要查明案件的事实。你的任务如下：
                        （1）你要根据输入的信息，以及当前的辩论焦点和查明情况，进一步调整/更新辩论焦点。
                        """+self.strategy_prompt+
                        """
                        （2）除了调整/更新辩论焦点外，你还要根据输入的信息、更新后的辩论焦点、先前的查明情况，总结现在的每一个焦点的**查明情况。**
                        **查明情况**是控辩双方对这个焦点的讨论情况的概述、讨论得是否充分、以及作为审判长你的看法。
                        **简要说明即可。**
                        
                        最终请严格按照如下格式进行回复：
                        辩论焦点从1开始编号，查明情况紧随其后。
                        请严格按照以下格式回复：
                        1.法庭辩论焦点。查明情况。
                        2.法庭辩论焦点。查明情况。
                        3.法庭辩论焦点。查明情况。
                        
                        例如：
                        1.被告人自首是否成立...公诉人认为不构成自首，通过xxx进行证明；辩护人认为构成自首，表示xxx。审判长认为被告人的自首成立，因为xxx
                        2.关于证据xx里提到的xxx是否和本案有关联，控辩双方各自认为xxx，审判长认为还需要进一步辩论。
                        """
                        )
            self.debate_focus=res
        else:
            info="起诉书："+self.prosecution_statement+"被告人信息："+self.defendant_information+"之前法庭人员发言记录总结："+str(self.memory)+"最新的庭审记录:"+context.content+"目前的证据："+str(self.evidence_pool)+"拟定的目标："+self.goal+"目前的策略："+str(self.strategy)
            task="""
            你要根据输入的信息，进一步调整/更新策略。
            """+self.strategy_prompt
            QA_pair=self.plan(info+task)
            self.init_QA_pair.update(QA_pair)
            res=self.speak(info+"参考资料："+str(self.init_QA_pair),
                        """
                        你要根据输入的信息，进一步调整/更新策略。
                        """+self.strategy_prompt+
                        """
                        你的回复应当严格按照如下格式（分条表述）：
                        攻击策略：1.xxx2.xxx3.xxx
                        防御策略：1.xxx2.xxx3.xxx
                        
                        其中每一条的格式为：
                        xxx（策略内容），参考法条：xxx（法条名称及内容概括），参考案例：xxx（案例编号及内容概括）
                        
                        法条和案例如果没有，或对于约定俗成的常见策略，则不必添加这些参考。
                        
                        【注意】
                        1.注意，策略要实事求是符合实际！不能无中生有！
                        2.直接按照格式返回，不要说多余的话
                        3.每一个策略下，**要附带能支撑该策略的参考法条以及类案信息**，（从给你的参考资料中取，如果没有则不用带）
                        4.你要进一步调整策略，要和之前的策略进行合理地修改，而非照搬或者全盘否定。
                        """
                        )
            self.strategy=res
            self.check_hallucination(context)
            
        if self.role=="审判长" or simplify==False:
            # tmp=""
            # if self.memory!="":
            #     tmp+="之前的庭审总结"+str(self.memory)
            tmp="最新的庭审记录:"+context.content
            
            res=self.speak(tmp,
                """
                你要根据最新的庭审记录，写出这一部分的庭审总结。
                （1）庭审总结应当包括：按先后顺序发生的、【且可能影响最终定罪量刑的事情】的概括与总结。
                程序性、重复性、与案件无关、法官控场打断等【没有实质性内容的话语】应当省略！
                
                例如：
                庭审准备阶段，审判长询问被告人xxx，被告人表示xx
                法庭调查阶段，公诉人依次询问xxx，被告人回复xxx，辩护人询问xxx，被告人回复xxx
                
                **注意:**
                1.你只要返回这一阶段的总结即可。
                2.可能涉及最后罪情的重要的数字、重要信息应当保留！例如赔偿金额，轻伤/重伤判定等。
                3.双方有争议的也要总结并保留，不能丢弃。
                """           
                )
            self.memory+="\n\n"+res
    
    def yilvkezhi_retriever(self,prompt):
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
        # print(response)
        answer=response["data"]["answer"]
        sim_cases=extract_bracket_content(answer)
        anhao={}
        for js in response["data"]["wenshu_results"]:
            anhao[js['anhao']]=js
        sim_cases_text="类似案件为："
        fl=0
        for case in sim_cases:
            if case=="" or case is None:
                continue
            if case in anhao:
                if anhao[case]['caipanliyou']!="" and anhao[case]['caipanjieguo']!="":
                    if anhao[case]['caipanliyou'] is not None and anhao[case]['caipanjieguo'] is not None:
                        fl+=1
                        sim_cases_text+="\n"+"【"+case+"】："+anhao[case]['caipanliyou']+anhao[case]['caipanjieguo']
                if fl==1: #only 1 cases
                    break
        if fl!=0:
            answer+="\n\n#####\n"+sim_cases_text
        return answer

    def law_retriever(self,query_text):
        if query_text in law_repository:
            return law_repository[query_text]
        return None

    def _get_plan(self,context,hint=""):
        prompt = """
        现在，为了更好地完成任务，有两个工具供你使用。
        1.法条检索库。包含中华人民共和国全部法条，包含刑法、民法典、民事诉讼法等。根据查询内容，可以返回法条内容。同时也包含部分法律法规和司法解释。
        2.‘一律可知’。可以通过输入法律问题，法律事实，争议焦点，案例信息来获取相关案例以及专业的分析答案。
        请根据你的任务目标和当前信息，决定是否要使用这两个工具。以及要询问什么内容。
        一次可以查询多个问题，多个问题放到list里面。
        
       【注意！！】
        1.法条检索库输入的法律名称必须是全称，不能缩写。比如必须写明为“中华人民共和国刑法第一条”，“中华人民共和国刑法第一百二十条之二”，“最高人民法院关于审理未成年人刑事案件具体应用法律若干问题的解释第十五条” 等
        2.不要写款、项！仅写明法条的全名。例如，不要写“中华人民共和国刑法第一百三十四条第一款”，只写“中华人民共和国刑法第一百三十四条”
        
        你的回复要严格按照如下格式（不要说任何多余的话！无需进行其他回复！！）：
        
        {
            "法条":{
                "使用":0代表不适用，1代表使用。
                "询问":[你要询问的问题1,你要询问的问题2]
            },
            "一律可知":{
                "使用":0代表不适用，1代表使用。
                "询问":[你要询问的问题1,你要询问的问题2]
            }
        }
        
        例如:
        {
            "法条":{
                "使用":1,
                "询问":["中华人民共和国民法典第四百六十九条","中华人民共和国刑法第五条","最高人民法院关于审理未成年人刑事案件具体应用法律若干问题的解释第十五条"]
            },
            "一律可知":{
                "使用":1
                "询问":["客户信息是否属于公司的商业秘密？","单位可以利用末位淘汰制度与员工解除劳动合同吗？"]
            }
        }
        
        """+hint
        response = self.speak(
            context,
            prompt,
            check=False
        )
        print("Queries",self.role,response)
        return response
            
    def plan(self, context,hint=""):
        now_plan=self._get_plan(context,hint=hint)
        now_plan=json.loads(now_plan)
        
        laws=""
        QA_pair={}
        if now_plan["一律可知"]["使用"]==1:
            for query in now_plan["一律可知"]["询问"]:
                answer=self.yilvkezhi_retriever(query)
                if answer is not None:
                    QA_pair.update({query:answer})
                    now_plan["一律可知"].update({query:answer})
                    
                    pattern = r"### 核心法条\n(.*?)\n\n###"
                    core_statutes = re.search(pattern, answer, re.S)

                    core_statutes_content = core_statutes.group(1) if core_statutes else ""
                    laws+=core_statutes_content
        
        if now_plan["法条"]["使用"]==1:
            prompt = """
                提取所给出的文本中的所有法条、法规、司法解释名称及具体条目。
                法条包含刑法、民法典、民事诉讼法等。同时也包含部分法律法规和司法解释。
                
                【注意！！】
                1.每一项法律法规司法解释必须是全称，不能缩写。比如必须写明为“中华人民共和国刑法第一条”，“中华人民共和国刑法第一百二十条之二”，“最高人民法院关于审理未成年人刑事案件具体应用法律若干问题的解释第十五条” 等
                2.不要写款、项！仅写明法条的全名（即精确到第xx条）。例如，不要写“中华人民共和国刑法第一百三十四条第一款”，只写“中华人民共和国刑法第一百三十四条”
                3.直接返回提取的结果，相邻两个条目之间用|分隔。
                4.法条法规不要带书名号！直接衔接第x条。
                
                【返回格式】
                法条法规1|法条法规2|法条法规3|法条法规4
                
                例如：
                中华人民共和国刑法第一条|中华人民共和国刑法第一百二十条之二|最高人民法院关于审理未成年人刑事案件具体应用法律若干问题的解释第十五条
                
                """
            response = self.speak(
                laws+str(now_plan["法条"]["询问"]),
                prompt,
                check=False
            )
            response=response.split("|")
            for query in response:
                answer=self.law_retriever(query)
                if answer is not None:
                    QA_pair.update({query:answer})
                    now_plan["法条"].update({query:answer})
        
        self.current_plan=now_plan
        self.current_answer=QA_pair
        print("Generate QA_pair",self.role,QA_pair)
        return QA_pair

    # --- Do Phase --- #

    def execute(
        self, plan: Dict[str, Any], history_list: List[Dict[str, str]], prompt: str, simple:int
    ) -> str:
        
        history_context = self.prepare_history_context(history_list)
        self.history_context=history_context
        if simple==1: #审判长宣读辩论焦点
            return self.speak("当前庭审记录："+history_context, prompt,check=True)
        elif simple==2: # 最后判决
            context="目前的辩论焦点和查明情况："+str(self.debate_focus)+"法庭发言记录总结："+str(self.memory)
            # QA_pair=self.plan(context+prompt.split("#####")[0],hint="提示，可以搜索类似案件判决情况，关注刑期长短，关注社会评价与社会影响，关注是否适用缓刑，是否需要赔偿、处罚罚金，以及具体数值等。**建议至少查询类似案件、实刑刑期长度、缓刑适用、罚金数额！**")
            # self.init_QA_pair.update(QA_pair)
            # print("参考资料："+str(self.init_QA_pair), context+prompt)
            return self.speak("", context+prompt,check=True)
        elif simple==6: # 判决书生成
            context="庭审记录总结："+str(self.memory)+"目前的辩论焦点和查明情况："+str(self.debate_focus)
            return self.speak(context, prompt,check=True)
        elif simple==5: # 被告人回答是否之前有过其他法律处分/法官宣读庭审启动
            return self.speak("", prompt)
        
        
        if self.role=="审判长":
            context="之前法庭人员发言记录总结："+str(self.memory)+"目前的证据："+str(self.evidence_pool)+"目前的辩论焦点和查明情况："+str(self.debate_focus)+"最新的庭审记录:"+history_context
        elif self.role=="被告人":
            context="目前的策略："+str(self.strategy)+"最新的庭审记录:"+history_context
            prompt+="被告人请按实际情况诚实回答，无中生有可能会加重判罚。例如，如果没有赔偿，或没有取得谅解，就要如实回答没有。"
        else:
            # context="之前法庭人员发言记录总结："+str(self.memory)+"目前的证据："+str(self.evidence_pool)+"目前的策略："+str(self.strategy)+"最新的庭审记录:"+history_context
            context="之前法庭人员发言记录总结："+str(self.memory)+"目前的证据："+str(self.evidence_pool)
            context+="目前的策略："+str(self.strategy)+"最新的庭审记录:"+history_context
            
        if simple==3: #公诉人/辩护人 法庭调查的提问
            context+="拟询问的问题（仅供参考），注意不要和之前问题重复："+str(self.questions)
        
        if simple==4: #审判长打断选项
            return self.speak(context, prompt)
    
        if simple==7: #审判长判断有没有认罪认罚具结书
            return self.speak(context, prompt)
        
        # QA_pair=self.plan(context)
        # return self.speak(context+"参考资料："+str(QA_pair), prompt)
        return self.speak(context, prompt,check=True)
    
    def pure_final_judge(self,context,prompt):
        QA_pair=self.plan(context+prompt,hint="提示，可以搜索类似案件判决情况，关注刑期长短，关注社会评价与社会影响，关注是否适用缓刑，是否需要赔偿、处罚罚金，以及具体数值等。**建议至少查询类似案件、实刑刑期长度、缓刑适用、罚金数额！**")
        return self.speak("案件事实"+context+"参考资料："+str(QA_pair), prompt)
        # return self.speak(context, prompt)
    
    def speak(self, context: str, prompt: str, max_tokens=4096,check=False) -> str:
        instruction = f"{self.instruction}\n\n"
        full_prompt = f"{context}\n\n{prompt}"
        
        hint=""
        
        # if check==False:
        return self.llm.generate(instruction=instruction, prompt=full_prompt+hint,max_tokens=max_tokens)
        
        # for i in range(2):
        #     response=self.llm.generate(instruction=instruction, prompt=full_prompt+hint,max_tokens=max_tokens)
        #     check_res=self.check_speak_hallucination(self.history_context,response)
        #     if check_res[0]=='无':
        #         return response
        #     hint="请仔细查看证据信息，务必遵循证据事实，确保不要无中生有！你已经出现了一次幻觉！"
        # print("HALLUCINATION!")
        # return "【HALLUCINATION!】"+response
    # --- Reflect Phase --- #

    def prepare_history_context(self, history_list: List[Dict[str, str]]) -> str:
        formatted_history = ["当前庭审记录："]
        for entry in history_list:
            role = entry["role"]
            content = entry["content"].replace("\n", "\n  ")
            formatted_entry = f"\\role{{{role}}}\n  {content}"
            formatted_history.append(formatted_entry)
        return "\n\n".join(formatted_history)

    

class Agent_litigants(Agent):
    def __init__(
        self,
        id: int,
        name: str,
        role: str,
        description: str,
        llm: Any,
        fact=None
    ):
        super().__init__(id,name,role,description,llm)
        self.strategy=""
        # {
        #     "攻击策略":"",
        #     "防御策略":""
        # }
        self.questions=""
        self.fact=fact
    
    def call_thought(self,save_only=False):
        res={}
        res.update({
            "策略":self.strategy,
            "记忆":self.memory,
            })
        if self.role!="被告人":
            res.update({
                "规划":self.current_plan,
            })
        if save_only==True:
            res.update({
                "目标":self.goal
            })
            if self.role!="被告人":
                res.update({
                    "询问":self.questions
                })
        return res
        
    def preparation(self,prosecution_statement,defendant_information,evidence):
        # term_mention=f"""
        #     被告人被指控的罪名有：{all_term}
        #     你的策略应当针对该罪名的定罪、量刑进行制定。一定要有针对性。
        # """
        
        
        self.defendant_information=defendant_information
        self.prosecution_statement=prosecution_statement
        self.evidence_pool=evidence
        
        all_input=self.crime3aspect
        
        if self.role=="公诉人":
            self.strategy_prompt="""
            【攻击策略】公诉人需要制定自己的攻击策略，包含被告人犯罪的证据链（通过对证据、法律条文的精准解读说明为什么被告人犯罪），质疑辩护人的证据的关联性与证明效力（例如辩护人出示自首证据，可以质疑是否真的自首），以及论述为什么足以判处起诉状中的刑期（比如社会危害度，可改造程度等）等。
            【防御策略】公诉人需要制定自己的防御策略，包含如何维护自身证据的关联性和证明效力，以应对辩护人和被告人潜在的对证据的质疑。
                
            你的策略应当参考被告人信息、被告人的诉求！
            此外要注意，**公诉人的目的是协助法官查明真相，对被告人进行公正的判罚**，所以对于**你认可的被告人能够从轻处罚的情节**，也可以加入到策略之中，而非机械地反对被告人/辩护人的一切观点与诉求。
            
            你的策略可以晓之以理动之以情，可以换位思考，站在被告人的角度，事实经过的角度去制定策略。
            """
            
            info="起诉状："+prosecution_statement+"被告人信息："+defendant_information+"证据："+evidence
            task="""
                在庭审开始前，你要根据起诉状、被告人信息、证据条目，制定自己本次出庭的目标、攻击策略、防御策略。
                """+all_input+"""
                **再次注意，只有当三个角度都成立，且具有直接因果关系时，罪名才真正成立**
                **所以你的策略应当围绕论证犯罪的定义成立，且因果成立的角度。**
                越具体越好！
                """+"""
                【目标】公诉人的目标通常为保证准确、及时地查明犯罪事实，正确应用法律，惩罚犯罪分子，保障无罪的人不受刑事追究。具体地，你的目标还应当包含期望法庭给被告人处以的罪名、刑期和罚金。
                """+self.strategy_prompt
            # QA_pair=self.plan(info+task)
            # res=self.speak(info+"参考资料："+str(QA_pair),
            #     task+
            #     """
            #     你的回复应当严格按照如下格式：
            #     [一句话总结目标]|[攻击策略，直接分条回复。1.xxx2.xxx3.xxx]|[防御策略，分条回复。1.xxx2.xxx3.xxx]
            #     回复时不要包含[]
            #     例如：
            #     请求法院判处被告人xxx|1.证据xxx证明2.被告人的自首系xxx3.社会危害性xxx|1.证据xxx是由xxx，具有法律效力2.xxx
                
                
            #     其中每一条的格式为：
            #     xxx（策略内容），参考法条：xxx（法条名称及内容概括），参考案例：xxx（案例编号及内容概括）
                
            #     法条和案例如果没有，或对于约定俗成的常见策略，则不必添加这些参考。
                
            #     【注意】
            #     1.注意，策略要实事求是符合实际！不能无中生有！
            #     2.直接按照格式返回，不要说多余的话
            #     3.每一个策略下，**要附带能支撑该策略的参考法条以及类案信息**，（从给你的参考资料中取，如果没有则不用带）
            #     4.你要进一步调整策略，要和之前的策略进行合理地修改，而非照搬或者全盘否定。
            #     """
            #                      )
            
        elif self.role=="辩护人":
            info="起诉状："+prosecution_statement+"被告人信息："+defendant_information+"证据："+evidence
            self.strategy_prompt="""
            【攻击策略】辩护人需要制定自己的攻击策略，质疑公诉人的证据（例如说明公诉人的证据与本案件的不具备关联性，或证明效力不够充分），指出其证据不足或推理不合理。
            【防御策略】辩护人需要制定自己的防御策略，以减轻被告人的罪责。包含寻找有利证据、构建合理故事、法律条文的精准解读、强调案件特殊情节、强调积极态度与悔悟等为被告人进行开脱，同时，也可以强调被告人的学历认知受限、家庭困难等客观因素，争取减轻判罚。此外，还要维护自身证据与案件事实的关联性，以应对公诉人潜在的对证据的质疑。
            
            你的策略整体上要围绕定罪、量刑、缓刑、罚金展开，应当参考被告人信息、被告人的诉求！
            例如被告人家庭经济条件不好，则应当尝试减少罚金，争取缓刑等；被告人提出希望缓刑，则应当争取缓刑。
            
            你的策略可以晓之以理动之以情，可以换位思考，站在被告人的角度，事实经过的角度去制定策略。
            """
            task="""
                在庭审开始前，你要根据起诉状、被告人信息、证据条目，制定自己本次出庭的目标、攻击策略、防御策略。
                """+all_input+"""
                **再次注意，只有当三个角度都成立，且具有直接因果关系时，罪名才真正成立**
                **所以你的策略应当围绕论证犯罪的定义不成立，或者因果不完全成立的角度。**
                越具体越好！
                """+"""
                【目标】辩护人的责任是根据事实和法律，提出犯罪嫌疑人、被告人无罪、罪轻或者减轻、免除其刑事责任的材料和意见，维护犯罪嫌疑人、被告人的诉讼权利和其他合法权益。具体地，你的目标应还当包含期望法庭给被告人处以的罪名、刑期和罚金。（要低于起诉状中的罪情）
                """+self.strategy_prompt
            # QA_pair=self.plan(info+task)
            # res=self.speak(info+"参考资料："+str(QA_pair),
            #     task+
            #     """
            #     你的回复应当严格按照如下格式：
            #     [一句话总结目标]|[攻击策略，直接分条回复。1.xxx2.xxx3.xxx]|[防御策略，分条回复。1.xxx2.xxx3.xxx]
            #     回复时不要包含[]
                
            #     例如：
            #     请求法院判处被告人xxx|1.证据xxx不足以xxx2.xxx处推理不合理|1.证据xxx是由xxx，具有法律效力2.被告人态度良好xxx
                
                
            #     其中每一条的格式为：
            #     xxx（策略内容），参考法条：xxx（法条名称及内容概括），参考案例：xxx（案例编号及内容概括）
                
            #     法条和案例如果没有，或对于约定俗成的常见策略，则不必添加这些参考。
                
            #     【注意】
            #     1.注意，策略要实事求是符合实际！不能无中生有！
            #     2.直接按照格式返回，不要说多余的话
            #     3.每一个策略下，**要附带能支撑该策略的参考法条以及类案信息**，（从给你的参考资料中取，如果没有则不用带）
            #     4.你要进一步调整策略，要和之前的策略进行合理地修改，而非照搬或者全盘否定。
            #     """
            #                      )
        # res=res.split("|")
        self.goal=""#res[0]
        self.strategy=""#f"攻击策略：{res[1]}"+ "\n"+ f"防御策略：{res[2]}"
        self.init_QA_pair=""# QA_pair

        if self.role=="公诉人":
            self.questions=""
            # self.speak("起诉状："+prosecution_statement+"被告人信息："+defendant_information+"证据："+evidence+"最终目标："+self.goal+"策略: "+self.strategy+"参考资料："+str(QA_pair),
            #     """
            #     在法庭调查阶段，作为公诉人，你要围绕定罪量刑相关问题对被告人进行发问。
            #     比如针对案件事实，犯罪动机，犯罪情节等。
            #     现在请你根据起诉状、被告人信息、证据条目、本次出庭的目标、攻击策略、防御策略，制定法庭调查阶段拟询问被告人的问题。
                
            #     问题应当涵盖多个角度，而总数不要太多！
            #     """+
            #     all_input+
            #     """
            #     请分条回复。**按照重要性先后顺序！**
            #     例如
            #     1.xxxx
            #     2.xxxx
            #     3.xxxx
            #     """)
            
        elif self.role=="辩护人":
            self.questions=""
            
            # self.speak("起诉状："+prosecution_statement+"被告人信息："+defendant_information+"证据："+evidence+"最终目标："+self.goal+"策略："+self.strategy+"参考资料："+str(QA_pair),
            #     """
            #     在法庭调查阶段，作为辩护人，你要围绕定罪量刑相关问题对被告人进行发问。
            #     比如针对案件事实，犯罪动机，犯罪情节等。
            #     现在请你根据起诉状、被告人信息、证据条目、本次出庭的目标、攻击策略、防御策略，制定法庭调查阶段拟询问被告人的问题。
            #     问题应当涵盖多个角度，而总数不要太多！
            #     """+
            #     all_input+
            #     """
            #     请分条回复。**按照重要性先后顺序！**
            #     例如
            #     1.xxxx
            #     2.xxxx
            #     3.xxxx
            #     """)
        
    def for_defendant(self,prosecution_statement,defendant_information,evidence):
        # 辩护人和被告人商议最终目标
        # term_mention=f"""
        #     被告人被指控的罪名有：{all_term}
        #     你的策略应当针对该罪名的定罪、量刑进行制定。一定要有针对性。
        # """
        defendant_strategy_prompt="""
        【防御策略】被告人需要制定自己的防御策略，以减轻自己的罪责。如果目标是带来减刑，则应当表示认罪认罚悔罪态度；若目标是否认指控自证无罪，则应当坚定地声称自身的清白。
        """
        # res=self.speak("起诉状："+prosecution_statement+"被告人信息："+defendant_information+"证据："+evidence+"参考资料："+str(self.init_QA_pair),
        #     """
        #     你是辩护人，你的当事人（被告人）被指控犯罪。
        #     在庭审开始前，你要根据起诉状、被告人信息、证据条目，帮助被告人制定其在本次出庭的目标、防御策略。
        #     如果被告人提出了诉求，那么诉求中的内容应当出现在被告人的目标与策略中。
        
        #     """
        #     +term_mention+
        #     """
        #     【目标】被告人的目标是在已知信息的范围内，维护自己的利益。良好的认罪认罚态度有可能带来减刑，直接否认指控自证无罪可能会免除罪责，也有可能会罪加一等。
        #     """
        #     +defendant_strategy_prompt+
        #     """
        #     此前，作为辩护人，你自己制定的目标和策略是：
        #     """+
        #     "辩护目标："+self.goal+"辩护策略"+str(self.strategy)+
        #     """
        #     **注意，你代表被告人的利益，所以给被告人制定的策略要和你自己制定的辩护策略相一致。**
        #     **注意，策略必须要符合实际，如果证据中没有提及赔偿、谅解等情节，则不应该有这部分策略！**
        #     **反之，如果被告人做出了赔偿、征得了谅解，则应当有这部分的策略**
        #     **如果被告人提出了诉求，那么诉求中的内容应当出现在被告人的目标与策略中。**
            
        #     你的回复应当严格按照如下格式：
        #     [一句话总结目标]|[防御策略，分条回复。1.xxx2.xxx3.xxx]
        #     回复时不要包含[]
        #     例如：
        #     希望以悔罪的态度争取xxxx|1.积极悔罪xxx2.说明自身自首xxx
            
            
        #     """
        #                         )
        # res=res.split("|")
        return defendant_strategy_prompt,"",""
    
    # def think_answer(self,questions):
    #     self.answer=self.speak("出庭目标："+self.goal+self.strategy+"辩护人询问的问题："+self.questions,
    #             """
    #             在法庭调查阶段，辩护人可能会向被告人询问一些问题。
    #             作为被告人，请你根据你的出庭目标、防御策略，针对辩护人打算询问的问题依次做出回复。
    #             你的回复应当严格按照如下形式：
    #             1.xxxx
    #             2.xxxx
    #             3.xxxx
    #             """
    #             )
    
    def set_strategy(self,strategy_prompt,goal,strategy,prosecution_statement,defendant_information,evidence):
        # self.all_term=all_term
        self.prosecution_statement=prosecution_statement
        self.defendant_information=defendant_information
        self.evidence_pool=evidence
        self.strategy_prompt=strategy_prompt
        self.goal=goal
        self.strategy=strategy
    
class Agent_Judge(Agent):
    def __init__(
        self,
        id: int,
        name: str,
        role: str,
        description: str,
        llm: Any,
    ):
        super().__init__(id,name,role,description,llm)
        self.debate_focus=""
        # self.conclusion=""
    def call_thought(self,save_only=False):
        res={}
        res.update({"辩论焦点与查明情况":self.debate_focus,
                    "记忆":self.memory,
                    "规划":self.current_plan})
        return res
        
    def preparation(self, prosecution_statement, defendant_information, evidence):
        self.evidence_pool=evidence
        self.prosecution_statement=prosecution_statement
        self.defendant_information=defendant_information
        
        # term_mention=f"""
        #     被告人被指控的罪名有：{all_term}
        #     你所要查明的事实也应当针对该罪名的定罪、量刑进行制定。一定要有针对性。
        # """
        self.strategy_prompt="""
            作为审判长，你需要查明案件的事实，所以辩论焦点还要考虑涵盖以下几个角度的内容：
            辩论焦点包括：
            定罪与否、责任认定情况（比如年龄是不是符合，主责或次责等）、量刑情况（是否有一些从轻或从重处罚的情节，是否自首，是否取得被害人原谅）
            还应当包括应当查明但双方还没有讨论清楚的内容，你认为对定罪量刑有价值的问题。
            辩论焦点应当具体且灵活。
        """
        info="起诉状："+prosecution_statement+"被告人信息："+defendant_information+"证据："+evidence
        task="""
            在庭审开始前，你要根据起诉状、被告人信息、证据条目，生成本案可能的辩论焦点。
            """+self.crime3aspect+"""
            **只有当三个角度都成立，且具有直接因果关系时，罪名才真正成立**
            所以你的辩论焦点也应该围绕这三个角度。越具体越好！
            """+self.strategy_prompt
        
        self.init_QA_pair=""# self.plan(info+task)
        
        # res=self.speak(info+"参考资料："+str(self.init_QA_pair),
        #     task+
        #     """
        #     辩论焦点从1开始编号
            
        #     例如：1.是否构成故意伤害罪。需要讨论直到被告表示认罪受罚，或证明被告罪行不满足故意伤害罪条件。若此前被告已经明确表示认罪，则无需进行辩论。2.是否构成自首。3.是否征得被害人谅解。
            
        #     请严格按照以下格式回复：
        #     1.法庭辩论焦点2.法庭辩论焦点3.法庭辩论焦点
        #     """
        #                         )
            
        self.debate_focus=""
        
        
        self.questions=""
        # self.speak("起诉状："+prosecution_statement+"被告人信息："+defendant_information+"证据："+evidence+"辩论焦点："+self.debate_focus+"参考资料："+str(self.init_QA_pair),
        #         """
        #         在法庭调查阶段，作为审判长，你要查清案件事实，围绕定罪量刑相关问题对被告人进行发问。
        #         比如针对案件事实，犯罪动机，犯罪情节等。
        #         现在请你根据起诉状、被告人信息、证据条目、辩论焦点制定法庭调查阶段拟询问被告人的问题。
                
        #         问题应当涵盖多个角度，而总数不要太多！
                
        #         请分条回复。**按照重要性先后顺序！**
        #         例如
        #         1.xxxx
        #         2.xxxx
        #         3.xxxx
        #         """)
