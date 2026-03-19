using UnityEngine;
using UnityEngine.InputSystem;
using System;
using System.Net;
using System.Net.Sockets;
using System.Text;

/// <summary>
/// Quest3 头显姿态 → Siyi A8mini 云台控制
/// 
/// 数据流: Quest3 头部旋转 → 构建 Siyi 协议帧 → UDP 发送到 Python 服务器
/// Python 服务器解析后经平滑处理转发给 A8mini 云台
/// 
/// 功能:
///   - 实时发送 pitch/yaw 到服务器
///   - 支持按键回中 (重置参考方向)
///   - 按键校准 (以当前朝向为正前方)
/// </summary>
[DisallowMultipleComponent]
public class Quest3EulerSender : MonoBehaviour
{
    // ========== 网络配置 ==========
    [Header("Network Settings")]
    [Tooltip("Python 服务器 IP 地址")]
    public string serverIP = "192.168.123.18";
    
    [Tooltip("服务器端口号 (对应 unified_server 的 PORT_HEAD_IN)")]
    public int serverPort = 6666;
    
    [Tooltip("数据发送间隔（秒）")]
    [Range(0.01f, 0.2f)]
    public float sendInterval = 0.05f;

    // ========== XR 输入配置 ==========
    [Header("XR Input")]
    [Tooltip("头显旋转输入 Action")]
    public InputActionProperty headRotationAction;

    [Tooltip("回中按钮 (可选, 如右手柄 B 键)")]
    public InputActionReference recenterAction;

    // ========== 云台参数 ==========
    [Header("Gimbal Mapping")]
    [Tooltip("Yaw 灵敏度 (1.0 = 1:1 映射)")]
    [Range(0.5f, 2.0f)]
    public float yawSensitivity = 1.0f;

    [Tooltip("Pitch 灵敏度")]
    [Range(0.5f, 2.0f)]
    public float pitchSensitivity = 1.0f;

    [Tooltip("Pitch 角度限幅 (度)")]
    public Vector2 pitchClamp = new Vector2(-45f, 135f);

    [Tooltip("Yaw 角度限幅 (度)")]
    public Vector2 yawClamp = new Vector2(-160f, 160f);

    // ========== 协议配置 ==========
    // Siyi A8mini 帧头: STX(55 66) + CTRL(01) + DataLen(04 00) + SEQ(00 00) + CMD_ID(0E)
    private static readonly byte[] COMMAND_HEADER = 
        { 0x55, 0x66, 0x01, 0x04, 0x00, 0x00, 0x00, 0x0E };

    // CRC-16/XMODEM 查表（多项式 0x1021）
    private static readonly ushort[] crc16Table = 
    {
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
        0x6E17, 0x7E36, 0x4E55, 0x5E74, 0x2E93, 0x3EB2, 0x0ED1, 0x1EF0
    };

    private UdpClient _udpClient;
    private IPEndPoint _remoteEP;
    private float _timer;
    private bool _isQuitting;
    private ushort _seqCounter;

    // 校准偏移 (按下回中键时记录当前朝向, 后续角度相对于此偏移)
    private Vector3 _calibrationOffset = Vector3.zero;
    private bool _isCalibrated = false;

    // 统计
    private int _packetsSent = 0;
    private int _sendErrors = 0;

    // ========== 生命周期方法 ==========
    private void Awake() => Application.quitting += () => _isQuitting = true;

    private void OnEnable()
    {
        try
        {
            InitializeUDP();
            headRotationAction.action.Enable();

            if (recenterAction != null)
            {
                recenterAction.action.Enable();
                recenterAction.action.performed += OnRecenter;
            }

            Debug.Log("[GimbalLink] UDP 模块已启动");
        }
        catch (Exception e)
        {
            Debug.LogError($"[GimbalLink] 初始化失败: {e.Message}");
        }
    }

    private void OnDisable()
    {
        if (recenterAction != null)
        {
            recenterAction.action.performed -= OnRecenter;
            recenterAction.action.Disable();
        }

        if (!_isQuitting)
        {
            ShutdownNetwork();
            Debug.Log("[GimbalLink] UDP 模块临时禁用");
        }
        headRotationAction.action.Disable();
    }

    private void Update()
    {
        try
        {
            var rotation = headRotationAction.action.ReadValue<Quaternion>();
            var rawEuler = rotation.eulerAngles;
            var euler = ProcessEulerAngles(rawEuler);

            // 定时发送
            if ((_timer += Time.deltaTime) >= sendInterval)
            {
                SendDatagram(euler);
                _timer = 0;
            }
        }
        catch (Exception e)
        {
            Debug.LogError($"[GimbalLink] 更新异常: {e.Message}");
        }
    }

    private void OnDestroy()
    {
        _isQuitting = true;
        ShutdownNetwork();
        Debug.Log($"[GimbalLink] 已销毁 (sent={_packetsSent}, errors={_sendErrors})");
    }

