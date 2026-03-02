from flask import Flask, request, jsonify, make_response, send_file

import os
import time
import matplotlib.pyplot as plt

from main.main import generate
app = Flask(__name__)

request_count = 0


# 假设音频文件存放在这个目录
AUDIO_DIR = "main/audio"

@app.route('/message', methods=['POST'])
async def process_data():
    global request_count
    data = request.json
    # 处理数据
    if data['input'] == 'are you ok':
        result = 'Im ok'
    elif  data['input'] == 'are you running':
        request_count+=1
        result = f'request for {request_count} times'
    elif data['input'] == 'update':
        loginfo = await generate()
        print(f"更新结束：{loginfo}")
        result = 'Infomation Updated'
    else:
        result = {"processed": data["input"].upper()}
    return jsonify(result)



@app.route('/get_audio_data', methods=['GET'])
def get_audio_data():
    # 1. 准备文本消息
    text_message = "这是来自Flask服务器的消息，下面是可播放的音频列表"
    
    # 2. 获取音频文件目录列表
    with open(f'{AUDIO_DIR}/audio_index.txt', 'r') as f:
        audio_files = f.readlines()
        audio_files = [f.strip() for f in audio_files]
    
    # 3. 准备第一个音频文件用于演示
    first_audio = audio_files[0] if audio_files else None
    audio_path = os.path.join(AUDIO_DIR, first_audio) if first_audio else None
    
    # 4. 构建响应
    response = {
        "status": "success",
        "message": text_message,
        "audio_files": audio_files,
        "current_audio": first_audio,
        "audio_url": f"/download_audio/{first_audio}" if first_audio else None
    }
    
    return jsonify(response)

@app.route('/download_audio/<filename>', methods=['GET'])
def download_audio(filename):
    # 确保文件名安全
    if not filename.endswith(('.mp3', '.wav', '.ogg')):
        return make_response(jsonify({"error": "Invalid file type"}), 400)
    
    audio_path = os.path.join(AUDIO_DIR, filename)
    if not os.path.exists(audio_path):
        return make_response(jsonify({"error": "File not found"}), 404)
    
    return send_file(audio_path, mimetype="audio/mpeg", as_attachment=False)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
    
