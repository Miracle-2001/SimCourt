import fastapi
from fastapi import HTTPException
from pydantic import BaseModel
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
import os

# 假设你已经定义了一个函数来加载模型路径
def get_model_path(model_name):
    if model_name == "llama3.1-8b-instruct":
        return "/home/lijiaqi/ParaAgent/model/meta-llama/Llama-3.1-8B-Instruct"
    elif model_name == "qwen2.5-7b-instruct":
        return "/home/lijiaqi/ParaAgent/model/Qwen/Qwen2.5-7B-Instruct"
    else:
        return model_name

# 定义模型加载的API
class ModelRequest(BaseModel):
    model_name: str
    messages: list

app = fastapi.FastAPI()

# 创建一个全局模型字典，防止重复加载
loaded_models = {}

# 加载模型
def load_model(model_name: str):
    print("model_name to load: ", model_name)
    if model_name in loaded_models:
        return loaded_models[model_name]
    
    model_path = get_model_path(model_name)
    if not os.path.exists(model_path):
        raise HTTPException(status_code=404, detail="Model path not found")
    print("model_path ok: ", model_path)

    model = AutoModelForCausalLM.from_pretrained(model_path)
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    print(f"Model and tokenizer loaded from {model_path}")

    loaded_models[model_name] = {"model": model, "tokenizer": tokenizer}
    
    print("model loaded: ", model_name)
    return loaded_models[model_name]

# API 路由，处理请求
@app.post("/predict/")
async def predict(request: ModelRequest):
    try:
        # 加载模型
        model_data = load_model(request.model_name)
        model = model_data["model"]
        tokenizer = model_data["tokenizer"]
        
        # 手动补全
        # print("model loaded : ", model)
        # # 将消息列表转换为 Qwen 的对话格式
        # prompt = ""
        # for msg in request.messages:
        #     role = msg['role']
        #     content = msg['content']
        #     if role == "system":
        #         prompt += f"<|im_start|>system\n{content}<|im_end|>\n"
        #     elif role == "user":
        #         prompt += f"<|im_start|>user\n{content}<|im_end|>\n"
        #     elif role == "assistant":
        #         prompt += f"<|im_start|>assistant\n{content}<|im_end|>\n"
        
        # prompt += "<|im_start|>assistant\n"  # 添加助手角色标记以开始生成
        
        # # 编码输入文本
        # inputs = tokenizer(prompt, return_tensors="pt")

        # 使用chat函数补全
        inputs = tokenizer(
            tokenizer.apply_chat_template(request.messages, 
                                      add_generation_prompt=True, 
                                      tokenize=False, 
                                      pad_token_id=tokenizer.pad_token_id),
            return_tensors = "pt")
        
        print(f"inputs: {inputs}")
        # 获取模型输出
        outputs = model.generate(inputs['input_ids'], max_length=8000)
        print(f"outputs: {outputs}")
        # 解码输出
        result = tokenizer.decode(outputs[0], skip_special_tokens=True)
        print(f"result: {result}")
        # 解析最终回复
        if "assistant\n" in result:
            response_text = result.split("assistant\n", 1)[-1].strip()
        else:
            response_text = result.strip()  # 兜底处理，防止解析失败

        print(f"response_text: {response_text}")
        # 生成返回格式
        return {
            "choices": [{"message": {"content": response_text}}],
            "usage": {
                "completion_tokens": len(outputs[0]), 
                "prompt_tokens": len(inputs["input_ids"][0])
            }
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 启动 FastAPI 服务器
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
