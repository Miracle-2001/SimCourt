import openai
from openai import OpenAI
import httpx
from dotenv import load_dotenv
import os
import backoff
import requests
from pydantic import BaseModel
import re

# import megatechai
# megatechai.api_key = "mega"
# megatechai.model_api_url = "http://region-31.seetacloud.com:39638/llm-api/"

class ModelRequest(BaseModel):
    model_name: str
    messages: list

from zhipuai import ZhipuAI

MAX_TRIES=10
MAX_TIME=10

load_dotenv()

os.environ['BASE_URL'] = "https://svip.xty.app/v1"
os.environ['API_KEY'] = "sk-IDaJAtYpgbgprsWRGBeVpQtmL4ddqTtElxbSYcr3eNMdACzG"


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

@backoff.on_exception(backoff.expo, openai.OpenAIError, max_tries=MAX_TRIES, max_time=MAX_TIME, raise_on_giveup=True)
def completion_with_backoff(**kargs):
    return client.chat.completions.create(
        **kargs
    )

BASE_MODEL="qwen2.5-32b-instruct"

def query_model(messages, model_name, sys_msg=None, temperature=0.7, max_tokens=1024):
    print("query_model",model_name,temperature)
    # msgs = []
    # if sys_msg is not None:
    #     msgs.append({"role": "system", "content": sys_msg})
    # msgs.append({"role": "user", "content": msg})
    tokens_param = "max_completion_tokens" if model_name == "o1-mini" else "max_tokens"

    if model_name == BASE_MODEL:
        print("base_model ",messages)
        url = "http://127.0.0.1:8005/predict/"
        data = {
            "model_name": model_name, 
            "messages": messages
            }
        post_data = ModelRequest(**data)
        # 发送POST请求
        print("posting..")
        response = requests.post(url, json=post_data.model_dump())
        print("post!")
        response_data = response.json()
        content = response_data['choices'][0]['message']['content']
        print(content)
        return content, {
            "completion_tokens": response_data['usage']['completion_tokens'],
            "prompt_tokens": response_data['usage']['prompt_tokens'],
        }

    if model_name == "qwen2.5-7b-instruct" or model_name == "distill-qwen2.5-7b-instruct" or model_name == "qwen2.5-32b-instruct" or model_name=="QwQ-32B":
        url = "http://127.0.0.1:8002/predict/"
        data = {
            "model_name": model_name, 
            "messages": messages
            }
        post_data = ModelRequest(**data)
        # 发送POST请求
        response = requests.post(url, json=post_data.model_dump())
        response_data = response.json()
        content = response_data['choices'][0]['message']['content']

        return content, {
            "completion_tokens": response_data['usage']['completion_tokens'],
            "prompt_tokens": response_data['usage']['prompt_tokens'],
        }
    elif model_name == "Llama-3.1-8B-Instruct" or model_name == "glm-4-9b-chat":
        url = "http://127.0.0.1:8002/predict/"
        data = {
            "model_name": model_name, 
            "messages": messages
            }
        post_data = ModelRequest(**data)
        # 发送POST请求
        response = requests.post(url, json=post_data.model_dump())
        response_data = response.json()
        content = response_data['choices'][0]['message']['content']

        return content, {
            "completion_tokens": response_data['usage']['completion_tokens'],
            "prompt_tokens": response_data['usage']['prompt_tokens'],
        }
    elif model_name == "glm-4-air":
        # https://open.bigmodel.cn/dev/api/normal-model/glm-4#sdk
        client = ZhipuAI(api_key="d53d76ddaf28b10adb14ff67deb7196f.LEtOwntH3vx08gP1") 
        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=temperature
        )
        content = response.choices[0].message.content
        return content, {
            "completion_tokens": response.usage.completion_tokens,
            "prompt_tokens": response.usage.prompt_tokens,
        }
    elif model_name == "deepseek-official":
        client = openai.OpenAI(api_key="sk-1d9535a9f8584209a3621dd2db9493e8", base_url="https://api.deepseek.com")
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            stream=False
        )

        content = response.choices[0].message.content
        return content, {
            "completion_tokens": response.usage.completion_tokens,
            "prompt_tokens": response.usage.prompt_tokens,
        }
    elif model_name == "deepseek-v3-silicon":
        # print("inside silicon deepseek-r1 ")
        for i in range(3):
            client = OpenAI(
                base_url='https://api.siliconflow.cn/v1',
                api_key='sk-gkdahtyanpeqrloadhiqbjarcmzfqlbrpjzhummgqxnedhjw'
            )

            # 发送带有流式输出的请求
            print("length:",len(str(messages)))
            response = client.chat.completions.create(
                model="Pro/deepseek-ai/DeepSeek-V3",
                messages=[
                    {"role": "user", "content": str(messages)}
                ],
                stream=False  # 启用流式输出
            )
            # 逐步接收并处理响应
            content = response.choices[0].message.content
            if content=="":
                continue
            return content,{}
        return "No Response.",{}
    elif model_name == "deepseek-v3-250324":
        for i in range(3):
            print("length:",len(str(messages)))
            response = completion_with_backoff(
                model="deepseek-v3-250324",
                messages=messages,
                temperature=temperature,
                **{tokens_param: max_tokens},
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
            return content, {
                "completion_tokens": None,#response.usage.completion_tokens,
                "prompt_tokens": None,#response.usage.prompt_tokens,
            }
        return "No Response.",{}
        # response = completion_with_backoff(
        #     model="deepseek-reasoner",
        #     messages=messages,
        #     temperature=temperature,
        #     **{tokens_param: max_tokens},
        # )
        # content = response.choices[0].message.content
        # # 删除content中<think>和</think>之间的内容
        # cleaned_text = re.sub(r'<think>[\s\S]*?</think>', '', content, flags=re.DOTALL)
        # return cleaned_text, {
        #     "completion_tokens": response.usage.completion_tokens,
        #     "prompt_tokens": response.usage.prompt_tokens,
        # }
            
    elif model_name == "distill-qwen2.5-7b-instruct":
        url = "http://127.0.0.1:8000/predict/"
        data = {
            "model_name": model_name, 
            "messages": messages
            }
        post_data = ModelRequest(**data)
        # 发送POST请求
        response = requests.post(url, json=post_data.model_dump())
        response_data = response.json()
        content = response_data['choices'][0]['message']['content']
        print(f'original content from qwen-2.5-r1-distill-7b: {content}')
        cleaned_text = re.sub(r'<think>[\s\S]*?</think>', '', content, flags=re.DOTALL)
        if "</think>" in cleaned_text:
            cleaned_text = cleaned_text.split("</think>")[-1].strip()
        return cleaned_text, {
            "completion_tokens": response_data['usage']['completion_tokens'],
            "prompt_tokens": response_data['usage']['prompt_tokens'],
        }
    else:
        print("length:",len(str(messages)))
        response = completion_with_backoff(
            model=model_name,
            messages=messages,
            temperature=temperature,
            **{tokens_param: max_tokens},
        )
        content = response.choices[0].message.content
        print("res",content)
        return content, {
            "completion_tokens": response.usage.completion_tokens,
            "prompt_tokens": response.usage.prompt_tokens,
        }

# 这里的 model_name 是请求体中的参数，未必是模型的正式名称，为了避免混淆，这里将其封装，只对外暴露模型的正式名称
def query_o1_mini(messages, **kwargs):
    return query_model(messages=messages, model_name="o1-mini", **kwargs)

def query_gpt_4(messages, **kwargs):
    return query_model(messages=messages, model_name="gpt-4-0125-preview", **kwargs)

def query_gpt_4o_mini(messages, **kwargs):
    return query_model(messages=messages, model_name="gpt-4o-mini", **kwargs)

def query_gpt_35_turbo(messages, **kwargs):
    return query_model(messages=messages, model_name="gpt-3.5-turbo-0125", **kwargs)

def query_claude_3_haiku(messages, **kwargs):
    return query_model(messages=messages, model_name="claude-3-haiku-20240307", **kwargs)

def query_claude_3_opus(messages, **kwargs):
    return query_model(messages=messages, model_name="claude-3-opus-20240229", **kwargs)

def query_claude_3_sonnet(messages, **kwargs):
    return query_model(messages=messages, model_name="claude-3-sonnet-20240229", **kwargs)

def query_legalone(messages, **kwargs):
    return query_model(messages=messages, model_name="0809_qa_0811_with92k_belle-ep4", **kwargs)

def query_glm4_air(messages, **kwargs):
    return query_model(messages=messages, model_name="glm-4-air", **kwargs)

def query_deepseek_official(messages, **kwargs):
    return query_model(messages=messages, model_name="deepseek-official", **kwargs)

def query_qwen(messages, **kwargs):
    return query_model(messages=messages, model_name="qwen2.5-7b-instruct", **kwargs)

def query_qwen_32b(messages, **kwargs):
    return query_model(messages=messages, model_name="qwen2.5-32b-instruct", **kwargs)

def query_qwen_7b_distill(messages, **kwargs):
    return query_model(messages=messages, model_name="distill-qwen2.5-7b-instruct", **kwargs)

def query_deepseek_r1(messages, **kwargs):
    return query_model(messages=messages, model_name="deepseek-r1", **kwargs)

def query_llama3_1_8b_instruct(messages, **kwargs):
    return query_model(messages=messages, model_name="Llama-3.1-8B-Instruct", **kwargs)

def query_glm4_9b_chat(messages, **kwargs):
    return query_model(messages=messages, model_name="glm-4-9b-chat", **kwargs)

def query_qwq_32b(messages, **kwargs):
    return query_model(messages=messages, model_name="QwQ-32B", **kwargs)

def query_deepseek_v3_250324(messages, **kwargs):
    return query_model(messages=messages, model_name="deepseek-v3-250324", **kwargs)

# 这里的 key 是模型的正式名称，使用时无需关心请求体中的名称
api_pool = {
    "gpt-3.5-turbo": query_gpt_35_turbo,
    "gpt-4": query_gpt_4,
    "gpt-4o-mini": query_gpt_4o_mini,
    "o1-mini": query_o1_mini,

    "claude-3-haiku": query_claude_3_haiku,
    "claude-3-opus": query_claude_3_opus,
    "claude-3-sonnet": query_claude_3_sonnet,

    "legalone": query_legalone,
    "chatglm-4-air": query_glm4_air,
    "deepseek-official": query_deepseek_official,
    "deepseek-v3-250324":query_deepseek_v3_250324,
    "deepseek-r1": query_deepseek_r1,
    "qwen2.5-7b-instruct": query_qwen,
    "qwen2.5-32b-instruct": query_qwen_32b,
    "distill-qwen2.5-7b-instruct": query_qwen_7b_distill,
    "QwQ-32B":query_qwq_32b,
    "glm-4-9b-chat": query_glm4_9b_chat,
    "Llama-3.1-8B-Instruct": query_llama3_1_8b_instruct
}
