import os
from openai import OpenAI

def test_official_key(api_key):
    # 初始化客户端，指向 Minimax 官方的兼容接口
    client = OpenAI(
        api_key=api_key,
        base_url="https://api.minimax.io/v1",
    )
    try:
        # 发送一个简单的对话请求
        completion = client.chat.completions.create(
            model="MiniMax-M2.1", # 使用一个可用的模型
            messages=[{"role": "user", "content": "你好，请用一句话介绍你自己。"}],
            stream=False, # 关闭流式输出
        )
        # 打印模型的回复
        print("✅ API Key 有效！模型回复：")
        print(completion.choices[0].message.content)
        return True
    except Exception as e:
        # 捕获并打印任何错误信息
        print("❌ API Key 无效或调用失败。错误信息：")
        print(e)
        return False

if __name__ == "__main__":
    # 在此处填入你的 API Key
    my_api_key = "sk-cp-O1jG1f6LrLj-Kvj5K1QlG4lg6Z7S69cmvDl2ytvZ-eJuCw4HhIW5FKyvSAWmvIXzF-QwnQCRToz7HwBtxugf3pomyOLakXs0bOlhS3Q35fQef6knJV7ARWc"
    test_official_key(my_api_key)