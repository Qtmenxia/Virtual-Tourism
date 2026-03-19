# -*- coding: utf-8 -*-
"""
unified_server.py
第一阶段目标：
1. RTSP 拉流
2. UDP JPEG 推流到 Unity
3. TCP 接收移动控制
4. UDP 接收头显姿态
5. TCP 与 VRClient 交互
6. AI 识别线程可运行，但失败不拖垮主程序

当前配置：
- Go2 教育版
- Quest3
- 外接摄像头：思翼 A8mini（当前仅使用 RTSP 视频，不控制云台）
"""

import os
import cv2
import time
import json
import socket
import struct
import threading
import traceback
from queue import Queue, Empty

import image_classification

# 可选模块：不存在也不影响第一阶段启动
try:
    import information_retrieval
    INFO_AVAILABLE = True
except Exception:
    information_retrieval = None
    INFO_AVAILABLE = False

try:
    import texttospeech
    TTS_AVAILABLE = True
except Exception:
    texttospeech = None
    TTS_AVAILABLE = False

try:
    from gimbal_control import SiyiGimbalController
    GIMBAL_AVAILABLE = True
except Exception:
    SiyiGimbalController = None
    GIMBAL_AVAILABLE = False


# =========================
# 配置区
# =========================
CONFIG = {
    "ROBOT_IP": "0.0.0.0",                 # 服务监听全部网卡
    "UNITY_IP": "10.68.194.40",            # 先按你提供的 Quest IP 处理
    "RTSP_URL": "rtsp://192.168.144.25:8554/main.264",

    "PORT_VIDEO_OUT": 7777,                # Python -> Unity (UDP JPEG)
    "PORT_HEAD_IN": 6666,                  # Unity -> Python (UDP 头显姿态)
    "PORT_MOVE_IN": 5555,                  # Unity -> Python (TCP 摇杆控制)
    "PORT_AUDIO_RPC": 8000,                # Unity VRClient -> Python

    "VIDEO_WIDTH": 640,
    "VIDEO_HEIGHT": 480,
    "JPEG_QUALITY": 65,
    "VIDEO_FPS_LIMIT": 20,

    "AI_ENABLED": True,
    "AI_MIN_CONFIDENCE": 0.78,
    "AI_INTERVAL_SEC": 2.0,
    "AI_AUDIO_COOLDOWN_SEC": 15.0,

    "AUDIO_CACHE_DIR": "./audio_cache",
    "USE_FAKE_TTS": True,                  # 第一阶段先开着，保证链路可跑
    "PRINT_HEAD_DATA": True,               # 第一阶段只验证头显数据是否到达
    "PRINT_MOVE_DATA": False,

    # ===== 云台控制 =====
    "GIMBAL_ENABLED": True,                # 是否启用头显→云台联动
    "GIMBAL_CAMERA_IP": "192.168.144.25",  # A8mini IP
    "GIMBAL_CAMERA_PORT": 37260,           # A8mini UDP 控制端口
    "GIMBAL_YAW_LIMIT": (-135.0, 135.0),   # Yaw 限幅 (度)
    "GIMBAL_PITCH_LIMIT": (-90.0, 25.0),   # Pitch 限幅 (度)
    "GIMBAL_SMOOTH_ALPHA": 0.35,           # EMA 平滑系数 (0~1, 越大响应越快)
    "GIMBAL_DEAD_ZONE": 1.5,              # 死区角度 (度, 小于此变化量不发送)
    "GIMBAL_MAX_HZ": 15.0,                # 最大发送频率
    "GIMBAL_YAW_OFFSET": 0.0,             # Yaw 偏移校正 (度)
    "GIMBAL_PITCH_OFFSET": 0.0,           # Pitch 偏移校正 (度)
    "GIMBAL_YAW_SCALE": 1.0,              # Yaw 缩放系数 (用于调节灵敏度)
    "GIMBAL_PITCH_SCALE": 1.0,            # Pitch 缩放系数
}

# 为了便于排查，统一输出前缀
def log(tag, msg):
    print(f"[{tag}] {msg}", flush=True)


# =========================
# Unitree SDK
# =========================
SDK_AVAILABLE = False
SportClient = None
ChannelFactory = None

try:
    from unitree_sdk2_python.unitree_sdk2py.core.channel import ChannelFactory
    from unitree_sdk2_python.unitree_sdk2py.go2.sport.sport_client import SportClient
    SDK_AVAILABLE = True
    log("系统", "Unitree SDK2 已加载")
except Exception as e:
    log("警告", f"未找到 unitree_sdk2py，将以模拟模式运行: {e}")


