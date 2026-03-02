// RTSPWebRTCReceiver.cs
// 用法：挂在场景某个 GameObject 上，Inspector 填写 signaling 地址等。
// 这个脚本负责：建立 PeerConnection -> 接收视频 track -> 把 track.Texture 赋给 RawImage 或 MeshRenderer 的材质。

using System;
using UnityEngine;
using Unity.WebRTC;
using UnityEngine.UI;
using System.Collections;

public class RTSPWebRTCReceiver : MonoBehaviour
{
    [Header("Signaling")]
    public string signalingServerUrl = "wss://your-signaling.example/ws"; // 你的信令服务器
    public string roomId = "camera-room";

    [Header("Display")]
    public RawImage displayImage; // 如果是 UI，用 RawImage
    public MeshRenderer displayRenderer; // 或者贴到场景物体

    RTCPeerConnection pc;
    VideoStreamTrack remoteTrack;
    Texture remoteTexture;

    IEnumerator Start()
    {
        // Unity WebRTC 3.0+ 不再需要显式调用 Initialize，
        // 但如果你使用的是需要初始化的版本，使用无参数版本：
        // WebRTC.Initialize();
        
        var config = GetDefaultRTCConfig();
        pc = new RTCPeerConnection(ref config);

        pc.OnTrack = e =>
        {
            Debug.Log("OnTrack received: " + e.Track.Kind);
            if (e.Track is VideoStreamTrack videoTrack)
            {
                remoteTrack = videoTrack;
                // 订阅 OnVideoReceived 事件来获取纹理
                videoTrack.OnVideoReceived += tex =>
                {
                    remoteTexture = tex;
                    ApplyTexture(remoteTexture);
                };
            }
        };

        // 启动 WebRTC 更新协程
        yield return StartCoroutine(WebRTC.Update());

        // TODO: signaling: connect to server, exchange offer/answer/ICE
        // 这里不写完整信令实现，示例给你 WebRTC 接收与渲染的关键代码
        // 如果需要，我可以一并给出简单的 Node.js 信令样例或 Janus 流程。
    }

    void ApplyTexture(Texture t)
    {
        if (displayImage) displayImage.texture = t;
        if (displayRenderer) displayRenderer.material.mainTexture = t;
    }

    private RTCConfiguration GetDefaultRTCConfig()
    {
        var config = new RTCConfiguration
        {
            iceServers = new[] {
                new RTCIceServer { urls = new[]{ "stun:stun.l.google.com:19302" } }
            }
        };
        return config;
    }

    private void OnDestroy()
    {
        if (remoteTrack != null) remoteTrack.Dispose();
        if (pc != null) 
        {
            pc.Close();
            pc.Dispose();
        }
        // WebRTC.Dispose() 在 3.0+ 版本中已移除，不需要调用
    }
}