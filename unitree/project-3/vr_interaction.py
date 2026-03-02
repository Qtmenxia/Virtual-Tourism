import socket
import threading
import time
import json
import os

class VRInteraction:
    def __init__(self, host='0.0.0.0', port=8000):
        self.host = host
        self.port = port
        self.server_socket = None
        self.client_socket = None
        self.client_address = None
        self.running = False
        self.main_thread = None
        self.main_program_stop_event = None

    def connect_vr_glasses(self):
        """连接 VR 眼镜"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(1)
        print(f"服务器已启动,监听在 {self.host}:{self.port}...")
        return self

    def start_listening(self):
        """开始监听 VR 眼镜请求"""
        self.running = True
        try:
            while self.running:
                print("等待 VR 眼镜连接...")
                self.client_socket, self.client_address = self.server_socket.accept()
                print(f"VR 眼镜已连接: {self.client_address}")

                # 在新线程中处理客户端请求
                client_handler = threading.Thread(
                    target=self.handle_client_connection,
                    args=(self.client_socket,)
                )
                client_handler.daemon = True
                client_handler.start()

        except KeyboardInterrupt:
            print("服务器正在关闭...")
            self.stop_listening()

    def handle_client_connection(self, client_socket):
        """处理 VR 眼镜的连接请求"""
        try:
            while True:
                # 接收客户端数据
                data = client_socket.recv(1024)
                if not data:
                    break
                
                request = data.decode('utf-8').strip()
                print(f"接收到消息: {request}")

                # ==================== ★新增:处理文件下载请求 ★ ====================
                # 检查是否是音频文件请求
                if request.endswith('.mp3'):
                    print(f"收到文件下载请求: {request}")
                    self.send_audio_file(client_socket, request)
                    continue  # 跳过后续JSON处理

                # ==================== 原有的控制指令处理 ====================
                if request == "START":
                    # 启动主程序
                    from main import main
                    self.main_program_stop_event = threading.Event()
                    self.main_thread = threading.Thread(
                        target=main, 
                        args=(self, self.main_program_stop_event)
                    )
                    self.main_thread.daemon = True
                    self.main_thread.start()
                    response = {"status": "started", "message": "开始预测"}
                
                elif request == "STOP":
                    # 停止主程序
                    if self.main_program_stop_event:
                        self.main_program_stop_event.set()
                    response = {"status": "stopped", "message": "停止预测"}
                
                elif request == "STATUS":
                    # 返回当前状态
                    status = "running" if self.running else "idle"
                    response = {"status": status, "message": "当前状态"}
                
                else:
                    response = {"status": "error", "message": "未知请求"}

                # 发送JSON响应
                client_socket.send(json.dumps(response).encode('utf-8'))

        except Exception as e:
            print(f"处理请求时出错: {e}")
        finally:
            client_socket.close()
            print("客户端连接已关闭")

    # ==================== ★新增函数:发送音频文件 ★ ====================
    def send_audio_file(self, client_socket, filename):
        """
        发送音频文件到VR眼镜
        
        协议:
            1. 发送4字节文件大小(小端序整数)
            2. 分块发送文件内容(每次4KB)
        
        Args:
            client_socket: 客户端socket连接
            filename: 文件名(如"output.mp3")
        """
        try:
            # 构建完整文件路径
            # 假设音频文件在项目根目录
            file_path = os.path.join('/home/unitree/project-3', filename)
            
            # 检查文件是否存在
            if not os.path.exists(file_path):
                print(f"❌ 文件不存在: {file_path}")
                # 发送大小0表示文件不存在
                client_socket.send((0).to_bytes(4, byteorder='little'))
                return
            
            # 获取文件大小
            file_size = os.path.getsize(file_path)
            print(f"📁 文件: {filename}, 大小: {file_size} 字节 ({file_size/1024:.1f} KB)")
            
            # 步骤1: 发送文件大小(4字节小端序整数)
            size_bytes = file_size.to_bytes(4, byteorder='little')
            client_socket.send(size_bytes)
            print(f"✓ 已发送文件大小: {file_size}")
            
            # 步骤2: 分块发送文件内容
            with open(file_path, 'rb') as f:
                sent_bytes = 0
                chunk_size = 4096  # 每次发送4KB
                
                while sent_bytes < file_size:
                    # 读取数据块
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    
                    # 发送数据块
                    client_socket.send(chunk)
                    sent_bytes += len(chunk)
                    
                    # 显示进度(每100KB显示一次)
                    if sent_bytes % 102400 == 0 or sent_bytes == file_size:
                        progress = (sent_bytes / file_size) * 100
                        print(f"📤 发送进度: {progress:.1f}% ({sent_bytes}/{file_size})")
            
            print(f"✅ 文件发送完成: {filename}")
        
        except Exception as e:
            print(f"❌ 发送文件时出错: {e}")
            import traceback
            traceback.print_exc()

    def play_audio(self, audio_file):
        """发送播放指令到VR"""
        if self.client_socket:
            try:
                audio_info = {
                    "action": "play_audio",
                    "file_path": audio_file,
                    "timestamp": time.time()
                }
                self.client_socket.send(json.dumps(audio_info).encode('utf-8'))
                print(f"✓ 已发送音频播放指令: {audio_file}")
            except Exception as e:
                print(f"❌ 播放音频时出错: {e}")

    def stop_listening(self):
        """停止监听"""
        self.running = False
        if self.client_socket:
            self.client_socket.close()
        if self.server_socket:
            self.server_socket.close()
        print("服务器已关闭")


# 测试代码
if __name__ == "__main__":
    vr_interaction = VRInteraction()
    vr_glasses = vr_interaction.connect_vr_glasses()
    try:
        vr_glasses.start_listening()
    except KeyboardInterrupt:
        vr_glasses.stop_listening()