# =========================
# 全局状态
# =========================
class RobotState:
    def __init__(self):
        self.is_running = True

        self.frame = None
        self.frame_lock = threading.Lock()

        self.current_spot = None
        self.last_audio_time = 0.0

        self.sport_client = None
        self.gimbal_controller = None  # SiyiGimbalController 实例

        self.last_rtsp_ok_time = 0.0
        self.last_video_send_ok_time = 0.0
        self.last_move_cmd_time = 0.0
        self.last_head_packet_time = 0.0
        self.last_gimbal_cmd_time = 0.0
        self.gimbal_cmd_count = 0

state = RobotState()


# =========================
# 工具函数
# =========================
def ensure_dir(path: str):
    if path and not os.path.exists(path):
        os.makedirs(path, exist_ok=True)

def safe_json_loads(text: str):
    try:
        return json.loads(text)
    except Exception:
        return None

def make_silent_placeholder_mp3(filepath: str):
    """
    第一阶段占位：仅保证 VRClient 文件下载链路可通。
    注意：这不是合法 MP3，仅用于验证“文件请求-返回字节流”流程。
    真正联调音频播放时要换成真实 mp3。
    """
    ensure_dir(os.path.dirname(filepath))
    if not os.path.exists(filepath):
        with open(filepath, "wb") as f:
            f.write(b"ID3\x03\x00\x00\x00\x00\x00\x00")


def generate_or_get_audio_file(spot_name: str, label_pinyin: str) -> str:
    """
    第一阶段策略：
    - 优先查缓存
    - 否则占位生成
    """
    ensure_dir(CONFIG["AUDIO_CACHE_DIR"])
    filename = f"{label_pinyin}.mp3"
    filepath = os.path.join(CONFIG["AUDIO_CACHE_DIR"], filename)

    if os.path.exists(filepath):
        return filepath

    # 第一阶段不强依赖 TTS
    if CONFIG["USE_FAKE_TTS"]:
        make_silent_placeholder_mp3(filepath)
        return filepath

    # 后续阶段可接真实 TTS
    # 这里保留接口，不在本轮强行启用
    make_silent_placeholder_mp3(filepath)
    return filepath


# =========================
# 1) RTSP 拉流 + UDP JPEG 推流
# =========================
def open_rtsp_capture(rtsp_url: str):
    """
    优先使用 FFMPEG 后端，失败则退回默认方式。
    """
    log("视频", f"尝试打开 RTSP: {rtsp_url}")
    cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
    if cap.isOpened():
        return cap

    cap = cv2.VideoCapture(rtsp_url)
    return cap


def video_stream_thread():
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65535 * 4)

    target = (CONFIG["UNITY_IP"], CONFIG["PORT_VIDEO_OUT"])
    log("视频", f"目标推流地址: {target[0]}:{target[1]}")

    cap = None
    last_open_try = 0.0
    frame_interval = 1.0 / max(CONFIG["VIDEO_FPS_LIMIT"], 1)

    while state.is_running:
        try:
            now = time.time()

            # 断线重连
            if cap is None or not cap.isOpened():
                if now - last_open_try < 2.0:
                    time.sleep(0.2)
                    continue
                last_open_try = now

                if cap is not None:
                    try:
                        cap.release()
                    except Exception:
                        pass

                cap = open_rtsp_capture(CONFIG["RTSP_URL"])
                if not cap.isOpened():
                    log("视频", "RTSP 打开失败，2秒后重试")
                    time.sleep(2.0)
                    continue

                # 尝试减小缓存
                try:
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                except Exception:
                    pass

                log("视频", "RTSP 已连接")

            ret, frame = cap.read()
            if not ret or frame is None:
                log("视频", "读取 RTSP 帧失败，准备重连")
                try:
                    cap.release()
                except Exception:
                    pass
                cap = None
                time.sleep(0.5)
                continue

            state.last_rtsp_ok_time = time.time()

            with state.frame_lock:
                state.frame = frame.copy()

            resized = cv2.resize(
                frame,
                (CONFIG["VIDEO_WIDTH"], CONFIG["VIDEO_HEIGHT"])
            )

            ok, buffer = cv2.imencode(
                ".jpg",
                resized,
                [int(cv2.IMWRITE_JPEG_QUALITY), int(CONFIG["JPEG_QUALITY"])]
            )
            if not ok:
                time.sleep(frame_interval)
                continue

            data = buffer.tobytes()
            if len(data) >= 65000:
                log("视频", f"JPEG 包过大({len(data)} bytes)，请继续降分辨率或质量")
                time.sleep(frame_interval)
                continue

            udp_socket.sendto(data, target)
            state.last_video_send_ok_time = time.time()

            time.sleep(frame_interval)

        except Exception as e:
            log("视频异常", f"{e}")
            traceback.print_exc()
            time.sleep(1.0)

    try:
        if cap is not None:
            cap.release()
    except Exception:
        pass
    udp_socket.close()


