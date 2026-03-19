# -*- coding: utf-8 -*-
"""
gimbal_control.py
思翼 A8mini 云台控制驱动

协议参考：Siyi A8mini SDK (UDP, 默认端口 37260)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
帧格式:
  STX(2) | CTRL(1) | Data_len(2,LE) | SEQ(2,LE) | CMD_ID(1) | DATA(N) | CRC16(2,LE)

主要命令:
  0x08 — 设置云台角度 (绝对值, 单位 0.1°)
         DATA: yaw(2,LE,signed) + pitch(2,LE,signed)
  0x07 — 手动旋转 (速度控制, -100~100)
         DATA: yaw_speed(1,signed) + pitch_speed(1,signed)
  0x01 — 固件版本查询 (心跳)
  0x08 — 获取当前云台角度
"""

import socket
import struct
import time
import threading
import math

# ========================================
# CRC-16/XMODEM 查表 (多项式 0x1021)
# ========================================
_CRC16_TABLE = [
    0x0000, 0x1021, 0x2042, 0x3063, 0x4084, 0x50A5, 0x60C6, 0x70E7,
    0x8108, 0x9129, 0xA14A, 0xB16B, 0xC18C, 0xD1AD, 0xE1CE, 0xF1EF,
    0x1231, 0x0210, 0x3273, 0x2252, 0x52B5, 0x4294, 0x72F7, 0x62D6,
    0x9339, 0x8318, 0xB37B, 0xA35A, 0xD3BD, 0xC39C, 0xF3FF, 0xE3DE,
    0x2462, 0x3443, 0x0420, 0x1401, 0x64E6, 0x74C7, 0x44A4, 0x5485,
    0xA56A, 0xB54B, 0x8528, 0x9509, 0xE5EE, 0xF5CF, 0xC5AC, 0xD58D,
    0x3653, 0x2672, 0x1611, 0x0630, 0x76D7, 0x66F6, 0x5695, 0x46B4,
    0xB75B, 0xA77A, 0x9719, 0x8738, 0xF7DF, 0xE7FE, 0xD79D, 0xC7BC,
    0x48C4, 0x58E5, 0x6886, 0x78A7, 0x0840, 0x1861, 0x2802, 0x3823,
    0xC9CC, 0xD9ED, 0xE98E, 0xF9AF, 0x8948, 0x9969, 0xA90A, 0xB92B,
    0x5AF5, 0x4AD4, 0x7AB7, 0x6A96, 0x1A71, 0x0A50, 0x3A33, 0x2A12,
    0xDBFD, 0xCBDC, 0xFBBF, 0xEB9E, 0x9B79, 0x8B58, 0xBB3B, 0xAB1A,
    0x6CA6, 0x7C87, 0x4CE4, 0x5CC5, 0x2C22, 0x3C03, 0x0C60, 0x1C41,
    0xEDAE, 0xFD8F, 0xCDEC, 0xDDCD, 0xAD2A, 0xBD0B, 0x8D68, 0x9D49,
    0x7E97, 0x6EB6, 0x5ED5, 0x4EF4, 0x3E13, 0x2E32, 0x1E51, 0x0E70,
    0xFF9F, 0xEFBE, 0xDFDD, 0xCFFC, 0xBF1B, 0xAF3A, 0x9F59, 0x8F78,
    0x9188, 0x81A9, 0xB1CA, 0xA1EB, 0xD10C, 0xC12D, 0xF14E, 0xE16F,
    0x1080, 0x00A1, 0x30C2, 0x20E3, 0x5004, 0x4025, 0x7046, 0x6067,
    0x83B9, 0x9398, 0xA3FB, 0xB3DA, 0xC33D, 0xD31C, 0xE37F, 0xF35E,
    0x02B1, 0x1290, 0x22F3, 0x32D2, 0x4235, 0x5214, 0x6277, 0x7256,
    0xB5EA, 0xA5CB, 0x95A8, 0x8589, 0xF56E, 0xE54F, 0xD52C, 0xC50D,
    0x34E2, 0x24C3, 0x14A0, 0x0481, 0x7466, 0x6447, 0x5424, 0x4405,
    0xA7DB, 0xB7FA, 0x8799, 0x97B8, 0xE75F, 0xF77E, 0xC71D, 0xD73C,
    0x26D3, 0x36F2, 0x0691, 0x16B0, 0x6657, 0x7676, 0x4615, 0x5634,
    0xD94C, 0xC96D, 0xF90E, 0xE92F, 0x99C8, 0x89E9, 0xB98A, 0xA9AB,
    0x5844, 0x4865, 0x7806, 0x6827, 0x18C0, 0x08E1, 0x3882, 0x28A3,
    0xCB7D, 0xDB5C, 0xEB3F, 0xFB1E, 0x8BF9, 0x9BD8, 0xABBB, 0xBB9A,
    0x4A75, 0x5A54, 0x6A37, 0x7A16, 0x0AF1, 0x1AD0, 0x2AB3, 0x3A92,
    0xFD2E, 0xED0F, 0xDD6C, 0xCD4D, 0xBDAA, 0xAD8B, 0x9DE8, 0x8DC9,
    0x7C26, 0x6C07, 0x5C64, 0x4C45, 0x3CA2, 0x2C83, 0x1CE0, 0x0CC1,
    0xEF1F, 0xFF3E, 0xCF5D, 0xDF7C, 0xAF9B, 0xBFBA, 0x8FD9, 0x9FF8,
    0x6E17, 0x7E36, 0x4E55, 0x5E74, 0x2E93, 0x3EB2, 0x0ED1, 0x1EF0,
]


