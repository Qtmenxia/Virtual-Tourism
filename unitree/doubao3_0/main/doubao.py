
import asyncio
from volcenginesdkarkruntime import Ark


from main.tts_websocket_demo import test_query
from main.TTSWebSocketDemo import gen_audio
# 从环境变量中读取您的方舟API Key
AK = "AKLTMGM4NjZmMTJjZWFiNDI0MmEyZTMzOTU2NjM2ZWQyMDg"
SK = "TmpoaE9UY3pNMlJsT0RCak5EZGtOemhtWmpKaU1EWTJNV0UwTlRRNU56WQ=="
API_KEY = "0403856c-d05b-48ef-9b4a-6661d775d796"


client = Ark(
    ak=AK,
    sk=SK,
    api_key = API_KEY,
)
async def get_msg(label:str):
    print("正在生成文本")
    label = label.split("_")[0]
    label2name = {
        "zhulou":"一校区主楼",
        "xiaobulou":"校部楼",
        "xingzhenglou":"行政楼",
        "hangtianguan":"科学园航天馆",
        "xiaobowuguan":"校部楼",
        "tushuguan":"一校区图书馆",
        "wozhencangqiong":"科学园卧震苍穹",
        
    }

    completion = client.chat.completions.create(
        # 替换 <Model>为 Model ID
        model="doubao-1-5-pro-32k-250115",
        messages=[{"role": "user", "content": f"请为我介绍哈尔滨工业大学的{label2name[label]}"}],
    )
    msg = completion.choices[0].message
    return msg.content

async def get_audio(msg,
              audio_path,
              k = 100):
    print("正在生成语音")
    audio_files = []
    loop = asyncio.get_event_loop()
    for i in range(0, len(msg), k):
        audio_file = f"/{audio_path}/audio_{i}.mp3"
        audio_files.append(audio_file)
        text = msg[i:i+k]
        await gen_audio(text, audio_file)
    with open(f'{audio_path}/audio_index.txt', 'w') as f:
        f.write('\n'.join(audio_files))
    return audio_files
        
        
if __name__ == "__main__":
    
    label = "zhulou_0"
    msg = get_msg(label)
    get_audio(msg, 'audio')
    