# =========================
# 2) 移动控制
# =========================
def handle_move_command(obj):
    if not isinstance(obj, dict):
        return

    move = obj.get("move")
    if not isinstance(move, dict):
        return

    vx = float(move.get("x", 0.0))
    vy = float(move.get("y", 0.0))
    vyaw = float(move.get("z", 0.0))

    # 简单限幅，避免 Unity 误发超大值
    vx = max(min(vx, 1.0), -1.0)
    vy = max(min(vy, 1.0), -1.0)
    vyaw = max(min(vyaw, 1.0), -1.0)

    state.last_move_cmd_time = time.time()

    if CONFIG["PRINT_MOVE_DATA"]:
        log("移动", f"vx={vx:.3f}, vy={vy:.3f}, vyaw={vyaw:.3f}")

    if state.sport_client is not None:
        try:
            state.sport_client.Move(vx, vy, vyaw)
        except Exception as e:
            log("移动SDK异常", f"{e}")
    else:
        # 模拟模式
        pass


def movement_control_thread():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((CONFIG["ROBOT_IP"], CONFIG["PORT_MOVE_IN"]))
    server.listen(2)
    log("控制", f"移动服务监听 TCP {CONFIG['PORT_MOVE_IN']}")

    while state.is_running:
        try:
            conn, addr = server.accept()
            log("控制", f"移动连接接入: {addr}")
            with conn:
                conn.settimeout(1.0)
                recv_buf = ""

                while state.is_running:
                    try:
                        data = conn.recv(2048)
                        if not data:
                            break

                        recv_buf += data.decode("utf-8", errors="ignore")

                        # 按换行切包
                        while "\n" in recv_buf:
                            line, recv_buf = recv_buf.split("\n", 1)
                            line = line.strip()
                            if not line:
                                continue

                            obj = safe_json_loads(line)
                            if obj is not None:
                                handle_move_command(obj)

                    except socket.timeout:
                        continue
                    except Exception as e:
                        log("移动异常", f"{e}")
                        break

        except Exception as e:
            if state.is_running:
                log("移动服务重置", f"{e}")
                time.sleep(1.0)

    server.close()


# =========================
# 3) 头显姿态接收 + 云台控制
# =========================
def head_control_thread():
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.bind((CONFIG["ROBOT_IP"], CONFIG["PORT_HEAD_IN"]))
    log("控制", f"头部服务监听 UDP {CONFIG['PORT_HEAD_IN']}")

    # 初始化云台控制器
    gimbal = state.gimbal_controller  # 在 main 中已创建

    while state.is_running:
        try:
            data, addr = udp_socket.recvfrom(1024)
            if len(data) < 14:
                continue

            # 解析 Siyi 协议格式的数据包
            # 头部: 55 66 01 04 00 00 00 0E [yaw_s16_le] [pitch_s16_le] [crc16_le]
            yaw_short = struct.unpack("<h", data[8:10])[0]
            pitch_short = struct.unpack("<h", data[10:12])[0]

            yaw_deg = yaw_short / 10.0
            pitch_deg = pitch_short / 10.0

            state.last_head_packet_time = time.time()

            if CONFIG["PRINT_HEAD_DATA"]:
                log("头显", f"来自 {addr} | pitch={pitch_deg:.1f}, yaw={yaw_deg:.1f}")

            # ===== 云台联动 =====
            if CONFIG["GIMBAL_ENABLED"] and gimbal is not None and gimbal.is_connected:
                # 应用缩放和偏移
                mapped_yaw = yaw_deg * CONFIG["GIMBAL_YAW_SCALE"] + CONFIG["GIMBAL_YAW_OFFSET"]
                mapped_pitch = pitch_deg * CONFIG["GIMBAL_PITCH_SCALE"] + CONFIG["GIMBAL_PITCH_OFFSET"]

                sent = gimbal.set_angle(mapped_yaw, mapped_pitch, use_smooth=True)

                if sent:
                    state.last_gimbal_cmd_time = time.time()
                    state.gimbal_cmd_count += 1

        except Exception as e:
            log("头部异常", f"{e}")
            time.sleep(0.1)

    udp_socket.close()


