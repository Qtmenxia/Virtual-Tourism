using System.Collections;
using System.Collections.Generic;
using UnityEngine;

using System.Net.Sockets;
using System.Text;

public class SocketClient : MonoBehaviour
{
    private TcpClient client;
    private NetworkStream stream;
    private byte[] data;

    void Start()
    {
        client = new TcpClient("192.168.159.65", 5555); // 连接到Python端的Socket服务器
        stream = client.GetStream();
    }

    void SendData(string message)
    {
        data = Encoding.ASCII.GetBytes(message);
        stream.Write(data, 0, data.Length); // 发送数据
    }
}