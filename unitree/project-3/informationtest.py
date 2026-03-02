from openai import OpenAI

def get_introduction_text(predicted_spot_name, api_key):
    client = OpenAI(api_key="sk-7bbd9bd7ae0c46f58f7c5e9413c425ab", base_url="https://api.deepseek.com")

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "You are a helpful assistant"},
            {"role": "user", "content":f"请介绍哈尔滨工业大学{predicted_spot_name}这个校园景点，包括它的历史背景、重要事件、建筑特点、文化内涵、周边景点及推荐游览时长。字数控制在300字左右"}
        ],
        stream=False
    )
    return response.choices[0].message.content