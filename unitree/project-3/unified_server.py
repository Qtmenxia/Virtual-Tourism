"""
file: unified_server.py
运行环境: Unitree Go2 (IP: 192.168.123.18)
功能: 
1. UDP视频推流 -> Unity (7777)
2. 接收Unity头部数据 -> 控制狗头/身体 (6666)
3. 接收Unity摇杆数据 -> 控制移动 (5555)
4. 运行 PyTorch AI 导览逻辑 (非阻塞)
5. 处理 VR 客户端音频交互 (8000)
"""

import threading
import time
import socket
import json
import cv2
import struct
import numpy as np
from queue import Queue, Empty
import os

# 引入 PyTorch 版的 AI 模块
# 请确保 image_classification.py 和 resnet50_model.pth 在同一目录
import image_classification

# 如果你有这些模块请取消注释，否则将使用模拟数据
# import information_retrieval 
# import texttospeech 

# ========== 配置部分 (请根据实际情况修改) ==========
# 【重要】请修改为你的 VR 头显或运行 Unity 电脑的 IP 地址
UNITY_IP = "192.168.123.100" 
ROBOT_IP = "192.168.123.18"

# 端口定义 (需与 Unity 脚本对应)
PORTS = {
    "VIDEO_OUT": 7777,      # UDP: 发送视频到 Unity
    "HEAD_IN": 6666,        # UDP: 接收头部角度
    "MOVE_IN": 5555,        # TCP: 接收移动指令
    "AUDIO_RPC": 8000       # TCP: VRClient 交互
}

# 尝试导入 Unitree SDK2
try:
    from unitree_sdk2_python.unitree_sdk2py.core.channel import ChannelPublisher, ChannelFactory
    from unitree_sdk2_python.unitree_sdk2py.go2.sport.sport_client import SportClient
    SDK_AVAILABLE = True
    print("[系统] Unitree SDK2 已加载")
except ImportError:
    SDK_AVAILABLE = False
    print("[警告] 未找到 unitree_sdk2py，将运行在 SDK 模拟模式")

# ========== 全局状态管理 ==========
class RobotState:
    def __init__(self):
        self.frame = None           # 最新视频帧
        self.frame_lock = threading.Lock()
        self.is_running = True      # 全局运行标志
        
        # AI 状态
        self.last_audio_time = 0    # 上次播放语音的时间
        self.audio_cooldown = 15.0  # 语音冷却时间(秒)，防止连续触发
        self.current_spot = None    # 当前识别到的景点
        
        # 机器人状态
        self.sport_client = None    # SDK 客户端实例

state = RobotState()

