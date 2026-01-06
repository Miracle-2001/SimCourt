# uvicorn local_model_api:app --reload
# uvicorn local_model_api_vllm:app --reload
CUDA_VISIBLE_DEVICES=0,1,2,3 uvicorn local_model_api_vllm:app --reload --host='127.0.0.1' --port=8002