from api_pool import api_pool
"""
可用的 API：
"o1-mini"
"gpt-4"
"gpt-4o-mini"
"gpt-3.5-turbo"
"claude-3-sonnet"
"chatglm-4-air"
"deepseek"
"""
#! NOTE: o1-mini不可以有system prompt

# if __name__ == "__main__":
#     prompt = "你好，什么是api？"
#     model = "o1-mini"
#     print(f"Model: {model}")
#     result, usage = api_pool[model](prompt)
#     print(result)


from openai import OpenAI
import httpx

client = OpenAI(
    base_url="https://svip.xty.app/v1", 
    api_key="sk-r0WeYOdkMjzYdnSxEcC8B931Aa904e4bBaCcAc2a57D803F1",
    http_client=httpx.Client(
        base_url="https://svip.xty.app/v1",
        follow_redirects=True,
    ),
)

completion = client.chat.completions.create(
  model="gpt-4o-mini",
  messages=[
    {"role": "user", "content": "Hello!"}
  ]
)

print(completion.choices[0].message.content)



# client = OpenAI(api_key="sk-6e32712cdaef42a4a867d463d9e87d5e", base_url="https://api.deepseek.com")

# response = client.chat.completions.create(
#     model="deepseek-chat",
#     messages=[
#         {"role": "system", "content": "You are a helpful assistant"},
#         {"role": "user", "content": "Hello"},
#     ],
#     stream=False
# )

# content = response.choices[0].message.content

# print(content)