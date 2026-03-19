# -*- coding: utf-8 -*-
"""
gimbal_test.py
A8mini 云台控制测试工具

用法:
  python gimbal_test.py                    # 使用默认 IP
  python gimbal_test.py 192.168.144.25     # 指定 IP
  python gimbal_test.py --simulate         # 模拟模式 (不真正发送)

交互命令:
  c       - 回中
  w/s     - Pitch 上/下 (5°步进)
  a/d     - Yaw 左/右 (10°步进)
  r       - 连续旋转测试 (扫描 -60°~60°)
  f       - 快速跟随测试 (模拟头部快速转动)
  h       - 心跳测试
  q       - 退出
"""

import sys
import time
import math

# 确保能找到同目录的模块
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gimbal_control import SiyiGimbalController


def log(tag, msg):
    print(f"[{tag}] {msg}", flush=True)


def run_sweep_test(ctrl: SiyiGimbalController, yaw_range=60, pitch_range=20, steps=30):
    """
    扫描测试: 云台平滑扫过一个范围, 验证跟随是否顺畅。
    """
    log("测试", f"开始扫描测试: yaw ±{yaw_range}°, pitch ±{pitch_range}°, {steps} 步")

    for i in range(steps + 1):
        t = i / steps  # 0.0 ~ 1.0
        angle = math.sin(t * 2 * math.pi)  # -1 ~ 1

        yaw = angle * yaw_range
        pitch = angle * pitch_range * 0.5

        ctrl.set_angle(yaw, pitch, use_smooth=False)
        log("扫描", f"  yaw={yaw:+.1f}°  pitch={pitch:+.1f}°")
        time.sleep(0.15)

    log("测试", "扫描测试完成, 回中")
    ctrl.center()


def run_follow_test(ctrl: SiyiGimbalController, duration=5.0):
    """
    快速跟随测试: 模拟头部快速左右转动, 验证平滑效果。
    """
    log("测试", f"开始快速跟随测试 ({duration}s)")

    start = time.time()
    while time.time() - start < duration:
        t = time.time() - start
        # 模拟头部快速摆动 (频率递增)
        freq = 0.5 + t * 0.3
        yaw = 40 * math.sin(2 * math.pi * freq * t)
        pitch = 10 * math.cos(2 * math.pi * freq * 0.7 * t)

        ctrl.set_angle(yaw, pitch, use_smooth=True)
        time.sleep(0.05)

    log("测试", "跟随测试完成, 回中")
    ctrl.center()


def interactive_mode(ctrl: SiyiGimbalController):
    """交互模式, 用键盘控制云台。"""
    current_yaw = 0.0
    current_pitch = 0.0
    yaw_step = 10.0
    pitch_step = 5.0

    print()
    print("=" * 50)
    print("  A8mini 云台交互控制")
    print("=" * 50)
    print("  w/s   — Pitch 上/下")
    print("  a/d   — Yaw 左/右")
    print("  c     — 回中")
    print("  r     — 扫描测试")
    print("  f     — 快速跟随测试")
    print("  h     — 心跳测试")
    print("  i     — 查看状态")
    print("  q     — 退出")
    print("=" * 50)
    print()

    while True:
        try:
            cmd = input(f"[yaw={current_yaw:+.1f}° pitch={current_pitch:+.1f}°] > ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            break

        if cmd == 'q':
            break
        elif cmd == 'c':
            current_yaw = 0.0
            current_pitch = 0.0
            ctrl.center()
            log("操作", "回中")
        elif cmd == 'w':
            current_pitch += pitch_step
            ctrl.set_angle(current_yaw, current_pitch, use_smooth=False)
            log("操作", f"Pitch 上 → {current_pitch:+.1f}°")
        elif cmd == 's':
            current_pitch -= pitch_step
            ctrl.set_angle(current_yaw, current_pitch, use_smooth=False)
            log("操作", f"Pitch 下 → {current_pitch:+.1f}°")
        elif cmd == 'a':
            current_yaw -= yaw_step
            ctrl.set_angle(current_yaw, current_pitch, use_smooth=False)
            log("操作", f"Yaw 左 → {current_yaw:+.1f}°")
        elif cmd == 'd':
            current_yaw += yaw_step
            ctrl.set_angle(current_yaw, current_pitch, use_smooth=False)
            log("操作", f"Yaw 右 → {current_yaw:+.1f}°")
        elif cmd == 'r':
            run_sweep_test(ctrl)
            current_yaw = 0.0
            current_pitch = 0.0
        elif cmd == 'f':
            run_follow_test(ctrl)
            current_yaw = 0.0
            current_pitch = 0.0
        elif cmd == 'h':
            ok = ctrl._send_heartbeat()
            log("心跳", "成功" if ok else "无回复")
        elif cmd == 'i':
            stats = ctrl.get_stats()
            for k, v in stats.items():
                print(f"  {k}: {v}")
        elif cmd:
            print(f"  未知命令: {cmd}")


def main():
    simulate = "--simulate" in sys.argv
    ip = "192.168.144.25"

    for arg in sys.argv[1:]:
        if not arg.startswith("--"):
            ip = arg

    if simulate:
        log("模式", "模拟模式 (不连接真实设备)")
        log("提示", "使用真实设备请去掉 --simulate 参数")
        # 模拟模式仍然创建控制器, 但连接会失败, 命令不会真正发送
        # 主要用于验证代码逻辑

    ctrl = SiyiGimbalController(camera_ip=ip, log_func=log)

    log("系统", f"连接 A8mini @ {ip}...")
    connected = ctrl.connect()

    if not connected and not simulate:
        log("错误", "连接失败! 请检查:")
        log("错误", f"  1. A8mini 是否开机并连接到同一网络")
        log("错误", f"  2. IP 地址是否正确: {ip}")
        log("错误", f"  3. 端口 37260 是否被防火墙阻止")
        log("提示", "使用 --simulate 可进入模拟模式")
        return

    try:
        interactive_mode(ctrl)
    finally:
        ctrl.disconnect()
        log("系统", "已退出")


if __name__ == "__main__":
    main()
