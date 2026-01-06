import fastapi
from fastapi import HTTPException
from pydantic import BaseModel
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch
import os

# 假设你已经定义了一个函数来加载模型路径
def get_model_path(model_name):
    if model_name == "llama3.1-8b-instruct":
        return "/home/lijiaqi/ParaAgent/model/meta-llama/Llama-3.1-8B-Instruct"
    elif model_name == "qwen2.5-7b-instruct":
        return "/home/lijiaqi/ParaAgent/model/Qwen/Qwen2.5-7B-Instruct"
    else:
        return model_name

# 创建一个client类来模拟调用模型
class LocalModelClient:
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.model_data = self.load_model(model_name)

    def load_model(self, model_name: str):
        model_path = get_model_path(model_name)
        if not os.path.exists(model_path):
            raise HTTPException(status_code=404, detail="Model path not found")

        model = AutoModelForCausalLM.from_pretrained(model_path)
        tokenizer = AutoTokenizer.from_pretrained(model_path)
        return {"model": model, "tokenizer": tokenizer}

    def chat(self, messages: list, stream: bool = False):
        tokenizer = self.model_data["tokenizer"]
        model = self.model_data["model"]

        # 假设messages是一个包含dict的列表，每个dict包含"role"和"content"
        input_text = " ".join([msg["content"] for msg in messages])

        inputs = tokenizer(input_text, return_tensors="pt")
        outputs = model.generate(inputs["input_ids"], max_length=100)

        response_text = tokenizer.decode(outputs[0], skip_special_tokens=True)

        # 模拟返回的格式
        return {
            "choices": [{"message": {"content": response_text}}],
            "usage": {"completion_tokens": len(outputs[0]), "prompt_tokens": len(inputs["input_ids"][0])}
        }

# FastAPI部分
app = fastapi.FastAPI()

# 定义请求模型
class ModelRequest(BaseModel):
    model_name: str
    messages: list  # 保证接收的字段名为 messages

@app.post("/predict/")
async def predict(request: ModelRequest):
    try:
        # 根据请求的模型名称创建client
        client = LocalModelClient(request.model_name)
        
        # 调用chat方法获取模型的响应
        response = client.chat(messages=request.messages, stream=False)
        
        # 返回内容和token使用信息
        content = response["choices"][0]["message"]["content"]
        usage_info = {
            "completion_tokens": response["usage"]["completion_tokens"],
            "prompt_tokens": response["usage"]["prompt_tokens"],
        }
        return {"content": content, "usage": usage_info}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 启动 FastAPI 服务器
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