# =========================
# 4) AI 识别线程
# =========================
def ai_logic_thread(msg_queue: Queue):
    if not CONFIG["AI_ENABLED"]:
        log("AI", "AI 已关闭")
        return

    log("AI", "识别线程已启动")

    while state.is_running:
        try:
            now = time.time()
            if now - state.last_audio_time < CONFIG["AI_AUDIO_COOLDOWN_SEC"]:
                time.sleep(0.5)
                continue

            with state.frame_lock:
                frame = None if state.frame is None else state.frame.copy()

            if frame is None:
                time.sleep(0.5)
                continue

            label_pinyin, confidence = image_classification.predict_cv2_image(frame)
            spot_name = image_classification.pinyin_to_name(label_pinyin)

            if confidence >= CONFIG["AI_MIN_CONFIDENCE"] and spot_name != "未知景点":
                # 避免对同一景点连续轰炸
                if state.current_spot == spot_name:
                    time.sleep(CONFIG["AI_INTERVAL_SEC"])
                    continue

                state.current_spot = spot_name
                log("AI", f"识别成功: {spot_name} ({label_pinyin}, conf={confidence:.3f})")

                audio_path = generate_or_get_audio_file(spot_name, label_pinyin)

                message = {
                    "status": "success",
                    "action": "play_audio",
                    "message": f"为您介绍: {spot_name}",
                    "file_path": audio_path
                }
                msg_queue.put(json.dumps(message, ensure_ascii=False))
                state.last_audio_time = time.time()

            time.sleep(CONFIG["AI_INTERVAL_SEC"])

        except Exception as e:
            log("AI异常", f"{e}")
            traceback.print_exc()
            time.sleep(1.0)


# =========================
# 5) VR 音频/消息服务
# =========================
def send_file_with_size_prefix(conn, filepath: str):
    if not os.path.exists(filepath):
        conn.send(struct.pack("<I", 0))
        return

    size = os.path.getsize(filepath)
    conn.send(struct.pack("<I", size))
    with open(filepath, "rb") as f:
        while True:
            chunk = f.read(4096)
            if not chunk:
                break
            conn.sendall(chunk)


def audio_server_thread(msg_queue: Queue):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((CONFIG["ROBOT_IP"], CONFIG["PORT_AUDIO_RPC"]))
    server.listen(2)

    log("交互", f"VR 交互服务监听 TCP {CONFIG['PORT_AUDIO_RPC']}")

    while state.is_running:
        try:
            conn, addr = server.accept()
            log("交互", f"VR 客户端连接成功: {addr}")

            with conn:
                conn.settimeout(0.1)
                recv_buf = ""

                while state.is_running:
                    # 先收
                    try:
                        data = conn.recv(4096)
                        if data:
                            recv_buf += data.decode("utf-8", errors="ignore")
                            # VRClient 当前发送的 START/STOP/STATUS 不带换行，
                            # 这里做简单兼容处理
                            request = recv_buf.strip()
                            recv_buf = ""

                            if request:
                                if ("/" in request) or ("\\" in request) or request.endswith(".mp3"):
                                    log("文件", f"请求下载: {request}")
                                    send_file_with_size_prefix(conn, request)
                                elif request == "START":
                                    log("指令", "用户开启导览")
                                elif request == "STOP":
                                    log("指令", "用户停止导览")
                                elif request == "STATUS":
                                    status_msg = {
                                        "status": "success",
                                        "action": "status",
                                        "message": "server_alive"
                                    }
                                    conn.sendall((json.dumps(status_msg, ensure_ascii=False) + "\n").encode("utf-8"))
                        else:
                            break

                    except socket.timeout:
                        pass
                    except Exception as e:
                        log("交互接收异常", f"{e}")
                        break

                    # 再推送 AI 消息
                    try:
                        while True:
                            msg_str = msg_queue.get_nowait()
                            conn.sendall((msg_str + "\n").encode("utf-8"))
                            log("交互", f"推送消息: {msg_str}")
                    except Empty:
                        pass
                    except Exception as e:
                        log("交互发送异常", f"{e}")
                        break

        except Exception as e:
            if state.is_running:
                log("交互服务重置", f"{e}")
                time.sleep(1.0)

    server.close()