# ========== 1. 视频流线程 (UDP JPEG 推流) ==========
def video_stream_thread():
    # 优先尝试本地设备 (延迟最低)
    cap = cv2.VideoCapture('/dev/video0') 
    if not cap.isOpened():
        cap = cv2.VideoCapture(0)
    
    # 如果本地失败，尝试 RTSP 回环
    if not cap.isOpened():
        print("[视频] 本地摄像头打开失败，尝试 RTSP...")
        cap = cv2.VideoCapture(f"rtsp://127.0.0.1:8554/live/0")

    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # 增大发送缓冲区
    udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65535 * 4)
    
    print(f"[视频] 开始推流到 {UNITY_IP}:{PORTS['VIDEO_OUT']}")
    
    frame_count = 0
    while state.is_running:
        ret, frame = cap.read()
        if not ret:
            time.sleep(0.1)
            continue
            
        # 1. 保存最新帧供 AI 线程使用
        with state.frame_lock:
            state.frame = frame.copy()
            
        # 2. 压缩并发送给 Unity
        try:
            # 缩放以降低带宽压力 (QVGA: 320x240, VGA: 640x480)
            # 建议先用 640x480，如果卡顿则降级
            resized = cv2.resize(frame, (640, 480))
            
            # JPEG 压缩，质量 70
            _, buffer = cv2.imencode('.jpg', resized, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
            data = buffer.tobytes()
            
            # UDP 包大小限制检查 (65507 bytes max)
            if len(data) < 65000:
                udp_socket.sendto(data, (UNITY_IP, PORTS['VIDEO_OUT']))
            else:
                # 如果单帧过大，可以降低质量重试，或者简单的丢弃
                print(f"[视频] 帧过大 ({len(data)} bytes)，已丢弃")
                
        except Exception as e:
            # 网络错误不打印太多日志，以免刷屏
            if frame_count % 100 == 0:
                print(f"[视频异常] {e}")
        
        frame_count += 1
        time.sleep(0.033) # 限制在 ~30 FPS

    cap.release()
    udp_socket.close()

# ========== 2. 运动控制线程 (TCP 5555) ==========
def movement_control_thread():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(('0.0.0.0', PORTS['MOVE_IN']))
    server.listen(1)
    
    print(f"[控制] 移动服务监听 TCP {PORTS['MOVE_IN']}")
    
    while state.is_running:
        try:
            conn, addr = server.accept()
            # print(f"[控制] 移动控制器已连接: {addr}")
            
            with conn:
                conn.settimeout(2.0)
                while state.is_running:
                    try:
                        data = conn.recv(1024)
                        if not data: break
                        
                        # 解析 Unity 发送的 JSON
                        # 格式: {"move": {"x": 0.5, "y": 0.0, "z": 0.0}}
                        # z 在 Unity 脚本中被映射为转向 (Turning)
                        msg = data.decode('utf-8').strip()
                        # 处理粘包 (简单的按行分割)
                        lines = msg.split('\n')
                        
                        for line in lines:
                            if not line: continue
                            if '{' in line:
                                obj = json.loads(line)
                                if 'move' in obj:
                                    m = obj['move']
                                    vx = float(m.get('x', 0)) # 前后
                                    vy = float(m.get('y', 0)) # 左右
                                    vyaw = float(m.get('z', 0)) # 转向 (Unity将x轴映射到了这里的z)
                                    
                                    # 调用 SDK 控制机器人
                                    if state.sport_client:
                                        # Go2 SDK 参数: (vx, vy, vyaw)
                                        state.sport_client.Move(vx, vy, vyaw)
                                    else:
                                        # print(f"模拟移动: X={vx:.2f} Y={vy:.2f} Yaw={vyaw:.2f}")
                                        pass
                                        
                    except socket.timeout:
                        continue
                    except json.JSONDecodeError:
                        pass
                    except Exception as e:
                        print(f"[移动异常] {e}")
                        break
        except Exception as e:
            if state.is_running:
                print(f"[移动服务重置] {e}")
                time.sleep(1)

# ========== 3. 头部/云台控制线程 (UDP 6666) ==========
def head_control_thread():
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.bind(('0.0.0.0', PORTS['HEAD_IN']))
    
    print(f"[控制] 头部服务监听 UDP {PORTS['HEAD_IN']}")
    
    while state.is_running:
        try:
            # 接收 Unity CameraSocket.cs 发送的数据包
            data, _ = udp_socket.recvfrom(1024)
            
            # 简单的协议校验 (Header 8 bytes + 4 bytes payload + 2 bytes CRC)
            if len(data) >= 14:
                # Unity logic: 
                # short yaw = (short)(Mathf.Clamp(euler.y, ...) * 10);
                # short pitch = (short)(Mathf.Clamp(euler.x, ...) * 10);
                # Buffer structure: [Header 8] [Yaw 2] [Pitch 2] [CRC 2]
                
                yaw_short = struct.unpack('<h', data[8:10])[0]
                pitch_short = struct.unpack('<h', data[10:12])[0]
                
                yaw_deg = yaw_short / 10.0
                pitch_deg = pitch_short / 10.0
                
                # 调用 SDK 控制姿态
                # 注意: Go2 的 Euler API 通常控制的是身体姿态 (Roll, Pitch, Yaw)
                # 真正的头部控制需要查看具体机器人的关节定义
                if state.sport_client:
                    # 映射: Head Pitch -> Body Pitch, Head Yaw -> Body Yaw
                    # 注意角度转弧度: deg * pi / 180
                    # state.sport_client.Euler(0, pitch_deg * 0.01745, yaw_deg * 0.01745)
                    pass
                else:
                    # print(f"头部姿态: Pitch={pitch_deg:.1f}, Yaw={yaw_deg:.1f}")
                    pass
                    
        except Exception as e:
            print(f"[头部异常] {e}")

# ========== 4. AI 导览逻辑 (主循环) ==========
def ai_logic_thread(msg_queue):
    print("[AI] PyTorch 导览系统启动")
    
    # 预先加载模型 (在 import image_classification 时已加载，但此处可做检查)
    
    while state.is_running:
        try:
            current_time = time.time()
            
            # 1. 冷却检查
            if current_time - state.last_audio_time < state.audio_cooldown:
                time.sleep(1)
                continue
                
            # 2. 获取图像快照
            img_to_process = None
            with state.frame_lock:
                if state.frame is not None:
                    img_to_process = state.frame.copy()
            
            if img_to_process is None:
                time.sleep(1)
                continue
                
            # 3. AI 识别 (使用 PyTorch)
            # 这里的 predict_cv2_image 是上一轮对话中新增的接口
            label_pinyin, confidence = image_classification.predict_cv2_image(img_to_process)
            spot_name = image_classification.pinyin_to_name(label_pinyin)
            
            # 4. 结果判断
            if confidence > 0.75 and spot_name != "未知景点":
                print(f"[AI] 识别成功: {spot_name} (置信度: {confidence:.2f})")
                
                # 生成语音文件路径 (模拟或实际生成)
                # 实际场景：调用 texttospeech.py 生成 mp3
                audio_filename = f"{label_pinyin}.mp3"
                audio_full_path = f"/home/unitree/audio_cache/{audio_filename}"
                
                # 如果没有真实TTS，确保有一个测试文件存在，否则Unity下载会失败
                if not os.path.exists(os.path.dirname(audio_full_path)):
                    os.makedirs(os.path.dirname(audio_full_path), exist_ok=True)
                
                # 模拟创建一个空文件用于测试 (如果文件不存在)
                if not os.path.exists(audio_full_path):
                    with open(audio_full_path, 'wb') as f:
                        f.write(b'FAKE MP3 DATA FOR TESTING') 
                
                # 5. 向 Unity 发送指令
                # 协议参考 VRClient.cs: HandleServerResponse
                message = {
                    "status": "success",
                    "action": "play_audio",
                    "message": f"为您介绍: {spot_name}",
                    "file_path": audio_full_path 
                }
                
                msg_queue.put(json.dumps(message))
                
                # 进入冷却
                state.last_audio_time = time.time()
                print(f"[AI] 指令已发送，进入冷却 ({state.audio_cooldown}s)")
                
            else:
                # 未识别到，快速重试
                pass
                
        except Exception as e:
            print(f"[AI异常] {e}")
            
        time.sleep(2.0) # 每次识别间隔 2秒

# ========== 5. VR 音频交互服务 (TCP 8000) ==========
def audio_server_thread(msg_queue):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(('0.0.0.0', PORTS['AUDIO_RPC']))
    server.listen(1)
    
    print(f"[交互] VR交互服务监听 TCP {PORTS['AUDIO_RPC']}")
    
    while state.is_running:
        try:
            conn, addr = server.accept()
            print(f"[交互] VR客户端连接成功: {addr}")
            
            with conn:
                conn.settimeout(0.1) # 非阻塞模式以便发送消息
                
                while state.is_running:
                    # A. 尝试接收 Unity 请求 (例如下载文件)
                    try:
                        data = conn.recv(4096)
                        if not data: break
                        
                        request = data.decode('utf-8', errors='ignore').strip()
                        
                        # 处理 VRClient.cs 的文件下载请求
                        # 逻辑: VRClient 发送纯文件路径 -> Server 返回 (4字节长度 + 内容)
                        if "/" in request or "\\" in request or ".mp3" in request:
                            filepath = request
                            if os.path.exists(filepath):
                                size = os.path.getsize(filepath)
                                print(f"[文件] 发送音频: {os.path.basename(filepath)} ({size} bytes)")
                                
                                # 发送 4字节大小 (Little Endian)
                                conn.send(struct.pack('<I', size))
                                # 发送文件内容
                                with open(filepath, 'rb') as f:
                                    while True:
                                        chunk = f.read(4096)
                                        if not chunk: break
                                        conn.send(chunk)
                            else:
                                print(f"[文件] 请求的文件不存在: {filepath}")
                                conn.send(struct.pack('<I', 0)) # 发送0大小表示失败
                        elif request == "START":
                            print("[指令] 用户开启导览")
                        elif request == "STOP":
                            print("[指令] 用户停止导览")
                            
                    except socket.timeout:
                        pass
                    except Exception as e:
                        print(f"[交互错误] 接收失败: {e}")
                        break
                    
                    # B. 检查是否有 AI 产生的消息需要推送给 Unity
                    try:
                        while not msg_queue.empty():
                            msg_str = msg_queue.get_nowait()
                            # Unity 按换行符分割消息
                            packet = (msg_str + "\n").encode('utf-8')
                            conn.sendall(packet)
                            print(f"[交互] 推送消息: {msg_str[:50]}...")
                    except Exception as e:
                        print(f"[交互错误] 发送失败: {e}")
                        # 发送失败通常意味着连接断开
                        break
                        
        except Exception as e:
            print(f"[交互服务重置] {e}")
            time.sleep(1)

# ========== 主程序入口 ==========
if __name__ == "__main__":
    # 1. 初始化 SDK (如果可用)
    if SDK_AVAILABLE:
        try:
            channel = ChannelFactory().create()
            state.sport_client = SportClient(channel)
            time.sleep(1) # 等待连接
            print("[系统] SDK 连接成功")
        except Exception as e:
            print(f"[错误] SDK 初始化失败: {e}")

    # 2. 创建消息队列
    vr_msg_queue = Queue()
    
    # 3. 启动所有线程
    threads = [
        threading.Thread(target=video_stream_thread, name="Video"),
        threading.Thread(target=movement_control_thread, name="Move"),
        threading.Thread(target=head_control_thread, name="Head"),
        threading.Thread(target=audio_server_thread, args=(vr_msg_queue,), name="Audio"),
        threading.Thread(target=ai_logic_thread, args=(vr_msg_queue,), name="AI")
    ]
    
    for t in threads:
        t.daemon = True # 设置为守护线程，主程序退出时自动结束
        t.start()
        
    print(f"\n=== Unitree Go2 智能导览服务已启动 ===")
    print(f"IP: {ROBOT_IP}")
    print(f"正在等待 Unity ({UNITY_IP}) 连接...\n")

    # 4. 主线程保活
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[系统] 正在停止服务...")
        state.is_running = False