def _crc16_xmodem(data: bytes) -> int:
    crc = 0x0000
    for b in data:
        idx = ((crc >> 8) ^ b) & 0xFF
        crc = ((crc << 8) ^ _CRC16_TABLE[idx]) & 0xFFFF
    return crc


# ========================================
# 帧构造
# ========================================
_STX = b'\x55\x66'
_CTRL_NEED_ACK = 0x01
_CTRL_NO_ACK   = 0x00


def _build_frame(cmd_id: int, data: bytes, seq: int = 0, ctrl: int = _CTRL_NEED_ACK) -> bytes:
    """
    构造一个完整的 Siyi 协议帧。
    """
    data_len = len(data)
    # header 部分 (不含 CRC)
    header = bytearray()
    header += _STX
    header.append(ctrl)
    header += struct.pack('<H', data_len)
    header += struct.pack('<H', seq)
    header.append(cmd_id)
    header += data
    # CRC16
    crc = _crc16_xmodem(bytes(header))
    header += struct.pack('<H', crc)
    return bytes(header)


# ========================================
# 命令常量
# ========================================
CMD_FIRMWARE_VER    = 0x01  # 心跳/固件版本查询
CMD_GIMBAL_SPEED    = 0x07  # 速度控制 (yaw_speed, pitch_speed 各 1 字节 signed)
CMD_GIMBAL_ANGLE    = 0x0E  # 角度控制 (yaw, pitch 各 2 字节 signed, 单位 0.1°)
CMD_CENTER_GIMBAL   = 0x08  # 回中
CMD_GET_GIMBAL_INFO = 0x0A  # 获取云台姿态信息
CMD_PHOTO           = 0x0C  # 拍照
CMD_RECORD          = 0x0D  # 录像


# ========================================
# 角度平滑滤波器
# ========================================
class AngleSmoother:
    """
    指数移动平均 (EMA) + 死区滤波器。
    防止头显微小抖动导致云台不断调整。
    """

    def __init__(self, alpha: float = 0.3, dead_zone_deg: float = 2.0):
        """
        Args:
            alpha: EMA 系数, 越大响应越快 (0.0~1.0)
            dead_zone_deg: 死区角度 (度), 变化小于此值时不更新
        """
        self.alpha = alpha
        self.dead_zone = dead_zone_deg
        self._smoothed_yaw = 0.0
        self._smoothed_pitch = 0.0
        self._last_sent_yaw = 0.0
        self._last_sent_pitch = 0.0
        self._initialized = False

    def update(self, raw_yaw: float, raw_pitch: float) -> tuple:
        """
        输入原始角度 (度), 返回 (smoothed_yaw, smoothed_pitch, should_send)
        should_send 为 False 时表示变化太小不需要发送
        """
        if not self._initialized:
            self._smoothed_yaw = raw_yaw
            self._smoothed_pitch = raw_pitch
            self._last_sent_yaw = raw_yaw
            self._last_sent_pitch = raw_pitch
            self._initialized = True
            return (raw_yaw, raw_pitch, True)

        # EMA 平滑
        self._smoothed_yaw = self.alpha * raw_yaw + (1 - self.alpha) * self._smoothed_yaw
        self._smoothed_pitch = self.alpha * raw_pitch + (1 - self.alpha) * self._smoothed_pitch

        # 死区检测
        delta_yaw = abs(self._smoothed_yaw - self._last_sent_yaw)
        delta_pitch = abs(self._smoothed_pitch - self._last_sent_pitch)

        if delta_yaw < self.dead_zone and delta_pitch < self.dead_zone:
            return (self._smoothed_yaw, self._smoothed_pitch, False)

        self._last_sent_yaw = self._smoothed_yaw
        self._last_sent_pitch = self._smoothed_pitch
        return (self._smoothed_yaw, self._smoothed_pitch, True)

    def reset(self):
        self._initialized = False


