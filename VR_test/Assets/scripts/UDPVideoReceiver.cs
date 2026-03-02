using UnityEngine;
using UnityEngine.UI;
using System.Net;
using System.Net.Sockets;
using System.Threading;
using System.Collections.Concurrent;

public class UDPVideoReceiver : MonoBehaviour
{
    [Header("Network Settings")]
    public int listenPort = 7777; // 对应 Python 的 VIDEO_OUT

    [Header("Display")]
    public RawImage displayImage; // 拖入场景中的 UI RawImage 组件
    public Text statusText;       // 可选：用于显示 FPS

    private UdpClient udpClient;
    private Thread receiveThread;
    private bool isRunning;
    
    // 线程安全队列，用于在子线程接收数据，主线程渲染
    private ConcurrentQueue<byte[]> frameQueue = new ConcurrentQueue<byte[]>();
    private Texture2D texture;
    
    // 性能监控
    private float lastFrameTime;
    private int frameCount;

    void Start()
    {
        // 初始化纹理 (尺寸会由 LoadImage 自动调整，初始值不重要)
        texture = new Texture2D(640, 480, TextureFormat.RGB24, false);
        if (displayImage != null)
        {
            displayImage.texture = texture;
            // 修正画面倒转问题（OpenCV 和 Unity 坐标系差异）
            // displayImage.uvRect = new Rect(0, 0, 1, -1); // 如果画面倒了，取消注释这行
        }

        StartUDP();
    }

    void StartUDP()
    {
        try
        {
            udpClient = new UdpClient(listenPort);
            // 增加接收缓冲区，防止高清图丢包
            udpClient.Client.ReceiveBufferSize = 1024 * 1024 * 4; 
            
            isRunning = true;
            receiveThread = new Thread(ReceiveLoop);
            receiveThread.IsBackground = true;
            receiveThread.Start();
            
            Debug.Log($"[UDP Video] 开始监听端口 {listenPort}");
        }
        catch (System.Exception e)
        {
            Debug.LogError($"[UDP Video] 启动失败: {e.Message}");
        }
    }

    // 子线程：只负责收网，不处理图像
    void ReceiveLoop()
    {
        IPEndPoint remoteEP = new IPEndPoint(IPAddress.Any, 0);
        while (isRunning)
        {
            try
            {
                byte[] data = udpClient.Receive(ref remoteEP);
                if (data.Length > 0)
                {
                    // 简单的丢帧策略：如果队列里堆积了太多帧，说明渲染跟不上，清空旧的
                    if (frameQueue.Count > 2)
                    {
                        byte[] dump;
                        while(frameQueue.Count > 1) frameQueue.TryDequeue(out dump);
                    }
                    frameQueue.Enqueue(data);
                }
            }
            catch (SocketException)
            {
                // socket 关闭时会抛出异常，忽略
            }
            catch (System.Exception e)
            {
                Debug.LogWarning($"[UDP Receive Error] {e.Message}");
            }
        }
    }

    // 主线程：负责解码 JPEG 并上传 GPU
    void Update()
    {
        if (frameQueue.TryDequeue(out byte[] jpgData))
        {
            try
            {
                // LoadImage 是耗时操作，但在 Unity 中必须在主线程调用
                texture.LoadImage(jpgData); 
                texture.Apply();
                
                // 计算 FPS
                frameCount++;
                if (Time.time - lastFrameTime >= 1.0f)
                {
                    if(statusText != null) statusText.text = $"FPS: {frameCount} | KB: {jpgData.Length/1024}";
                    frameCount = 0;
                    lastFrameTime = Time.time;
                }
            }
            catch
            {
                Debug.LogWarning("解码图片失败");
            }
        }
    }

    void OnDestroy()
    {
        isRunning = false;
        if (udpClient != null) udpClient.Close();
        if (receiveThread != null && receiveThread.IsAlive) receiveThread.Abort();
    }
}
