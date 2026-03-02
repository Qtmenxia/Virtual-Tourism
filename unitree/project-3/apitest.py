from openai import OpenAI

client = OpenAI(api_key="sk-7bbd9bd7ae0c46f58f7c5e9413c425ab", base_url="https://api.deepseek.com")

response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[
        {"role": "system", "content": "You are a helpful assistant"},
        {"role": "user", "content": "Hello"},
    ],
    stream=False
)

print(response.choices[0].message.content)