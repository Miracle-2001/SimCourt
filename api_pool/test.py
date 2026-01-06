import os
base_url="https://svip.xty.app/v1",
api_key="sk-r0WeYOdkMjzYdnSxEcC8B931Aa904e4bBaCcAc2a57D803F1"
# # 设置环境变量
# os.putenv('BASE_URL', "https://svip.xty.app/v1")
# os.putenv('API_KEY', "sk-r0WeYOdkMjzYdnSxEcC8B931Aa904e4bBaCcAc2a57D803F1")
# 在某些系统上，可能需要这样做来更新 os.environ
os.environ['BASE_URL'] = "https://svip.xty.app/v1"
os.environ['API_KEY'] = "sk-r0WeYOdkMjzYdnSxEcC8B931Aa904e4bBaCcAc2a57D803F1"

# 现在环境变量已经设置
print(os.getenv('BASE_URL'))  # 输出: value
print(os.getenv('API_KEY'))