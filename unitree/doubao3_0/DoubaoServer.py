from flask import Flask, request, jsonify, make_response, send_file

import os
import time
import matplotlib.pyplot as plt

from main.main import generate
app = Flask(__name__)

request_count = 0


# 假设音频文件存放在这个目录
AUDIO_DIR = "/home/unitree/douboa3_0/main/audio"

@app.route('/message', methods=['POST'])
async def process_data():
    global request_count
    data = request.json
    # 处理数据
    if data['input'] == 'are you ok':
        result = 'Connected'
    elif  data['input'] == 'are you running':
        request_count+=1
        result = f'Doubao Server Running'
    elif data['input'] == 'update':
        loginfo = await generate()
        print(f"更新结束：{loginfo}")
        result = 'Updated'
    else:
        result = {"processed": data["input"].upper()}
    return jsonify(result)


@app.route('/get_audio_data', methods=['GET'])
def get_audio_data():
    with open('./main/introduction.txt', 'r') as f:
        text_message = f.read()
    print("解说内容：",text_message)
    
    response = {
        "status": "success",
        "message": text_message
    }
    
    return jsonify(response)

@app.route('/download_audio', methods=['GET'])
def download_audio():
    return send_file("/home/unitree/doubao3_0/main/audio/audio.mp3", mimetype="audio/mpeg", as_attachment=False)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
    