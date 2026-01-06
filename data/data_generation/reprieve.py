import json
import os
import random
import logging
import argparse
import gradio as gr
import datetime
import time
from rich.console import Console
import ast
from rich.logging import RichHandler
from rich.panel import Panel
from tqdm import trange
from tqdm import tqdm
# from EMDB.db import db
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from LLM.offlinellm import OfflineLLM
from LLM.apillm import APILLM
from agent import Agent
from frontEnd import frontEnd
from settings import data_gen_prompt
from crime_selection import get_apillm


agent=Agent(
        id=-1,
        name=-1,
        role='generator',
        description="",
        llm=get_apillm("deepseek-v3-250324")
    )
cases=[]
with open(os.path.join('./','data.jsonl')) as f:
    for line in f:
        case = json.loads(line)
        cases.append(case)
print(len(cases))
final=[]

failed=[]
for id in tqdm(range(len(cases))):
    case=cases[id]
    try:
        res=agent.speak(case['result'],"""
                        返回最终判决结果中的缓刑时长，单位为月，返回阿拉伯数字。
                        如果没有缓刑，则返回0
                        
                        例如：
                        ...判处有期徒刑二年六个月，缓刑三年。...
                        返回：
                        36
                        
                        直接返回结果即可，不要说多余的话！
                        """)
        
        case['reprieve']=float(res)
        final.append(case)
    except:
        failed.append(case['pid'])

with open("data_1.jsonl", 'w',encoding="utf-8") as file:
    for js in final:
        # js.update({"term":crime})
        js=json.dumps(js,ensure_ascii=False)
        file.write(js+'\n')