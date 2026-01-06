import json
import os
import random
import logging
import argparse
from tqdm import tqdm
import gradio as gr
import datetime
import time
from rich.console import Console
import ast
from rich.logging import RichHandler
from rich.panel import Panel
from tqdm import trange
from tqdm import tqdm
import sys
# from EMDB.db import db
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from LLM.offlinellm import OfflineLLM
from LLM.apillm import APILLM
from agent import Agent
from frontEnd import frontEnd
from settings import data_gen_prompt
# from SimCourt.AgentCourt.evaluation.evaluation import load_json
def load_json(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)
        
def get_apillm(name):
    return APILLM(
            api_key="JWXGr1DMcAz4yGPzPtdqHs4G",
            api_secret="4J4sAHLH4H6VmyTu3PbGNeqIN8uqqF9Y",
            platform="proxy",
            model=name,
        )
    
def save_json(js,filepath,filename):
    if os.path.exists(filepath) == False:
        os.makedirs(filepath)
    # js=json.loads(js)
    with open(os.path.join(filepath,filename),"w", encoding="utf-8") as f:
        json.dump(js, f, ensure_ascii=False, indent=2)

def get_res(agent,context,prompt,id,up=2):
    for i in range(up):
        if i>=0:
            prompt=prompt+"提醒：请不要想太多，不用检查。"
        max_tokens=4096
        if i==1:
            max_tokens=2048
        res=agent.speak(
            context=context,
            prompt=prompt,
            max_tokens=max_tokens
        )
        if res!="":
            return res
    with open("failed_find_name.txt", "a", encoding="utf-8") as file:
        file.write(str(id)+" ")    
    return False

def merge_strings(lst,size=10):
    new_list = ['@@'.join(lst[i:i+size]) for i in range(0, len(lst), size)]
    # if len(lst) % size != 0:
    #     new_list.append('@@'.join(lst[-(len(lst) % size):]))
    return new_list

def anonymity(dict,agent2,id):
    final_evidence=[[],[]]
    for t in range(2):
        evidence_merge=merge_strings(dict["evidence"][t])
        if evidence_merge==[]:
            continue
        # print(evidence_merge)
        for term in evidence_merge:
            tmp=get_res(
                agent=agent2,
                context=term,
                prompt=data_gen_prompt.prompt_anonymity,
                id=id
            )
            if tmp==False:
                return {}
            tmp=tmp.split("@@")
            final_evidence[t]+=tmp
    dict["evidence"]=final_evidence     
        
    # if t==0:
    #     evidence_merge=evidence_merge+"||1.谅解书谅解书谅解书"
    
    # debate_focus_merge="||".join(dict["debate_focus"])
    
    # merge_str=dict["defendant_information"]+"#"+dict["prosecution_statement"]+"#"+dict["advocate_statement"]+"#"+evidence_merge+"#"+debate_focus_merge
    
    # anonymity=agent2.speak(
    #     context=merge_str,
    #     prompt=data_gen_prompt.prompt_anonymity,
    # )
    # anonymity=anonymity.split("#")
    dict["defendant_information"]=get_res(
        agent=agent2,
        context=dict["defendant_information"],
        prompt=data_gen_prompt.prompt_anonymity,
        id=id
    )
    dict["prosecution_statement"]=get_res(
        agent=agent2,
        context=dict["prosecution_statement"],
        prompt=data_gen_prompt.prompt_anonymity,
        id=id
    )
    dict["prosecution_statement_sub"]=get_res(
        agent=agent2,
        context=dict["prosecution_statement_sub"],
        prompt=data_gen_prompt.prompt_anonymity,
        id=id
    )
    dict["fact"]=get_res(
        agent=agent2,
        context=dict["fact"],
        prompt=data_gen_prompt.prompt_anonymity,
        id=id
    )
    if dict["result"]!="": 
        dict["result"]=get_res(
            agent=agent2,
            context=dict["result"],
            prompt=data_gen_prompt.prompt_anonymity,
            id=id
        )
    if "request" in dict:
        dict["request"]=get_res(
            agent=agent2,
            context=dict["request"],
            prompt=data_gen_prompt.prompt_anonymity,
            id=id
        )
    # dict["advocate_statement"]=get_res(
    #     agent=agent2,
    #     context=dict["advocate_statement"],
    #     prompt=data_gen_prompt.prompt_anonymity,
    #     id=id
    # )
    # tmp=get_res(
    #     agent=agent2,
    #     context=debate_focus_merge,
    #     prompt=data_gen_prompt.prompt_anonymity,
    #     id=id
    # )
    # if tmp==False:
    #     return {}
    # dict["debate_focus"]=tmp.split("||")
    
    return dict
        
if __name__ =="__main__":
    agent=Agent(
        id=-1,
        name=-1,
        role='generator',
        description="",
        llm=get_apillm("deepseek-v3-250324"),
    )
    
    # basic_path='../data/data0417'
    basic_path='../data/data_video'
    # files=os.listdir(basic_path)
    # files=["example_1","example_3"]+["example_"+str(i) for i in range(6,100)]
    # ids = [0 ,1 ,230, 231, 232 ,233, 234 ,240 ,241, 242 ,243, 244, 250, 251, 252, 253 ]
    # for i in range(40):  # 5组数字
    #     for j in range(5):
    #         if i * 10+j <=330:
    #             continue
    #         ids.append(i * 10+j)
    # ids = [382 ,64 ,181 ,104, 
    #        353,62,214,241,262]
    # ids=[214]
    ids=[i for i in range(20,21)]
    files=["example_"+str(i) for i in ids]
    
    # 
    
    for f in tqdm(files):
        print(f)
        # if f=="example_6":
        #     continue
        try:
            if os.path.isdir(os.path.join(basic_path,f))==False:
                continue
            # print("OK")
            dict=load_json(os.path.join(basic_path,f,'data_raw.json'))
            dict=anonymity(dict,agent,id=f.split("_")[-1])
            
            # print(id,dict)
        
            name="data_tuned.json"
            save_json(dict,os.path.join(basic_path,f),name)
        except Exception as e:
            with open("failed_find_name.txt", "a", encoding="utf-8") as file:
                file.write(str(f.split("_")[-1])+" ")   
            continue
    