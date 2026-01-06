import fastapi
from fastapi import HTTPException
from pydantic import BaseModel
from vllm import LLM, SamplingParams
import os

# 假设你已经定义了一个函数来加载模型路径
def get_model_path(model_name):
    if model_name == "Llama-3.1-8B-Instruct":
        return "/liuzyai04/thuir/LLM/Meta-Llama-3.1-8B-Instruct"
    elif model_name == "qwen2.5-7b-instruct":
        return "/liuzyai04/thuir/LLM/Qwen2.5-7B-Instruct"
    elif model_name == "qwen2.5-32b-instruct":
        return "/liuzyai04/thuir/LLM/Qwen2.5-32B-Instruct"
    elif model_name == "QwQ-32B":
        return "/liuzyai04/thuir/LLM/QwQ-32B"
    elif model_name == "glm-4-9b-chat":
        return "/liuzyai04/thuir/LLM/glm-4-9b-chat"
    else:
        return model_name


# 定义模型加载的API
class ModelRequest(BaseModel):
    model_name: str
    messages: list

app = fastapi.FastAPI()

# 修改全局变量定义
loaded_models = {}

# 重写加载模型函数
def load_model(model_name: str):
    print("loading model: ", model_name)
    if model_name in loaded_models:
        return loaded_models[model_name]
    print("model not found, loading...")
    
    model_path = get_model_path(model_name)
    if not os.path.exists(model_path):
        raise HTTPException(status_code=404, detail="Model path not found")
    print("model_path ok: ", model_path)

    # 使用vLLM加载模型
    tp_size = 4
    model = LLM(
        model_path,
        trust_remote_code=True,
        gpu_memory_utilization=0.9,
        tensor_parallel_size=tp_size  # 张量并行
    )
    print(f"Model loaded from {model_path} using {tp_size} GPUs")

    loaded_models[model_name] = model
    return loaded_models[model_name]

# 修改API路由
@app.post("/predict/")
async def predict(request: ModelRequest):
    try:
        # 加载模型
        model = load_model(request.model_name)

        # 准备输入
        sampling_params = SamplingParams(
            temperature=0.7,
            max_tokens=1024,
            stop=None,
            seed=42
        )

        # print(f'last message: {request.messages[-1]["content"]}')

        # 构建提示词
        prompt = model.get_tokenizer().apply_chat_template(
            request.messages,
            tokenize=False,
            add_generation_prompt=True
        )

        # 使用vLLM生成回复
        outputs = model.generate(prompt, sampling_params)
        response_text = outputs[0].outputs[0].text.strip()

        # 计算token数量
        input_tokens = len(model.get_tokenizer().encode(prompt))
        output_tokens = len(model.get_tokenizer().encode(response_text))

        return {
            "choices": [{"message": {"content": response_text}}],
            "usage": {
                "completion_tokens": output_tokens,
                "prompt_tokens": input_tokens
            }
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 启动 FastAPI 服务器
if __name__ == "__main__":    
    import uvicorn
    # uvicorn.run(app, host="0.0.0.0", port=8000)
    uvicorn.run(app)