    // ========== 回中/校准 ==========
    private void OnRecenter(InputAction.CallbackContext ctx)
    {
        var rotation = headRotationAction.action.ReadValue<Quaternion>();
        var rawEuler = rotation.eulerAngles;

        _calibrationOffset = new Vector3(
            NormalizeAngle(rawEuler.x),
            NormalizeAngle(rawEuler.y),
            0
        );
        _isCalibrated = true;

        Debug.Log($"[GimbalLink] 已校准! 偏移: pitch={_calibrationOffset.x:F1}, yaw={_calibrationOffset.y:F1}");

        // 发送零位使云台回中
        SendDatagram(Vector3.zero);
    }

    /// <summary>
    /// 外部调用: 重置校准 (云台回到绝对模式)
    /// </summary>
    public void ResetCalibration()
    {
        _calibrationOffset = Vector3.zero;
        _isCalibrated = false;
        Debug.Log("[GimbalLink] 校准已重置");
    }

    // ========== 数据处理 ==========
    private float NormalizeAngle(float angle)
    {
        angle %= 360;
        return angle > 180 ? angle - 360 : angle;
    }

    private Vector3 ProcessEulerAngles(Vector3 rawEuler)
    {
        float pitch = NormalizeAngle(rawEuler.x);
        float yaw = NormalizeAngle(rawEuler.y);

        // 减去校准偏移
        if (_isCalibrated)
        {
            pitch -= _calibrationOffset.x;
            yaw -= _calibrationOffset.y;
        }

        // 应用灵敏度
        pitch *= pitchSensitivity;
        yaw *= yawSensitivity;

        // 限幅
        pitch = Mathf.Clamp(pitch, pitchClamp.x, pitchClamp.y);
        yaw = Mathf.Clamp(yaw, yawClamp.x, yawClamp.y);

        return new Vector3(pitch, yaw, 0);
    }

    // ========== 网络通信 ==========
    private void InitializeUDP()
    {
        try
        {
            _udpClient = new UdpClient();
            _remoteEP = new IPEndPoint(IPAddress.Parse(serverIP), serverPort);
            _seqCounter = 0;
            Debug.Log($"[GimbalLink] UDP 初始化成功, 目标: {serverIP}:{serverPort}");
        }
        catch (Exception e)
        {
            Debug.LogError($"[GimbalLink] UDP 初始化失败: {e.Message}");
            throw;
        }
    }

    private void SendDatagram(Vector3 euler)
    {
        try
        {
            // 数据转换: 角度 × 10 转为 short (0.1° 精度)
            short pitch = (short)(Mathf.Clamp(euler.x, pitchClamp.x, pitchClamp.y) * 10);
            short yaw = (short)(Mathf.Clamp(euler.y, yawClamp.x, yawClamp.y) * 10);

            // 构建完整 Siyi 协议帧
            var packet = new byte[14];

            // STX + CTRL + DataLen + SEQ(递增) + CMD_ID
            Buffer.BlockCopy(COMMAND_HEADER, 0, packet, 0, 8);
            // 更新序列号
            _seqCounter++;
            packet[4] = (byte)(_seqCounter & 0xFF);
            packet[5] = (byte)((_seqCounter >> 8) & 0xFF);

            // DATA: yaw(2 bytes LE) + pitch(2 bytes LE)
            Buffer.BlockCopy(BitConverter.GetBytes(yaw), 0, packet, 8, 2);
            Buffer.BlockCopy(BitConverter.GetBytes(pitch), 0, packet, 10, 2);

            // CRC16 over bytes[0..11]
            var crc = CalculateCRC(packet, 12);
            packet[12] = (byte)(crc & 0xFF);
            packet[13] = (byte)(crc >> 8);

            _udpClient.Send(packet, packet.Length, _remoteEP);
            _packetsSent++;
        }
        catch (Exception e)
        {
            _sendErrors++;
            Debug.LogError($"[GimbalLink] 发送失败: {e.Message}");

            if (_sendErrors > 10)
            {
                Debug.LogWarning("[GimbalLink] 错误过多, 尝试重新初始化 UDP");
                _sendErrors = 0;
                ShutdownNetwork();
                InitializeUDP();
            }
        }
    }

    private void ShutdownNetwork()
    {
        try
        {
            if (_udpClient != null)
            {
                // 发送零位回中
                SendDatagram(Vector3.zero);
                Debug.Log("[GimbalLink] 已发送回中指令");
            }
        }
        catch (Exception ex)
        {
            Debug.LogError($"[GimbalLink] 回中指令发送失败: {ex.Message}");
        }
        finally
        {
            _udpClient?.Close();
            _udpClient = null;
            Debug.Log("[GimbalLink] UDP 连接已关闭");
        }
    }

    // ========== CRC 计算 ==========
    private ushort CalculateCRC(byte[] data, int length)
    {
        ushort crc = 0x0000;
        for (var i = 0; i < length; i++)
        {
            var index = (byte)((crc >> 8) ^ data[i]);
            crc = (ushort)((crc << 8) ^ crc16Table[index]);
        }
        return crc;
    }
}
