from openai import OpenAI

client = OpenAI(
    api_key="api_key",
    base_url="https://api.deepseek.com"  # 确保使用正确的base_url
)

# 列出可用模型
models = client.models.list()
for model in models.data:
    print(model.id)