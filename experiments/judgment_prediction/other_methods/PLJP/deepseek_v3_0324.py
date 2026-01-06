import openai
from dotenv import load_dotenv
import os
import httpx
import backoff

MAX_TRIES=10
MAX_TIME=10

load_dotenv()

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

@backoff.on_exception(backoff.expo, openai.OpenAIError, max_tries=MAX_TRIES, max_time=MAX_TIME, raise_on_giveup=True)
def completion_with_backoff(**kargs):
    return client.chat.completions.create(
        **kargs
    )

def call_deepseek_v3_0324(messages,temperature=0,max_tokens=8192):
    messages = [
        {"role": "system", "content": "你是一名专业的法官。"},
        {"role": "user", "content": str(messages)},
    ]
    for i in range(3):
        print("length:",len(str(messages)))
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
        print(content)
        # content = response.choices[0].message.content
        # print("res",content)
        if content=="":
            continue
        return content
    return "No Response.",{}

if __name__=="__main__":
    print(call_deepseek_v3_0324("今天是几月几日？"))