# =========================
# 6) 状态监控线程
# =========================
def monitor_thread():
    while state.is_running:
        try:
            now = time.time()

            rtsp_alive = (now - state.last_rtsp_ok_time) < 5.0
            video_alive = (now - state.last_video_send_ok_time) < 5.0
            move_alive = (now - state.last_move_cmd_time) < 5.0
            head_alive = (now - state.last_head_packet_time) < 5.0
            gimbal_alive = (now - state.last_gimbal_cmd_time) < 5.0

            gimbal_status = "OFF"
            if CONFIG["GIMBAL_ENABLED"]:
                if state.gimbal_controller and state.gimbal_controller.is_connected:
                    gimbal_status = "OK" if gimbal_alive else "IDLE"
                else:
                    gimbal_status = "DISCONN"

            log(
                "状态",
                f"rtsp={'OK' if rtsp_alive else '----'} | "
                f"video={'OK' if video_alive else '----'} | "
                f"move={'OK' if move_alive else '----'} | "
                f"head={'OK' if head_alive else '----'} | "
                f"gimbal={gimbal_status}(sent={state.gimbal_cmd_count}) | "
                f"spot={state.current_spot}"
            )

            time.sleep(5.0)
        except Exception as e:
            log("监控异常", f"{e}")
            time.sleep(2.0)


# =========================
# 主程序
# =========================
def init_sdk():
    if not SDK_AVAILABLE:
        log("系统", "SDK 模拟模式运行")
        return

    try:
        channel = ChannelFactory().create()
        state.sport_client = SportClient(channel)
        time.sleep(1.0)
        log("系统", "SDK 初始化成功，运动控制可用")
    except Exception as e:
        state.sport_client = None
        log("错误", f"SDK 初始化失败，转为模拟模式: {e}")


def init_gimbal():
    """初始化云台控制器。"""
    if not CONFIG["GIMBAL_ENABLED"]:
        log("云台", "云台控制已关闭 (GIMBAL_ENABLED=False)")
        return

    if not GIMBAL_AVAILABLE:
        log("云台", "gimbal_control 模块未找到，云台控制不可用")
        return

    try:
        controller = SiyiGimbalController(
            camera_ip=CONFIG["GIMBAL_CAMERA_IP"],
            camera_port=CONFIG["GIMBAL_CAMERA_PORT"],
            yaw_limit=CONFIG["GIMBAL_YAW_LIMIT"],
            pitch_limit=CONFIG["GIMBAL_PITCH_LIMIT"],
            smooth_alpha=CONFIG["GIMBAL_SMOOTH_ALPHA"],
            dead_zone_deg=CONFIG["GIMBAL_DEAD_ZONE"],
            max_send_hz=CONFIG["GIMBAL_MAX_HZ"],
            log_func=log,
        )

        if controller.connect():
            state.gimbal_controller = controller
            log("云台", "A8mini 云台控制器初始化成功")
            # 启动时回中
            controller.center()
        else:
            log("云台", "A8mini 连接失败，头显姿态将仅记录不控制")

    except Exception as e:
        log("云台错误", f"初始化异常: {e}")


if __name__ == "__main__":
    ensure_dir(CONFIG["AUDIO_CACHE_DIR"])

    init_sdk()
    init_gimbal()

    vr_msg_queue = Queue()

    threads = [
        threading.Thread(target=video_stream_thread, name="Video", daemon=True),
        threading.Thread(target=movement_control_thread, name="Move", daemon=True),
        threading.Thread(target=head_control_thread, name="Head", daemon=True),
        threading.Thread(target=audio_server_thread, args=(vr_msg_queue,), name="Audio", daemon=True),
        threading.Thread(target=ai_logic_thread, args=(vr_msg_queue,), name="AI", daemon=True),
        threading.Thread(target=monitor_thread, name="Monitor", daemon=True),
    ]

    for t in threads:
        t.start()

    log("系统", "=== Unified Server 已启动 ===")
    log("系统", f"Unity/Quest IP: {CONFIG['UNITY_IP']}")
    log("系统", f"RTSP URL: {CONFIG['RTSP_URL']}")
    log("系统", f"视频端口: {CONFIG['PORT_VIDEO_OUT']}")
    log("系统", f"头显端口: {CONFIG['PORT_HEAD_IN']}")
    log("系统", f"移动端口: {CONFIG['PORT_MOVE_IN']}")
    log("系统", f"交互端口: {CONFIG['PORT_AUDIO_RPC']}")
    log("系统", f"云台控制: {'已启用' if CONFIG['GIMBAL_ENABLED'] else '已关闭'}")
    if state.gimbal_controller:
        log("系统", f"云台目标: {CONFIG['GIMBAL_CAMERA_IP']}:{CONFIG['GIMBAL_CAMERA_PORT']}")

    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        log("系统", "收到退出信号，准备停止")
        state.is_running = False
        if state.gimbal_controller:
            state.gimbal_controller.disconnect()
        time.sleep(1.0)