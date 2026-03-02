import asyncio
import os
import json
from pathlib import Path
from volcenginesdkarkruntime import Ark

from main.tts_websocket_demo import test_query
from main.TTSWebSocketDemo import gen_audio

from main.params import AUDIO_CACHE_DIR, OTHERS_AUDIO
# 从环境变量中读取您的方舟API Key
AK = "AKLTMGM4NjZmMTJjZWFiNDI0MmEyZTMzOTU2NjM2ZWQyMDg"
SK = "TmpoaE9UY3pNMlJsT0RCak5EZGtOemhtWmpKaU1EWTJNV0UwTlRRNU56WQ=="
API_KEY = "0403856c-d05b-48ef-9b4a-6661d775d796"

client = Ark(
    ak=AK,
    sk=SK,
    api_key=API_KEY,
)

# 创建缓存目录
os.makedirs(AUDIO_CACHE_DIR, exist_ok=True)

# 建筑名称映射
label2name = {
    "zhulou": "一校区主楼",
    "xiaobulou": "校部楼",
    "xingzhenglou": "一校区行政楼",
    "hangtianguan": "科学园航天馆",
    "xiaobowuguan": "校博物馆",
    "tushuguan": "一校区图书馆",
    "wozhencangqiong": "科学园卧震苍穹",
    "others": "未识别到目标"
}

async def get_msg(label: str):
    """获取解说文本，优先从缓存读取"""
    print("正在生成文本")
    label = label.split("_")[0]
    
    # 检查缓存
    cache_file = Path(AUDIO_CACHE_DIR) / f"{label}_text.json"
    if cache_file.exists():
        with open(cache_file, 'r', encoding='utf-8') as f:
            return json.load(f)['content']
    
    # 如果是others类别，返回预设文本
    if label == "others":
        return "未识别到目标建筑"
    
    # 从API获取文本
    completion = client.chat.completions.create(
        model="doubao-1-5-pro-32k-250115",
        messages=[{"role": "user", "content": f"请为我介绍哈尔滨工业大学的{label2name[label]}"}],
    )
    msg = completion.choices[0].message.content
    
    # 保存到缓存
    with open(cache_file, 'w', encoding='utf-8') as f:
        json.dump({"label": label, "content": msg}, f, ensure_ascii=False)
    
    return msg

async def get_audio(msg: str, label: str, chunk_size=100):
    """生成音频文件，优先使用缓存"""
    print("正在处理语音")
    
    # 如果是others类别，使用预设音频
    if label == "others":
        others_path = Path(AUDIO_CACHE_DIR) / OTHERS_AUDIO
        if not others_path.exists():
            await gen_audio("未识别到目标建筑", str(others_path))
        return [str(others_path)]
    
    # 创建分类目录
    label_dir = Path(AUDIO_CACHE_DIR) / label
    label_dir.mkdir(exist_ok=True)
    
    # 检查索引文件
    index_file = label_dir / "audio_index.txt"
    audio_files = []
    
    # 如果已有缓存，直接返回
    if index_file.exists():
        with open(index_file, 'r', encoding='utf-8') as f:
            cached_files = [line.strip() for line in f if line.strip()]
        
        # 验证所有音频文件都存在
        if all(Path(f).exists() for f in cached_files):
            return cached_files
    
    # 生成新的音频文件
    for i in range(0, len(msg), chunk_size):
        audio_file = label_dir / f"audio_{i}.mp3"
        text = msg[i:i+chunk_size]
        await gen_audio(text, str(audio_file))
        audio_files.append(str(audio_file))
    
    # 更新索引文件
    with open(index_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(audio_files))
    
    return audio_files

async def process_label(label: str):
    """处理标签的完整流程"""
    # 获取解说文本
    msg = await get_msg(label)
    
    # 获取音频文件
    base_label = label.split("_")[0]
    audio_files = await get_audio(msg, base_label)
    
    return audio_files

if __name__ == "__main__":
    # 测试用例
    test_labels = ["zhulou_0", "others_0"]
    
    async def main():
        for label in test_labels:
            print(f"\n处理标签: {label}")
            audio_files = await process_label(label)
            print(f"生成的音频文件: {audio_files}")
    
    asyncio.run(main())