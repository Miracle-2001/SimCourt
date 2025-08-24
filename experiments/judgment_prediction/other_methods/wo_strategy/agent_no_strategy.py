# no mem no plan
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
        
    # --- Plan Phase --- #
    def reflect_and_update(self,context:Context,summary=True):
        
        
    
        # if self.role=="审判长":
        #     # res=self.speak("最新的庭审记录:"+context.content+"法庭人员发言记录总结："+str(self.memory)+"目前的证据："+str(self.evidence_pool)+"目前的辩论焦点："+str(self.debate_focus),
        #     #             """
        #     #             你要根据输入的信息，进一步调整/更新辩论焦点。
        #     #             """+self.strategy_prompt+
        #     #             """
        #     #             辩论焦点从1开始编号
        #     #             请严格按照以下格式回复：
        #     #             1.法庭辩论焦点2.法庭辩论焦点3.法庭辩论焦点
        #     #             """
        #     #             )
        #     info="法庭人员发言记录总结："+str(self.memory)+"最新的庭审记录:"+context.content+"目前的证据："+str(self.evidence_pool)+"目前的辩论焦点与查明情况："+str(self.debate_focus)
        #     task="""
        #     作为审判长，你要查明案件的事实。你的任务如下：
        #     （1）你要根据输入的信息，以及当前的辩论焦点和查明情况，进一步调整/更新辩论焦点。
        #     """+self.strategy_prompt+"""
        #     （2）除了调整/更新辩论焦点外，你还要根据输入的信息、更新后的辩论焦点、先前的查明情况，总结现在的每一个焦点的**查明情况。**
        #     """
        #     QA_pair=self.plan(info+task)
        #     res=self.speak(info+"参考资料："+str(QA_pair),
        #                 """
        #                 作为审判长，你要查明案件的事实。你的任务如下：
        #                 （1）你要根据输入的信息，以及当前的辩论焦点和查明情况，进一步调整/更新辩论焦点。
        #                 """+self.strategy_prompt+
        #                 """
        #                 （2）除了调整/更新辩论焦点外，你还要根据输入的信息、更新后的辩论焦点、先前的查明情况，总结现在的每一个焦点的**查明情况。**
        #                 **查明情况**是控辩双方对这个焦点的讨论情况的概述、讨论得是否充分、以及作为审判长你的看法。
        #                 **简要说明即可。**
                        
        #                 最终请严格按照如下格式进行回复：
        #                 辩论焦点从1开始编号，查明情况紧随其后。
        #                 请严格按照以下格式回复：
        #                 1.法庭辩论焦点。查明情况。
        #                 2.法庭辩论焦点。查明情况。
        #                 3.法庭辩论焦点。查明情况。
                        
        #                 例如：
        #                 1.被告人自首是否成立...公诉人认为不构成自首，通过xxx进行证明；辩护人认为构成自首，表示xxx。审判长认为被告人的自首成立，因为xxx
        #                 2.关于证据xx里提到的xxx是否和本案有关联，控辩双方各自认为xxx，审判长认为还需要进一步辩论。
        #                 """
        #                 )
        #     self.debate_focus=res
        # else:
        #     info="之前法庭人员发言记录总结："+str(self.memory)+"最新的庭审记录:"+context.content+"目前的证据："+str(self.evidence_pool)+"拟定的目标："+self.goal+"目前的策略："+str(self.strategy)
        #     task="""
        #     你要根据输入的信息，进一步调整/更新策略。
        #     """+self.strategy_prompt
        #     QA_pair=self.plan(info+task)
        #     res=self.speak(info+"参考资料："+str(QA_pair),
        #                 """
        #                 你要根据输入的信息，进一步调整/更新策略。
        #                 """+self.strategy_prompt+
        #                 """
        #                 你的回复应当严格按照如下格式（分条表述）：
        #                 攻击策略：1.xxx2.xxx3.xxx
        #                 防御策略：1.xxx2.xxx3.xxx
                        
        #                 1.注意，策略要实事求是符合实际！不能无中生有！
        #                 2.直接按照格式返回，不要说多余的话
        #                 """
        #                 )
        #     self.strategy=res
        #     self.check_hallucination(context)
            
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
                你只要返回这一阶段的总结即可。
                """           
                )
            self.memory+="\n\n"+res
    
    def yilvkezhi_retriever(self,prompt):
        url = "http://web.megatechai.com:33615/case_app/wenshu_search/search_and_answer"
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

    def database_retriever(self,query_text:str):
        results = self.db.similarity_search_with_relevance_scores(query_text, k=3)
        if len(results) == 0 or results[0][1] < 0.7: #没有搜到
            print(f"Unable to find matching results.")
            return None
        context_text = "\n\n---\n\n".join([doc.page_content for doc, _score in results])
        return context_text

    def law_retriever(self,query_text):
        if query_text in law_repository:
            return law_repository[query_text]
        return None

    def _get_plan(self,context,hint=""):
        prompt = """
        现在，为了更好地完成任务，有两个工具供你使用。
        1.法条检索库。包含中华人民共和国全部法条，包含刑法、民法典、民事诉讼法等。根据查询内容，可以返回法条内容。
        2.‘一律可知’。可以通过输入法律问题，法律事实，争议焦点，案例信息来获取相关案例以及专业的分析答案。
        请根据你的任务目标和当前信息，决定是否要使用这两个工具。以及要询问什么内容。
        一次可以查询多个问题，多个问题放到list里面。
        
        注意！！
        法条检索库输入的法律名称必须是全称，不能缩写。
        比如必须写明为“中华人民共和国刑法第一条”等
        
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
                "询问":["中华人民共和国民法典第四百六十九条","中华人民共和国刑法第五条"]
            },
            "一律可知":{
                "使用":1
                "询问":["客户信息是否属于公司的商业秘密？","单位可以利用末位淘汰制度与员工解除劳动合同吗？"]
            }
        }
        
        """+hint
        response = self.speak(
            context,
            prompt
        )
        print("Queries",self.role,response)
        return response
            
    def plan(self, context,hint=""):
        now_plan=self._get_plan(context,hint=hint)
        now_plan=json.loads(now_plan)
        
        QA_pair={}
        if now_plan["法条"]["使用"]==1:
            for query in now_plan["法条"]["询问"]:
                answer=self.law_retriever(query)
                if answer is not None:
                    QA_pair.update({query:answer})
                    now_plan["法条"].update({query:answer})
        if now_plan["一律可知"]["使用"]==1:
            for query in now_plan["一律可知"]["询问"]:
                answer=self.yilvkezhi_retriever(query)
                if answer is not None:
                    QA_pair.update({query:answer})
                    now_plan["一律可知"].update({query:answer})
        self.current_plan=now_plan
        self.current_answer=QA_pair
        print("Generate QA_pair",self.role,QA_pair)
        return QA_pair

    def _prepare_queries(
        self, plans: Dict[str, bool], history_context: str
    ) -> Dict[str, str]:
        queries = {}
        if plans["experience"]:
            queries["experience"] = self._prepare_experience_query(history_context)
        if plans["case"]:
            queries["case"] = self._prepare_case_query(history_context)
        if plans["legal"]:
            queries["legal"] = self._prepare_legal_query(history_context)
        return queries

    def _prepare_experience_query(self, history_context: str) -> str:
        instruction = f"You are a {self.role}. {self.description}\n\n"
        prompt = """
        Based on the court history, analyze what kind of experience information is needed.
        Identify the key points and formulate a query to retrieve relevant experiences that can improve logic.
        Provide a JSON string containing query statement.
        like 
        {{
            'query':'劳动争议 处理方法 具体步骤'
        }}
        """
        response = self.llm.generate(
            instruction=instruction, prompt=prompt + "\n\n" + history_context
        )
        return self.extract_response(response)

    def _prepare_case_query(self, history_context: str) -> str:
        instruction = f"You are a {self.role}. {self.description}\n\n"
        prompt = """
        Based on the court history, analyze what kind of case information is needed.
        Identify the key points and formulate a query to retrieve relevant case precedents that can improve agility.
        Provide a JSON string containing query keywords.
        like 
        {{
            'query':'劳动合同纠纷 判决 分析'
        }}
        """
        response = self.llm.generate(
            instruction=instruction, prompt=prompt + "\n\n" + history_context
        )
        return self.extract_response(response)

    def _prepare_legal_query(self, history_context: str) -> str:
        instruction = f"You are a {self.role}. {self.description}\n\n"
        prompt = """
        Based on the court history, analyze what kind of legal information is needed.
        Identify the relevant laws or regulations, such as Civil Law, Labor Law, Family Law, or Labor Dispute, and formulate a query to retrieve relevant legal references that can improve professionalism.
        Provide a JSON string containing query keywords.
        like 
        {{
            'query':'侵权人行为 法律条文'
        }}
        """
        response = self.llm.generate(
            instruction=instruction, prompt=prompt + "\n\n" + history_context
        )
        return self.extract_response(response)

    # --- Do Phase --- #

    def execute(
        self, plan: Dict[str, Any], history_list: List[Dict[str, str]], prompt: str, simple:int
    ) -> str:
        # if not plan:
        #     context = self.prepare_history_context(history_list)
        # else:
        #     context = self._prepare_context(plan, history_list)
        
        history_context = self.prepare_history_context(history_list)
        if simple==1: #审判长宣读辩论焦点
            return self.speak("当前庭审记录："+history_context, prompt)
        elif simple==2: # 最后判决
            context="当前庭审记录："+history_context
            # QA_pair=self.plan(context+prompt.split("#####")[0],hint="提示，可以搜索类似案件判决情况，关注刑期长短，关注社会评价与社会影响，关注是否适用缓刑，是否需要赔偿、处罚罚金，以及具体数值等。**建议至少查询类似案件、实刑刑期长度、缓刑适用、罚金数额！**")
            return self.speak(context, prompt)
        elif simple==6: # 判决书生成
            context="庭审记录总结："+str(self.memory) #+"目前的辩论焦点和查明情况："+str(self.debate_focus)
            # context=history_context
            return self.speak(context, prompt)
        elif simple==5: # 被告人回答是否之前有过其他法律处分
            return self.speak("", prompt)
        
        if self.role=="审判长":
            context="最新的庭审记录:"+history_context
        elif self.role=="被告人":
            context="事实经过："+self.fact+"最新的庭审记录:"+history_context
            prompt+="被告人请按实际情况诚实回答，无中生有可能会加重判罚。例如，如果没有赔偿，或没有取得谅解，就要如实回答没有。"
        else:
            context="之前法庭人员发言记录总结："+str(self.memory)+"最新的庭审记录:"+history_context
            
        if simple==3: #公诉人/辩护人 法庭调查的提问
            context+=""
        
        if simple==4: #审判长打断选项
            return self.speak(context, prompt)
        
        # QA_pair=self.plan(context)
        # return self.speak(context+"参考资料："+str(QA_pair), prompt)
        return self.speak(context, prompt)
    
    def pure_final_judge(self,context,prompt):
        QA_pair=self.plan(context+prompt,hint="提示，可以搜索类似案件判决情况，关注刑期长短，关注社会评价与社会影响，关注是否适用缓刑，是否需要赔偿、处罚罚金，以及具体数值等。**建议至少查询类似案件、实刑刑期长度、缓刑适用、罚金数额！**")
        return self.speak("案件事实"+context+"参考资料："+str(QA_pair), prompt)
        # return self.speak(context, prompt)
    
    def speak(self, context: str, prompt: str, max_tokens=4096) -> str:
        instruction = f"{self.instruction}\n\n"
        full_prompt = f"{context}\n\n{prompt}"
        return self.llm.generate(instruction=instruction, prompt=full_prompt,max_tokens=max_tokens)

    def _prepare_context(
        self, plan: Dict[str, Any], history_list: List[Dict[str, str]]
    ) -> str:
        context = ""
        queries = plan["queries"]

        if "experience" in queries:
            experience_context = self.db.query_experience_metadatas(
                queries["experience"], n_results=3
            )
            context += (
                f"\n遵循下面的经验，以增强回复的逻辑严密性:\n{experience_context}\n"
            )

        if "case" in queries:
            case_context = self.db.query_case_metadatas(queries["case"], n_results=3)
            context += f"\nCase Context:\n{case_context}\n"

        if "legal" in queries:
            legal_context = self.db.query_legal(queries["legal"], n_results=3)
            context += f"\nLaw Context:\n{legal_context}\n"

        if self.log_think:
            self.logger.info(f"Agent ({self.role})\n\n{context}")

        history_context = self.prepare_history_context(history_list)
        context += "\nCommunication History:\n" + history_context + "\n"

        return context

    # --- Reflect Phase --- #

    def reflect(self, history_list: List[Dict[str, str]]):

        history_context = self.prepare_history_context(history_list)

        case_content = self.prepare_case_content(history_context)

        # Legal knowledge base reflection
        legal_reflection = self._reflect_on_legal_knowledge(history_context)
        if self.log_think:
            self.logger.info(f"Agent ({self.role})\n\n{legal_reflection}")

        # Experience reflection
        experience_reflection = self._reflect_on_experience(
            case_content, history_context
        )
        if self.log_think:
            self.logger.info(f"Agent ({self.role})\n\n{experience_reflection}")

        # Case reflection
        case_reflection = self._reflect_on_case(case_content, history_context)
        if self.log_think:
            self.logger.info(f"Agent ({self.role})\n\n{case_reflection}")

        return {
            "legal_reflection": legal_reflection,
            "experience_reflection": experience_reflection,
            "case_reflection": case_reflection,
        }

    def _reflect_on_legal_knowledge(self, history_context: str) -> Dict[str, Any]:
        # Determine if legal reference is needed
        need_legal = self._need_legal_reference(history_context)

        if need_legal:
            query = self._prepare_legal_query(history_context)
            laws = search_law(query)

            processed_laws = []
            for law in laws[:3]:  # Limit to 3 laws
                law_id = str(uuid.uuid4())
                processed_law = self._process_law(law)
                self.add_to_legal(
                    law_id, processed_law["content"], processed_law["metadata"]
                )
                processed_laws.append(processed_law)

            return {"needed_reference": True, "query": query, "laws": processed_laws}
        else:
            return {"needed_reference": False}

    def _need_legal_reference(self, history_context: str) -> bool:
        instruction = (
            f"You are a {self.role}. {self.description}\n\n"
            "Review the provided court case history and evaluate its thoroughness and professionalism. "
            "Determine if referencing specific legal statutes or regulations would enhance the quality of the response. "
            "Return 'true' if additional legal references are needed, otherwise return 'false'."
        )
        prompt = (
            "Court Case History:\n\n"
            + history_context
            + "\n\nIs additional legal reference needed? Output true unless it is absolutely unnecessary. Provide only a simple 'true' or 'false' answer."
        )
        response = self.llm.generate(instruction=instruction, prompt=prompt)

        cleaned_response = response.strip().lower()

        # 检查响应是否包含 'true' 或 'false'
        if "true" in cleaned_response:
            return True
        elif "false" in cleaned_response:
            return False
        else:
            return False

    def _process_law(self, law: dict) -> Dict[str, Any]:

        law_content = (
            law["lawsName"] + " " + law["articleTag"] + " " + law["articleContent"]
        )

        return {
            "content": law_content,
            "metadata": {"lawName": law["lawsName"], "articleTag": law["articleTag"]},
        }

    def _reflect_on_experience(
        self, case_content: str, history_context: str
    ) -> Dict[str, Any]:

        experience = self._generate_experience_summary(case_content, history_context)

        experience_entry = {
            "id": str(uuid.uuid4()),
            "content": experience["context"],  # 这里面放的应该是案件相关的描述
            "metadata": {
                "context": experience["content"],  # 这里面放的应该是案件相关的指导用
                "focusPoints": experience["focus_points"],
                "guidelines": experience["guidelines"],
            },
        }

        # Add to experience database
        self.add_to_experience(
            experience_entry["id"],
            experience_entry["content"],
            experience_entry["metadata"],
        )

        return experience_entry

    def _generate_experience_summary(
        self, case_content: str, history_context: str
    ) -> Dict[str, Any]:
        instruction = f"你是{self.role}。{self.description}\n\n"

        prompt = f"""
        根据以下案例内容和对话历史，生成一个逻辑上连贯的经验总结。请确保回复内容逻辑严密，并能有效指导类似案件的处理。

        案例内容: {case_content}
        对话历史: {history_context}

        请在回复中提供以下内容：
        1. 一个简要的案件背景描述，包括案件的主要争议点和各方立场，不要出现真实人名。
        2. 一个专注于逻辑连贯性的经验描述（内容），包括在处理此类案件时应重点关注的问题和策略。
        3. 有助于逻辑连贯性的3-5个关键点，具体说明如何在实际处理中应用这些关键点。
        4. 保持逻辑连贯性的3-5个指南，提供在处理类似案件时需要特别注意的事项和建议。

        将你的回复格式化为以下结构的JSON对象：
        {{
            "context": "简要背景...",
            "content": "专注于逻辑连贯性的经验描述...",
            "focus_points": "关键点1, 关键点2, 关键点3",
            "guidelines": "指南1, 指南2, 指南3"
        }}
        """

        response = self.llm.generate(instruction, prompt)

        data = self.extract_response(response)

        # 将列表转换为字符串
        return self.ensure_ex_string_fields(data)
        # if data and isinstance(data, dict):
        #    for key, value in data.items():
        #        if isinstance(value, list):
        #           data[key] = ", ".join(value)
        # return data

    def _reflect_on_case(
        self, case_content: str, history_context: str
    ) -> Dict[str, Any]:

        case_summary = self._generate_case_summary(case_content, history_context)

        case_entry = {
            "id": str(uuid.uuid4()),
            "content": case_summary["content"],
            "metadata": {
                "caseType": case_summary["case_type"],
                "keywords": case_summary["keywords"],
                "quick_reaction_points": case_summary["quick_reaction_points"],
                "response_directions": case_summary["response_directions"],
            },
        }

        # Add to case database
        self.add_to_case(
            case_entry["id"], case_entry["content"], case_entry["metadata"]
        )

        return case_entry

    def _generate_case_summary(
        self, case_content: str, history_context: str
    ) -> Dict[str, Any]:
        instruction = f"你是一个{self.role}，擅长快速分析案例并提供敏捷的回应。{self.description}\n\n"

        prompt = f"""
        根据以下案例内容和对话历史，生成一个简洁的案例摘要，以提高在类似情况下回应的敏捷性。请确保回复内容能够帮助快速理解案情并迅速制定回应策略。

        案例内容: {case_content}
        对话历史: {history_context}

        请在回复中提供以下内容：
        1. 案例名称及背景：给出一个凝练的案例名称，并简要描述案件的背景，包括主要争议点和各方立场，不要使用真实人名。
        2. 案件类型：说明这是什么类型的案件（如劳动争议、合同纠纷等）。
        3. 关键词：提供3-5个能够快速捕捉案件本质的关键词。
        4. 快速反应点：列出3-5个对于快速理解和处理此类案件至关重要的要点。
        5. 回应方向：提供3-5个可能的回应方向或角度，以便快速制定回应策略。

        将你的回复格式化为以下结构的JSON对象：
        {{
            "content": "案例名称及背景：...",
            "case_type": "案件类型...",
            "keywords": "关键词1, 关键词2, 关键词3",
            "quick_reaction_points": "要点1, 要点2, 要点3",
            "response_directions": "方向1, 方向2, 方向3"
        }}

        注意：内容应该简洁明了，便于快速识别核心问题和制定回应策略。重点放在能够提高思维敏捷性的信息上,注意格式是上面描述的json。
        """

        response = self.llm.generate(instruction, prompt)

        data = self.extract_response(response)

        # 确保是字符串
        return self.ensure_case_string_fields(data)
        # if data and isinstance(data, dict):
        #    for key, value in data.items():
        #        if isinstance(value, list):
        #            data[key] = ", ".join(value)
        # return data

    # --- Helper Methods --- #

    def extract_json_from_txt(self, response: str) -> Any:
        pattern = r"\{.*?\}"
        match = re.search(pattern, response, re.DOTALL)
        json_str = match.group()

        data = json.loads(json_str)
        return data

    def extract_response(self, response: str) -> Any:
        json_match = re.search(r"\{.*\}", response, re.DOTALL)
        if json_match:
            try:
                cleaned_json_str = re.sub(r"[\x00-\x1F\x7F]", "", json_match.group())
                return json.loads(cleaned_json_str, strict=False)
            except json.JSONDecodeError:
                pass
        return response.strip()

    def _extract_plans(self, plans_str: str) -> Dict[str, bool]:
        try:
            plans = plans_str if isinstance(plans_str, dict) else json.loads(plans_str)
            return {
                "experience": plans.get("experience", False),
                "case": plans.get("case", False),
                "legal": plans.get("legal", False),
            }
        except json.JSONDecodeError:
            return {"experience": False, "case": False, "legal": False}

    def add_to_experience(
        self, id: str, document: str, metadata: Dict[str, Any] = None
    ):
        self.db.add_to_experience(id, document, metadata)

    def add_to_case(self, id: str, document: str, metadata: Dict[str, Any] = None):
        self.db.add_to_case(id, document, metadata)

    def add_to_legal(self, id: str, document: str, metadata: Dict[str, Any] = None):
        self.db.add_to_legal(id, document, metadata)

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
        
    def preparation(self,all_term,prosecution_statement,defendant_information,evidence):
        term_mention=f"""
            被告人被指控的罪名有：{all_term}
            你的策略应当针对该罪名的定罪、量刑进行制定。一定要有针对性。
        """
        
        all_input=term_mention+self.crime3aspect
        
        if self.role=="公诉人":
            self.strategy_prompt="""
            【攻击策略】公诉人需要制定自己的攻击策略，包含被告人犯罪的证据链（通过对证据、法律条文的精准解读说明为什么被告人犯罪），质疑辩护人的证据的关联性与证明效力（例如辩护人出示自首证据，可以质疑是否真的自首），以及论述为什么足以判处起诉状中的刑期（比如社会危害度，可改造程度等）等。
            【防御策略】公诉人需要制定自己的防御策略，包含如何维护自身证据的关联性和证明效力，以应对辩护人和被告人潜在的对证据的质疑。    
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
            res=""
            
        elif self.role=="辩护人":
            info="起诉状："+prosecution_statement+"被告人信息："+defendant_information+"证据："+evidence
            self.strategy_prompt="""
            【攻击策略】辩护人需要制定自己的攻击策略，质疑公诉人的证据（例如说明公诉人的证据与本案件的不具备关联性，或证明效力不够充分），指出其证据不足或推理不合理。
            【防御策略】辩护人需要制定自己的防御策略，以减轻被告人的罪责。包含寻找有利证据、构建合理故事、法律条文的精准解读、强调案件特殊情节、强调积极态度与悔悟等为被告人进行开脱。此外，还要维护自身证据与案件事实的关联性，以应对公诉人潜在的对证据的质疑。
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
            res=""
        res=res.split("|")
        self.goal=""
        self.strategy=""
        self.init_QA_pair=""


        
    def for_defendant(self,all_term,prosecution_statement,defendant_information,evidence):
        # 辩护人和被告人商议最终目标
        term_mention=f"""
            被告人被指控的罪名有：{all_term}
            你的策略应当针对该罪名的定罪、量刑进行制定。一定要有针对性。
        """
        defendant_strategy_prompt="""
        【防御策略】被告人需要制定自己的防御策略，以减轻自己的罪责。如果目标是带来减刑，则应当表示认罪认罚悔罪态度；若目标是否认指控自证无罪，则应当坚定地声称自身的清白。
        """
        res=""
        res=res.split("|")
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
    
    def set_strategy(self,strategy_prompt,goal,strategy):
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
        
    def preparation(self,all_term,prosecution_statement,defendant_information,evidence):
        term_mention=f"""
            被告人被指控的罪名有：{all_term}
            你所要查明的事实也应当针对该罪名的定罪、量刑进行制定。一定要有针对性。
        """
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
            """+term_mention+self.crime3aspect+"""
            **只有当三个角度都成立，且具有直接因果关系时，罪名才真正成立**
            所以你的辩论焦点也应该围绕这三个角度。越具体越好！
            """+self.strategy_prompt
        
        # self.init_QA_pair=self.plan(info+task)
        
        res=""
        self.debate_focus=res
