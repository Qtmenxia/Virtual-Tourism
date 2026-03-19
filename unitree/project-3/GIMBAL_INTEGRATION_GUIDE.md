# 头显 → 云台联动 集成指南

## 新增/修改文件

### 新增: `gimbal_control.py`

Siyi A8mini 云台控制驱动，主要特性:

- 完整实现 Siyi 通信协议（STX + CTRL + DataLen + SEQ + CMD + DATA + CRC16）
- 支持角度控制（CMD 0x0E）和速度控制（CMD 0x07）
- 内置 EMA 指数平滑滤波器，消除头显微抖动
- 死区过滤：角度变化小于阈值时不发送命令，减少网络负载
- 速率限制器：控制发送频率不超过 15Hz（A8mini 推荐上限 20Hz）
- 心跳线程：定期查询固件版本保持 UDP 连接活跃
- Pitch 翻转：自动将 Quest3 的"抬头为正"映射到 A8mini 的"抬头为负"

### 新增: `gimbal_test.py`

交互式云台测试工具，支持:

- 键盘 WASD 手动控制
- 扫描测试（自动平滑扫过 ±60° 范围）
- 快速跟随测试（模拟头部快速摆动）
- 模拟模式（`--simulate`，不连接真实设备）

### 新增: `CameraSocket_v2.cs`

改进版头显姿态发送脚本，新增:

- 回中/校准按钮绑定（按下后以当前朝向为零点）
- 递增序列号（Siyi 协议要求）
- 灵敏度参数（Inspector 可调）
- 发送统计和错误计数
- 更清晰的日志前缀 `[GimbalLink]`

### 修改: `unified_server.py`

改动点:

1. 新增 `gimbal_control` 模块导入（可选，缺失不影响启动）
2. CONFIG 增加 12 个云台相关参数
3. RobotState 增加 `gimbal_controller`、`last_gimbal_cmd_time`、`gimbal_cmd_count`
4. `head_control_thread()` 接收到头显数据后，经缩放/偏移映射，调用 `gimbal.set_angle()`
5. `monitor_thread()` 增加云台状态显示（OK/IDLE/DISCONN/OFF）
6. 新增 `init_gimbal()` 函数，在 main 中 SDK 初始化后调用
7. 退出时自动调用 `gimbal.disconnect()` 使云台回中

## 数据流

```
Quest3 头部旋转
    ↓ (Unity InputSystem)
CameraSocket.cs / CameraSocket_v2.cs
    ↓ (构建 Siyi 协议帧, UDP 发往 Python)
unified_server.py : head_control_thread()
    ↓ (解析 yaw/pitch, 应用 scale + offset)
gimbal_control.py : SiyiGimbalController.set_angle()
    ↓ (EMA 平滑 → 死区过滤 → 速率限制 → 重新打包 Siyi 帧)
A8mini 云台 (UDP 37260)
    ↓ (物理转动)
RTSP 视频流方向改变
    ↓ (RTSP → Python → UDP JPEG)
Quest3 看到新视角
```

## 部署步骤

### 1. 复制文件到机器人

```bash
scp gimbal_control.py  unitree@192.168.123.18:/home/unitree/project-3/
scp gimbal_test.py     unitree@192.168.123.18:/home/unitree/project-3/
scp unified_server.py  unitree@192.168.123.18:/home/unitree/project-3/
```

### 2. 先测试云台通信

```bash
# 在机器人上运行
cd /home/unitree/project-3
python3 gimbal_test.py 192.168.144.25

# 按 c 回中, w/s 控制 pitch, a/d 控制 yaw
# 如果看到 "通信正常" 说明连接成功
```

### 3. 确认网络拓扑

```
A8mini 摄像头:  192.168.144.25  (RTSP: 8554, 云台控制: 37260)
Go2 机器人:     192.168.123.18  (Python 服务器)
Quest3 头显:    10.68.194.40    (Unity 客户端)
```

确保机器人能同时访问摄像头网段和 Quest3 网段。

### 4. 启动完整服务

```bash
cd /home/unitree/project-3
python3 unified_server.py
```

启动日志中应看到:
```
[云台] 已连接 192.168.144.25:37260
[云台] 通信正常 (收到心跳回复)
[云台] A8mini 云台控制器初始化成功
[系统] 云台控制: 已启用
```

### 5. Unity 侧替换脚本

将 `CameraSocket_v2.cs` 替换原有的 `CameraSocket.cs`，在 Inspector 中:

- 设置 `Server IP` = 机器人 IP
- 绑定 `Head Rotation Action` = XRI Head/Rotation
- 绑定 `Recenter Action` = 右手柄 B 键（可选）
- 调节 `Yaw/Pitch Sensitivity` 到舒适值

## 调参指南

在 `unified_server.py` 的 CONFIG 中:

| 参数 | 默认值 | 说明 |
|------|--------|------|
| GIMBAL_SMOOTH_ALPHA | 0.35 | 越大响应越快但越抖，建议 0.2~0.5 |
| GIMBAL_DEAD_ZONE | 1.5° | 越大越省带宽但会感觉"粘滞" |
| GIMBAL_MAX_HZ | 15 | 不要超过 20 |
| GIMBAL_YAW_SCALE | 1.0 | >1 放大头部运动，<1 缩小 |
| GIMBAL_PITCH_SCALE | 1.0 | 同上 |
| GIMBAL_YAW_OFFSET | 0.0° | 用于补偿摄像头安装偏差 |
| GIMBAL_PITCH_OFFSET | 0.0° | 同上 |

如果感觉延迟太大: 调高 `SMOOTH_ALPHA`（到 0.5）并降低 `DEAD_ZONE`（到 1.0°）。
如果感觉抖动严重: 调低 `SMOOTH_ALPHA`（到 0.2）并升高 `DEAD_ZONE`（到 2.5°）。

## 故障排查

| 症状 | 可能原因 | 解决方法 |
|------|----------|----------|
| "未收到心跳回复" | A8mini IP 不对 / 不在同一网段 | `ping 192.168.144.25` |
| 头显转动但云台不动 | 数据未到达 Python | 检查 `PRINT_HEAD_DATA` 日志 |
| 云台转动但很卡 | 网络丢包 / 发送频率太低 | 调高 `GIMBAL_MAX_HZ` |
| 云台一直抖动 | 死区太小 / 平滑系数太大 | 调大 `DEAD_ZONE` 到 3.0° |
| 监控显示 gimbal=DISCONN | 连接断开 | 重启服务或检查网络 |
