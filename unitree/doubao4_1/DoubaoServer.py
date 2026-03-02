from flask import Flask, request, jsonify, make_response, send_file
import os
import time
import json
from pathlib import Path

from main.main import generate
from main.params import AUDIO_DIR, OTHERS_AUDIO
app = Flask(__name__)

request_count = 0



@app.route('/message', methods=['POST'])
async def process_data():
    global request_count
    data = request.json
    # 处理数据
    if data['input'] == 'are you ok':
        result = 'Connected'
    elif data['input'] == 'are you running':
        request_count += 1
        result = f'Doubao Server Running (请求计数: {request_count})'
    elif data['input'] == 'update':
        loginfo = await generate()
        print(f"更新结束：{loginfo}")
        result = 'Updated'
    else:
        result = {"processed": data["input"].upper()}
    return jsonify(result)

@app.route('/get_audio_data', methods=['GET'])
def get_audio_data():
    # 从查询参数获取标签
    label = request.args.get('label', 'others_0')
    base_label = label.split('_')[0]
    
    # 检查是否为others分类
    if base_label == "others":
        response = {
            "status": "fail",
            "message": "未识别到目标建筑",
            "label": label
        }
        return jsonify(response)
    
    # 尝试读取对应标签的文本介绍
    text_file = os.path.join(Path(AUDIO_DIR) , f"{base_label}_text.json")
    
    if not os.path.exists(text_file):
        response = {
            "status": "fail",
            "message": "未找到该建筑的介绍文本",
            "label": label
        }
    else:
        with open(text_file, 'r', encoding='utf-8') as f:
            text_data = json.load(f)
        
        response = {
            "status": "success",
            "message": text_data['content'],
            "label": label
        }
    
    print(f"返回解说内容：{response}")
    return jsonify(response)

@app.route('/download_audio', methods=['GET'])
def download_audio():
    # 从查询参数获取标签和文件名
    label = request.args.get('label', 'others')
    filename = request.args.get('filename', OTHERS_AUDIO)
    
    # 构建文件路径
    if label == "others":
        audio_path = Path(AUDIO_DIR) / filename
    else:
        audio_path = Path(AUDIO_DIR) / label / filename
    
    # 检查文件是否存在
    if not audio_path.exists():
        return jsonify({
            "status": "error",
            "message": "音频文件不存在",
            "path": str(audio_path)
        }), 404
    
    # 发送音频文件
    return send_file(
        str(audio_path),
        mimetype="audio/mpeg",
        as_attachment=False,
        download_name=f"{label}_{filename}"
    )

if __name__ == '__main__':
    # 确保音频目录存在
    os.makedirs(AUDIO_DIR, exist_ok=True)
    app.run(host='0.0.0.0', port=5000, debug=False)
