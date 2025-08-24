import backoff
import requests
import os
import httpx
import openai
from openai import OpenAI

os.environ['BASE_URL'] = "https://svip.xty.app/v1"
os.environ['API_KEY'] = "sk-r0WeYOdkMjzYdnSxEcC8B931Aa904e4bBaCcAc2a57D803F1"
# os.environ['BASE_URL'] = 'https://api.siliconflow.cn/v1'
# os.environ['API_KEY'] = 'sk-gkdahtyanpeqrloadhiqbjarcmzfqlbrpjzhummgqxnedhjw'
client = openai.OpenAI(
    base_url=os.getenv("BASE_URL"),
    api_key=os.getenv("API_KEY"),
    http_client=httpx.Client(
        base_url=os.getenv("BASE_URL"),
        follow_redirects=True,
    ),
)

MAX_TRIES=10
MAX_TIME=10
@backoff.on_exception(backoff.expo, openai.OpenAIError, max_tries=MAX_TRIES, max_time=MAX_TIME, raise_on_giveup=True)
def completion_with_backoff(**kargs):
    return client.chat.completions.create(
        **kargs
    )
def query_model(messages, temperature=0.7, max_tokens=1024):
    messages=[
        {"role": "system", "content": ""},
        {"role": "user", "content": messages},
    ]
    for i in range(3):
        # print("length:",len(str(messages)))
        response = completion_with_backoff(
            model="deepseek-v3-250324",
            messages=messages,
            temperature=temperature,
            **{"max_tokens": max_tokens},
            stream=True  # 启用流式输出
        )
        # 逐步接收并处理响应
        
        
        collected_chunks = []
        for chunk in response:
            if not chunk.choices:
                continue
            if chunk.choices[0].delta.content:
                collected_chunks.append(chunk.choices[0].delta.content)

        # 组合输出片段并返回
        content= ''.join(collected_chunks)
        # content = response.choices[0].message.content
        # print("res",content)
        if content=="":
            continue
        return content
    return "No Response."

import json
pwd='./'
cases=[]
with open(os.path.join(pwd,'articles_fine.json')) as f:
    cases=json.load(f)
print("cases loaded.")
print(len(cases))

from tqdm import tqdm

# a=[41, 42, 43, 44, 73, 91, 92, 100, 133, 140, 144, 200, 201, 210, 211, 212, 213, 214, 240, 241, 242, 243, 244, 380, 381, 382, 383, 384]
# print(len(a))

dict_list=[]
ids=range(len(cases))
cnt=0
multi_list=[]
for id in tqdm(ids):
    cs=cases[id]
    assert(cs['id']==id)
    cs['count']=len(cs['crimes'])
    if cs['count']>1 and cs['id']%10<5:
        multi_list.append(cs)
    # cnt+=1
    dict_list.append(cs)
print(len(dict_list))
print(len(multi_list))
with open('articles_multi_crime_maybe.json', "w", encoding="utf-8") as f:
    json.dump(multi_list, f, ensure_ascii=False, indent=2)
'''
实际有问题的数据：
200
214
'''

with open('articles_fine2.json', "w", encoding="utf-8") as f:
    json.dump(dict_list, f, ensure_ascii=False, indent=2)
    
        