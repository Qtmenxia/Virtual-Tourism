using System;
using System.IO;
using System.Net.Sockets;
using System.Text;
using System.Threading.Tasks;

class VRClient
{
    private TcpClient client;
    private NetworkStream stream;
    private string serverIp = "192.168.10.110"; // 替换为运行服务器的机器狗的IP地址
    private int serverPort = 8080; // 替换为服务器监听的端口，应与vr_interaction.py中的端口一致

    public async Task StartClient()
    {
        try
        {
            client = new TcpClient();
            await client.ConnectAsync(serverIp, serverPort);
            stream = client.GetStream();
            Console.WriteLine("已连接到服务器");

            // 启动接收消息的任务
            Task receiveTask = ReceiveMessages();

            // 这里可以添加你的UI逻辑，例如按钮点击事件等
            // 以下是一些示例代码，模拟发送不同类型的请求
            Console.WriteLine("输入指令发送到服务器：");
            while (true)
            {
                string input = Console.ReadLine();
                switch (input)
                {
                    case "START":
                        await SendRequest("START");
                        break;
                    case "STOP":
                        await SendRequest("STOP");
                        break;
                    case "STATUS":
                        await SendRequest("STATUS");
                        break;
                    default:
                        Console.WriteLine("未知指令");
                        break;
                }
            }
        }
        catch (Exception e)
        {
            Console.WriteLine($"连接服务器失败: {e.Message}");
        }
    }

    private async Task SendRequest(string request)
    {
        try
        {
            byte[] data = Encoding.UTF8.GetBytes(request);
            await stream.WriteAsync(data, 0, data.Length);
            Console.WriteLine($"已发送请求: {request}");
        }
        catch (Exception e)
        {
            Console.WriteLine($"发送请求失败: {e.Message}");
        }
    }

    private async Task ReceiveMessages()
    {
        try
        {
            byte[] buffer = new byte[1024];
            while (true)
            {
                int bytesRead = await stream.ReadAsync(buffer, 0, buffer.Length);
                if (bytesRead == 0)
                {
                    Console.WriteLine("服务器断开连接");
                    break;
                }

                string response = Encoding.UTF8.GetString(buffer, 0, bytesRead);
                Console.WriteLine($"收到服务器响应: {response}");

                // 如果收到的是音频播放指令，处理音频播放
                if (response.StartsWith("{\"action\": \"play_audio\""))
                {
                    HandleAudioPlayback(response);
                }
            }
        }
        catch (Exception e)
        {
            Console.WriteLine($"接收消息失败: {e.Message}");
        }
        finally
        {
            // 关闭连接
            stream?.Close();
            client?.Close();
        }
    }

    private void HandleAudioPlayback(string audioInfo)
    {
        try
        {
            // 这里需要解析音频信息并播放音频
            // 实际应用中，你需要将音频数据从服务器获取并播放
            // 这里只是简单示例
            Console.WriteLine("收到音频播放指令，准备播放音频...");

            // 解析音频文件路径
            // 注意：实际应用中音频文件可能不会直接存储在服务器上的路径，而是通过流或其他方式传输
            // 下面的代码只是示例，实际需要根据你的音频传输方式调整
            string audioFilePath = ExtractAudioFilePath(audioInfo);
            Console.WriteLine($"音频文件路径: {audioFilePath}");

            // 播放音频的逻辑（需要你自己实现具体的播放功能）
            PlayAudioFile(audioFilePath);
        }
        catch (Exception e)
        {
            Console.WriteLine($"处理音频播放失败: {e.Message}");
        }
    }

    private string ExtractAudioFilePath(string audioInfo)
    {
        // 简单解析JSON格式的音频信息，获取文件路径
        // 实际应用中应该使用JSON解析库
        int startIndex = audioInfo.IndexOf("\"file_path\": \"") + "\"file_path\": \"".Length;
        int endIndex = audioInfo.IndexOf("\"", startIndex);
        return audioInfo.Substring(startIndex, endIndex - startIndex);
    }

    private void PlayAudioFile(string filePath)
    {
        // 这里是播放音频文件的示例逻辑
        // 实际应用中需要根据你的音频播放库来实现
        Console.WriteLine($"正在播放音频文件: {filePath}");
        // 你的音频播放代码
    }

    public void StopClient()
    {
        stream?.Close();
        client?.Close();
        Console.WriteLine("已断开与服务器的连接");
    }

    static async Task Main(string[] args)
    {
        VRClient client = new VRClient();
        await client.StartClient();
    }
}