# ========================================
# 速率限制器
# ========================================
class RateLimiter:
    """
    限制云台命令发送频率，避免刷爆 A8mini 的 UDP 接口。
    A8mini 推荐控制频率不超过 20Hz。
    """

    def __init__(self, max_hz: float = 15.0):
        self.min_interval = 1.0 / max(max_hz, 1.0)
        self._last_time = 0.0

    def should_send(self) -> bool:
        now = time.time()
        if now - self._last_time >= self.min_interval:
            self._last_time = now
            return True
        return False


# ========================================
# 主控制类
# ========================================
class SiyiGimbalController:
    """
    思翼 A8mini 云台控制器。

    使用方法:
        controller = SiyiGimbalController(camera_ip="192.168.144.25")
        controller.connect()
        controller.set_angle(yaw_deg=30.0, pitch_deg=-15.0)
        controller.center()
        controller.disconnect()
    """

    DEFAULT_PORT = 37260  # A8mini 默认 UDP 控制端口

    def __init__(
        self,
        camera_ip: str = "192.168.144.25",
        camera_port: int = DEFAULT_PORT,
        yaw_limit: tuple = (-135.0, 135.0),
        pitch_limit: tuple = (-90.0, 25.0),
        smooth_alpha: float = 0.35,
        dead_zone_deg: float = 1.5,
        max_send_hz: float = 15.0,
        enable_heartbeat: bool = True,
        log_func=None,
    ):
        """
        Args:
            camera_ip:       A8mini 的 IP 地址
            camera_port:     A8mini 的 UDP 控制端口 (默认 37260)
            yaw_limit:       Yaw 角度限幅 (min_deg, max_deg)
            pitch_limit:     Pitch 角度限幅 (min_deg, max_deg)
            smooth_alpha:    EMA 平滑系数
            dead_zone_deg:   死区角度
            max_send_hz:     最大发送频率
            enable_heartbeat: 是否启用心跳 (定期查询固件版本保持连接)
            log_func:        日志函数, 签名 log(tag, msg)
        """
        self.camera_ip = camera_ip
        self.camera_port = camera_port
        self.yaw_limit = yaw_limit
        self.pitch_limit = pitch_limit

        self.smoother = AngleSmoother(alpha=smooth_alpha, dead_zone_deg=dead_zone_deg)
        self.rate_limiter = RateLimiter(max_hz=max_send_hz)

        self._socket = None
        self._seq = 0
        self._connected = False
        self._heartbeat_thread = None
        self._heartbeat_running = False
        self._enable_heartbeat = enable_heartbeat
        self._lock = threading.Lock()

        self._last_yaw = 0.0
        self._last_pitch = 0.0
        self._cmd_count = 0
        self._error_count = 0

        self._log = log_func if log_func else lambda tag, msg: print(f"[{tag}] {msg}", flush=True)

    # ---------- 连接管理 ----------

    def connect(self) -> bool:
        """打开 UDP 连接并启动心跳。"""
        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._socket.settimeout(2.0)
            self._connected = True
            self._log("云台", f"已连接 {self.camera_ip}:{self.camera_port}")

            # 测试连通性：发送固件版本查询
            if self._send_heartbeat():
                self._log("云台", "通信正常 (收到心跳回复)")
            else:
                self._log("云台", "警告: 未收到心跳回复，可能 IP/端口不正确")

            # 启动心跳线程
            if self._enable_heartbeat:
                self._heartbeat_running = True
                self._heartbeat_thread = threading.Thread(
                    target=self._heartbeat_loop,
                    name="GimbalHeartbeat",
                    daemon=True,
                )
                self._heartbeat_thread.start()

            return True

        except Exception as e:
            self._log("云台错误", f"连接失败: {e}")
            self._connected = False
            return False

    def disconnect(self):
        """断开连接，云台回中。"""
        self._heartbeat_running = False
        if self._connected:
            try:
                self.center()
            except Exception:
                pass
            try:
                self._socket.close()
            except Exception:
                pass
            self._connected = False
            self._log("云台", "已断开连接")

    @property
    def is_connected(self) -> bool:
        return self._connected

    # ---------- 命令发送 ----------

    def _next_seq(self) -> int:
        with self._lock:
            self._seq = (self._seq + 1) & 0xFFFF
            return self._seq

    def _send_cmd(self, cmd_id: int, data: bytes) -> bool:
        """发送一条命令到 A8mini。"""
        if not self._connected or self._socket is None:
            return False

        try:
            frame = _build_frame(cmd_id, data, seq=self._next_seq())
            self._socket.sendto(frame, (self.camera_ip, self.camera_port))
            self._cmd_count += 1
            return True
        except Exception as e:
            self._error_count += 1
            self._log("云台发送错误", str(e))
            return False

    def _send_heartbeat(self) -> bool:
        """发送固件版本查询作为心跳。"""
        if not self._send_cmd(CMD_FIRMWARE_VER, b''):
            return False

        # 尝试接收回复
        try:
            data, _ = self._socket.recvfrom(512)
            return len(data) > 0
        except socket.timeout:
            return False
        except Exception:
            return False

    def _heartbeat_loop(self):
        """定期发送心跳保持连接。"""
        while self._heartbeat_running and self._connected:
            try:
                self._send_heartbeat()
            except Exception:
                pass
            time.sleep(3.0)

    # ---------- 云台控制 ----------

    def set_angle(self, yaw_deg: float, pitch_deg: float, use_smooth: bool = True) -> bool:
        """
        设置云台绝对角度。

        Args:
            yaw_deg:    Yaw 角度 (度), 正值向右
            pitch_deg:  Pitch 角度 (度), 正值向上 (但 A8mini 的 pitch 正值向下,
                        这里做了翻转以匹配 Quest3 的直觉)
            use_smooth: 是否启用平滑滤波

        Returns:
            True 如果命令已发送
        """
        # 限幅
        yaw_deg = max(self.yaw_limit[0], min(yaw_deg, self.yaw_limit[1]))
        pitch_deg = max(self.pitch_limit[0], min(pitch_deg, self.pitch_limit[1]))

        if use_smooth:
            yaw_deg, pitch_deg, should_send = self.smoother.update(yaw_deg, pitch_deg)
            if not should_send:
                return False

        # 速率限制
        if not self.rate_limiter.should_send():
            return False

        # 转换为 0.1° 单位的 signed short
        yaw_raw = int(round(yaw_deg * 10))
        pitch_raw = int(round(-pitch_deg * 10))  # 翻转 pitch: Quest 抬头为正, A8mini 抬头为负

        # 限制 short 范围
        yaw_raw = max(-32768, min(yaw_raw, 32767))
        pitch_raw = max(-32768, min(pitch_raw, 32767))

        data = struct.pack('<hh', yaw_raw, pitch_raw)
        ok = self._send_cmd(CMD_GIMBAL_ANGLE, data)

        if ok:
            self._last_yaw = yaw_deg
            self._last_pitch = pitch_deg

        return ok

    def set_speed(self, yaw_speed: int, pitch_speed: int) -> bool:
        """
        速度控制模式。

        Args:
            yaw_speed:   -100 ~ 100 (正值向右)
            pitch_speed: -100 ~ 100 (正值向上)
        """
        yaw_speed = max(-100, min(yaw_speed, 100))
        pitch_speed = max(-100, min(pitch_speed, 100))
        data = struct.pack('<bb', yaw_speed, pitch_speed)
        return self._send_cmd(CMD_GIMBAL_SPEED, data)

    def center(self) -> bool:
        """云台回中。"""
        self._log("云台", "执行回中")
        self.smoother.reset()
        return self._send_cmd(CMD_CENTER_GIMBAL, b'\x01')

    def take_photo(self) -> bool:
        """拍照。"""
        return self._send_cmd(CMD_PHOTO, b'\x00')

    def start_recording(self) -> bool:
        """开始录像。"""
        return self._send_cmd(CMD_RECORD, b'\x02')

    def stop_recording(self) -> bool:
        """停止录像。"""
        return self._send_cmd(CMD_RECORD, b'\x00')

    # ---------- 状态 ----------

    def get_stats(self) -> dict:
        return {
            "connected": self._connected,
            "last_yaw": self._last_yaw,
            "last_pitch": self._last_pitch,
            "cmd_count": self._cmd_count,
            "error_count": self._error_count,
        }


# ========================================
# 独立测试
# ========================================
if __name__ == "__main__":
    import sys

    ip = sys.argv[1] if len(sys.argv) > 1 else "192.168.144.25"
    print(f"测试连接 A8mini @ {ip}")

    ctrl = SiyiGimbalController(camera_ip=ip)
    if not ctrl.connect():
        print("连接失败")
        sys.exit(1)

    print("回中...")
    ctrl.center()
    time.sleep(2)

    print("向右转 30°, 下俯 15°")
    ctrl.set_angle(30, -15, use_smooth=False)
    time.sleep(2)

    print("向左转 30°, 上仰 10°")
    ctrl.set_angle(-30, 10, use_smooth=False)
    time.sleep(2)

    print("回中")
    ctrl.center()
    time.sleep(1)

    print(f"统计: {ctrl.get_stats()}")
    ctrl.disconnect()
    print("测试完成")
