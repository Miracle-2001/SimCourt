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
with open(os.path.join(pwd,'data.jsonl')) as f:
    for line in f:
        case = json.loads(line)
        cases.append(case)
print("cases loaded.")


from tqdm import tqdm

dict_list=[]
ids=range(len(cases))
for id in tqdm(ids):
    case=cases[id]
    articles=query_model(case['qw']+"""
                         请把其中【最终判决依据的【刑法】法条】列出来，返回的法条之间用#隔开，并按照法条顺序排列。

                         返回格式为：
                         法条1#法条2#法条3
                         
                         【示例1】
                         依照《中华人民共和国刑法》第二百三十三条、第四十五条、第六十一条、第六十二条、第六十七条第一款、第七十二条第一款、第七十三条第二、三款之规定，判决如下被告人殷某犯过失致人死亡罪，判处有期徒刑一年，缓刑一年。
                         
                         则你应当返回：
                         第四十五条#第六十一条#第六十二条#第六十七条第一款#第七十二条第一款#第七十三条第二#第七十三条第三款#第二百三十三条
                         
                         【示例2】
                         依照《中华人民共和国刑法》第二百三十三条、第一百九十条、第四十五条、第六十一条，《民法典》第十七条，《婚姻法》第二十七条...
                         （非刑法法条应当忽略）
                         
                         则你应当返回：
                         第四十五条#第六十一条#第一百九十条#第二百三十三条
                         
                         再次注意：
                         1.【最终判决依据】的刑法法条，不是最后判决依据的不要包含
                         2.最终判决依据的【刑法】法条，不是刑法法条不要包含。
                         3.如果是第x条第x款，则要把条和款都包含在内！
                         4.注意返回这些条目按数字从小到大排序的结果!
                         5.不要重复包含同一个法条！同一个法条下不同的款应当包含，同一个法条下同一款不能出现多次！
                         6.严格按照格式返回，不要说多余的话。
                         """
                         ).split("#")
    articles = list(set(articles))
    crimes=query_model(str(articles)+
                      """
                      把其中所有的【第一百零二条及之后的法条】都提取出来！
                      比如一百零五在一百零二条之后，所以算，而九十六条就不算。
                      
                      你的返回格式为：
                      法条1#法条2#法条3
                      （如果有多个法条，之间用#间隔！）
                      
                      注意！
                      1.如果是第x条第x款，那么要按照条来看。比如第六十二条第三款，则应当认为是第六十二条，不算在【第一百零二条及之后的法条】中！！而第一百三十三条第一款就算在内。
                      2.如果同一个法条出现多次，那么应该按照一次计算。
                      3.如果同一个法条下的不同的款，那么按照多次计算。
                      4.请严格按照格式返回，不要说多余的话!
                      """
                      ).split("#")
    crimes = list(set(crimes))
    dict_list.append({"id":id,"articles":articles,"crimes":crimes,"count":len(crimes)})
    with open('articles.json', "w", encoding="utf-8") as f:
        json.dump(dict_list, f, ensure_ascii=False, indent=2)