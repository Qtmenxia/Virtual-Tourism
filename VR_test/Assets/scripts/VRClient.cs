using UnityEngine;
using UnityEngine.InputSystem;
using System.Net.Sockets;
using System.Text;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System;
using System.Text.RegularExpressions;
using System.Threading.Tasks;
using UnityEngine.Networking;

public class VRClient : MonoBehaviour
{
    [Header("Network Settings")]
    public string serverIp = "192.168.123.18";
    public int serverPort = 8000;
    
    [Header("Audio Settings")]
    public AudioSource audioSource;
    
    [Header("Controller Settings")]
    public InputActionReference startAction;
    public InputActionReference stopAction;
    public InputActionReference statusAction;

    [Header("Audio Feedback")]
    public AudioClip buttonPressSound;
    public AudioClip connectionSound;
    public AudioClip errorSound;

    [Header("Debug Settings")]
    public bool enableDebugLog = true;
    
    // 缓存设置
    private string cacheDirectory;
    private const int MAX_CACHE_FILES = 5;
    private const float DOWNLOAD_TIMEOUT = 20f;
    private const float NETWORK_TIMEOUT = 10f;
    private const int MAX_RETRY_ATTEMPTS = 3;

    // 网络相关变量
    private TcpClient client;
    private NetworkStream stream;
    private bool isConnected = false;
    private bool shouldDisconnect = false;
    private bool isPredicting = false;
    
    // 连接跟踪
    private DateTime lastDataReceivedTime;
    private const int RECONNECT_DELAY_MS = 2000;
    private DateTime lastReconnectAttempt = DateTime.MinValue;
    
    // 消息处理
    private Queue<string> messageQueue = new Queue<string>();
    private readonly object queueLock = new object();
    private StringBuilder messageBuilder = new StringBuilder();
    
    // 任务管理
    private Task<bool> activeDownloadTask = null;
    private Task activeAudioLoadTask = null;
    private Task<bool> connectTask = null;
    
    // 重试计数器
    private int retryCount = 0;
    
    // 服务器响应数据结构
    [System.Serializable]
    private class ServerResponse
    {
        public string status;
        public string message;
        public string action;
        public string file_path;
    }

    void OnEnable()
    {
        // ⬇️⬇️⬇️ 修复：添加空值检查 ⬇️⬇️⬇️
        if (startAction != null) startAction.action.Enable();
        if (stopAction != null) stopAction.action.Enable();
        if (statusAction != null) statusAction.action.Enable();
        // ⬆️⬆️⬆️ 修复结束 ⬆️⬆️⬆️
    }

    void OnDisable()
    {
        // ⬇️⬇️⬇️ 修复：添加空值检查 ⬇️⬇️⬇️
        if (startAction != null) startAction.action.Disable();
        if (stopAction != null) stopAction.action.Disable();
        if (statusAction != null) statusAction.action.Disable();
        // ⬆️⬆️⬆️ 修复结束 ⬆️⬆️⬆️
        Disconnect();
    }

    void Start()
    {
        // 创建缓存目录
        cacheDirectory = Path.Combine(Application.persistentDataPath, "AudioCache");
        if (!Directory.Exists(cacheDirectory))
        {
            Directory.CreateDirectory(cacheDirectory);
            Log("Created audio cache directory: " + cacheDirectory);
        }
        
        // 启动连接
        ConnectToServerAsync();
        
        // ⬇️⬇️⬇️ 修复：添加空值检查 ⬇️⬇️⬇️
        // 绑定输入事件
        if (startAction != null)
            startAction.action.performed += ctx => SendNetworkCommand("START");
        if (stopAction != null)
            stopAction.action.performed += ctx => SendNetworkCommand("STOP");
        if (statusAction != null)
            statusAction.action.performed += ctx => SendNetworkCommand("STATUS");
        // ⬆️⬆️⬆️ 修复结束 ⬆️⬆️⬆️
    }

    void OnDestroy()
    {
        Disconnect();
    }

    void Update()
    {
        // 处理队列中的消息
        ProcessQueuedMessages();
        
        // 检查网络连接状态
        CheckNetworkStatus();
        
        // 检查任务状态
        CheckTaskStatus();
    }
    
    private void ProcessQueuedMessages()
    {
        lock (queueLock)
        {
            if (messageQueue.Count == 0) return;
            
            // 最多处理3条消息每帧，避免卡顿
            int processedCount = 0;
            while (messageQueue.Count > 0 && processedCount < 3)
            {
                string message = messageQueue.Dequeue();
                Log("Processing message: " + message);
                ProcessReceivedMessage(message);
                processedCount++;
            }
        }
    }
    
    private void CheckNetworkStatus()
    {
        if (!isConnected) return;
        
        // 检查网络超时
        if ((DateTime.Now - lastDataReceivedTime).TotalSeconds > NETWORK_TIMEOUT)
        {
            LogWarning($"No data received for {NETWORK_TIMEOUT}s, disconnecting...");
            Disconnect();
            ReconnectAfterDelay();
            return;
        }
        
        // 自动重连逻辑
        if ((client == null || !client.Connected) && 
            (DateTime.Now - lastReconnectAttempt).TotalMilliseconds > RECONNECT_DELAY_MS)
        {
            LogWarning("Connection lost, attempting to reconnect...");
            ReconnectAfterDelay();
        }
    }
    
    private void ReconnectAfterDelay()
    {
        Disconnect();
        lastReconnectAttempt = DateTime.Now;
        ConnectToServerAsync();
    }
    
    private void CheckTaskStatus()
    {
        if (activeDownloadTask != null)
        {
            if (activeDownloadTask.IsFaulted)
            {
                LogError($"Download task failed: {activeDownloadTask.Exception?.InnerException?.Message}");
                activeDownloadTask = null;
            }
            else if (activeDownloadTask.IsCompleted)
            {
                activeDownloadTask = null;
            }
        }
        
        if (activeAudioLoadTask != null)
        {
            if (activeAudioLoadTask.IsFaulted)
            {
                LogError($"Audio load task failed: {activeAudioLoadTask.Exception?.InnerException?.Message}");
                activeAudioLoadTask = null;
            }
            else if (activeAudioLoadTask.IsCompleted)
            {
                activeAudioLoadTask = null;
            }
        }
    }

    private async void ConnectToServerAsync()
    {
        if (isConnected || (connectTask != null && !connectTask.IsCompleted)) return;

        Log("Connecting to server...");
        
        try
        {
            client = new TcpClient();
            connectTask = Task.Run(() => 
            {
                client.ConnectAsync(serverIp, serverPort).Wait(5000);
                return client.Connected;
            });
            
            bool connected = await connectTask;
            
            if (connected)
            {
                stream = client.GetStream();
                isConnected = true;
                shouldDisconnect = false;
                lastDataReceivedTime = DateTime.Now;
                retryCount = 0;
                
                Log("Connected to server");
                
                // 开始接收消息
                _ = StartReceivingMessages();
            }
            else
            {
                LogError("Connection failed");
                if (retryCount < MAX_RETRY_ATTEMPTS)
                {
                    retryCount++;
                    LogWarning($"Retrying connection... Attempt {retryCount}/{MAX_RETRY_ATTEMPTS}");
                    await Task.Delay(1000);
                    ConnectToServerAsync();
                }
            }
        }
        catch (Exception e)
        {
            LogError($"Connection error: {e.Message}");
            if (retryCount < MAX_RETRY_ATTEMPTS)
            {
                retryCount++;
                LogWarning($"Retrying connection... Attempt {retryCount}/{MAX_RETRY_ATTEMPTS}");
                await Task.Delay(1000);
                ConnectToServerAsync();
            }
        }
        finally
        {
            connectTask = null;
        }
    }

    public void Disconnect()
    {
        if (!isConnected) return;
        
        shouldDisconnect = true;
        isConnected = false;
        
        try
        {
            if (stream != null)
            {
                stream.Close();
                stream = null;
            }
            
            if (client != null)
            {
                client.Close();
                client = null;
            }
            
            Log("Disconnected from server");
        }
        catch (Exception e)
        {
            LogError($"Error while disconnecting: {e.Message}");
        }
    }

    private void SendNetworkCommand(string command)
    {
        if (!isConnected)
        {
            LogWarning("Not connected - attempting to reconnect...");
            ConnectToServerAsync();
            return;
        }

        PlayButtonFeedback();
        
        try
        {
            byte[] data = Encoding.UTF8.GetBytes(command);
            stream.Write(data, 0, data.Length);
            Log($"Sent command: {command}");
        }
        catch (Exception e)
        {
            LogError($"Send failed: {e.Message}");
            Disconnect();
            ReconnectAfterDelay();
        }
    }

    private async Task StartReceivingMessages()
    {
        if (!isConnected) return;

        byte[] buffer = new byte[4096];
        Log("Start receiving messages...");
        
        try
        {
            while (isConnected && client != null && client.Connected && !shouldDisconnect)
            {
                try
                {
                    while (stream.DataAvailable)
                    {
                        int bytesRead = await stream.ReadAsync(buffer, 0, buffer.Length);
                        if (bytesRead == 0)
                        {
                            Log("Server disconnected");
                            shouldDisconnect = true;
                            break;
                        }

                        lastDataReceivedTime = DateTime.Now;
                        string message = Encoding.UTF8.GetString(buffer, 0, bytesRead);
                        Log($"Received raw message: {message}");

                        messageBuilder.Append(message);
                        ProcessMessageBuffer();
                    }
                    
                    await Task.Delay(50);
                }
                catch (ObjectDisposedException)
                {
                    Log("Network stream was disposed, stopping receive loop");
                    break;
                }
                catch (Exception e)
                {
                    LogError($"Receive error: {e.Message}");
                    shouldDisconnect = true;
                    break;
                }
            }
        }
        finally
        {
            if (shouldDisconnect)
            {
                Disconnect();
            }
            else
            {
                ReconnectAfterDelay();
            }
        }
    }
    
    private void ProcessMessageBuffer()
    {
        int newLineIndex = messageBuilder.ToString().IndexOf('\n');
        while (newLineIndex >= 0)
        {
            string message = messageBuilder.ToString(0, newLineIndex).Trim();
            messageBuilder.Remove(0, newLineIndex + 1);
            
            if (!string.IsNullOrEmpty(message))
            {
                lock (queueLock)
                {
                    messageQueue.Enqueue(message);
                }
            }
            
            newLineIndex = messageBuilder.ToString().IndexOf('\n');
        }
    }

    private void ProcessReceivedMessage(string message)
    {
        try
        {
            var response = JsonUtility.FromJson<ServerResponse>(message);
            if (response != null)
            {
                HandleServerResponse(response);
                return;
            }
        }
        catch
        {
            // 不是有效的JSON，继续处理
        }

        LogWarning($"Message is not valid JSON: {message}");
        
        if (message.Contains("play_audio") || message.Contains("file_path"))
        {
            string filePath = ExtractFilePathFromMessage(message);
            if (!string.IsNullOrEmpty(filePath))
            {
                LoadAndPlayAudio(filePath);
                return;
            }
        }
        else if (message.Contains("status") || message.Contains("message"))
        {
            Log($"Server response: {message}");
        }
        else
        {
            Log($"Raw server message: {message}");
        }
    }
    
    private void HandleServerResponse(ServerResponse response)
    {
        if (!string.IsNullOrEmpty(response.status))
        {
            switch (response.status.ToLower())
            {
                case "started":
                    isPredicting = true;
                    Log($"Prediction started: {response.message}");
                    break;
                    
                case "stopped":
                    isPredicting = false;
                    Log($"Prediction stopped: {response.message}");
                    break;
                    
                case "error":
                    LogError($"Server error: {response.message}");
                    HandleServerError();
                    break;
                    
                default:
                    Log($"Server status: {response.status}, message: {response.message}");
                    break;
            }
        }
        
        if (!string.IsNullOrEmpty(response.action) && response.action == "play_audio")
        {
            if (!string.IsNullOrEmpty(response.file_path))
            {
                Log($"Play audio request: {response.file_path}");
                LoadAndPlayAudio(response.file_path);
            }
            else
            {
                LogError("Received play_audio command without file_path");
            }
        }
    }
    
    private void HandleServerError()
    {
        LogWarning("Handling server error, attempting to reconnect...");
        Disconnect();
        ReconnectAfterDelay();
    }
    
    private string ExtractFilePathFromMessage(string message)
    {
        try
        {
            var match = Regex.Match(message, "\"file_path\"\\s*:\\s*\"([^\"]+)\"");
            if (match.Success)
            {
                return match.Groups[1].Value;
            }
            
            match = Regex.Match(message, @"file_path[\s=:]+([^\s\}""]+)");
            if (match.Success)
            {
                return match.Groups[1].Value;
            }
            
            return null;
        }
        catch (Exception e)
        {
            LogError($"Regex error: {e.Message}");
            return null;
        }
    }

    private void LoadAndPlayAudio(string originalPath)
    {
        string fileName = Path.GetFileName(originalPath);
        if (string.IsNullOrEmpty(fileName))
        {
            LogError($"Invalid file path: {originalPath}");
            return;
        }
        
        string uniqueName = $"{Path.GetFileNameWithoutExtension(fileName)}_{DateTime.Now.Ticks}{Path.GetExtension(fileName)}";
        string cachePath = Path.Combine(cacheDirectory, uniqueName);
        
        Log($"Starting audio download for: {fileName}");
        
        DownloadAudioFileAsync(fileName, cachePath, success => 
        {
            if (success)
            {
                PlayCachedAudio(cachePath);
                CleanupCacheFiles(fileName);
            }
            else
            {
                LogError("Audio download failed, skipping playback");
            }
        });
    }
    
    private async void DownloadAudioFileAsync(string fileName, string savePath, Action<bool> callback)
    {
        if (activeDownloadTask != null && !activeDownloadTask.IsCompleted)
        {
            LogWarning("Download already in progress, skipping new request");
            callback?.Invoke(false);
            return;
        }
        
        Log($"Requesting audio file: {fileName}");
        
        activeDownloadTask = DownloadFileAsyncInternal(fileName, savePath);
        
        try
        {
            bool result = await activeDownloadTask;
            callback?.Invoke(result);
        }
        catch (Exception e)
        {
            LogError($"Download failed: {e.Message}");
            callback?.Invoke(false);
        }
    }
    
    private async Task<bool> DownloadFileAsyncInternal(string fileName, string savePath)
    {
        DateTime totalStartTime = DateTime.Now;
        const float TOTAL_TIMEOUT = 40f;
        
        try
        {
            byte[] requestData = Encoding.UTF8.GetBytes(fileName);
            await stream.WriteAsync(requestData, 0, requestData.Length);
            Log($"Sent audio request: {fileName}");
            
            byte[] sizeBuffer = new byte[4];
            int bytesRead = 0;
            
            DateTime headerStartTime = DateTime.Now;
            while (bytesRead < 4)
            {
                if ((DateTime.Now - headerStartTime).TotalSeconds > DOWNLOAD_TIMEOUT)
                {
                    throw new Exception("Header read timed out");
                }
                
                int readNow = await stream.ReadAsync(sizeBuffer, bytesRead, 4 - bytesRead);
                if (readNow == 0)
                {
                    throw new Exception("Server disconnected during download");
                }
                
                bytesRead += readNow;
                await Task.Delay(10);
            }
            
            int fileSize = BitConverter.ToInt32(sizeBuffer, 0);
            Log($"File size: {fileSize} bytes");
            
            if (fileSize <= 0)
            {
                throw new Exception($"Invalid file size: {fileSize}");
            }
            
            using (FileStream fileStream = new FileStream(savePath, FileMode.Create, FileAccess.Write))
            {
                int totalBytesRead = 0;
                byte[] fileData = new byte[4096];
                
                while (totalBytesRead < fileSize)
                {
                    if ((DateTime.Now - totalStartTime).TotalSeconds > TOTAL_TIMEOUT)
                    {
                        throw new Exception($"Total download timed out ({TOTAL_TIMEOUT}s)");
                    }
                    
                    int bytesToRead = Math.Min(fileSize - totalBytesRead, fileData.Length);
                    int read = await stream.ReadAsync(fileData, 0, bytesToRead);
                    if (read == 0)
                    {
                        throw new Exception("Server disconnected during file transfer");
                    }
                    
                    await fileStream.WriteAsync(fileData, 0, read);
                    totalBytesRead += read;
                    
                    float progress = (float)totalBytesRead / fileSize * 100f;
                    if (totalBytesRead % (1024 * 10) == 0)
                    {
                        Log($"Download progress: {progress:F1}%");
                    }
                }
                
                Log($"File saved to: {savePath}");
                return true;
            }
        }
        catch (Exception e)
        {
            if (File.Exists(savePath))
            {
                try { File.Delete(savePath); }
                catch { LogWarning("Failed to delete incomplete file"); }
            }
            
            LogError($"Download error: {e.Message}");
            return false;
        }
    }
    
    private async void PlayCachedAudio(string filePath)
    {
        if (!File.Exists(filePath))
        {
            LogError($"Audio file not found: {filePath}");
            return;
        }
        
        string url = GetAudioFilePath(filePath);
        Log($"Loading audio from: {url}");
        
        using (UnityWebRequest www = new UnityWebRequest(url, "GET"))
        {
            DownloadHandlerAudioClip downloadHandler = new DownloadHandlerAudioClip(url, AudioType.UNKNOWN);
            downloadHandler.streamAudio = true;
            www.downloadHandler = downloadHandler;
            www.timeout = 15;
            
            activeAudioLoadTask = LoadAndPlayAudioAsync(www, filePath);
            await activeAudioLoadTask;
        }
    }
    
    private async Task LoadAndPlayAudioAsync(UnityWebRequest www, string filePath)
    {
        try
        {
            www.SendWebRequest();
            
            while (!www.isDone)
            {
                await Task.Delay(100);
                if ((DateTime.Now - lastDataReceivedTime).TotalSeconds > DOWNLOAD_TIMEOUT)
                {
                    LogError("Audio loading timed out");
                    return;
                }
            }
            
            HandleAudioLoadResult(www, filePath);
        }
        catch (Exception e)
        {
            LogError($"Audio load error: {e.Message}");
        }
    }
    
    private void HandleAudioLoadResult(UnityWebRequest www, string filePath)
    {
        if (www.result != UnityWebRequest.Result.Success)
        {
            LogError($"Audio load failed! Error: {www.error}");
            TryDifferentAudioFormats(filePath);
            return;
        }
        
        AudioClip clip = ((DownloadHandlerAudioClip)www.downloadHandler).audioClip;
        if (clip == null)
        {
            LogError("Downloaded audio clip is null");
            TryDifferentAudioFormats(filePath);
            return;
        }
        
        audioSource.clip = clip;
        audioSource.Play();
        Log($"Playing audio: {Path.GetFileName(filePath)}");
    }
    
    private string GetAudioFilePath(string filePath)
    {
        #if UNITY_ANDROID
        return "file://" + filePath;
        #else
        return "file:///" + filePath;
        #endif
    }
    
    private void TryDifferentAudioFormats(string filePath)
    {
        if (!File.Exists(filePath))
        {
            LogError("File not found for alternative formats");
            return;
        }
        
        Log("Attempting alternative formats");
        
        TryAudioFormat(filePath, AudioType.WAV);
        TryAudioFormat(filePath, AudioType.MPEG);
        TryAudioFormat(filePath, AudioType.OGGVORBIS);
    }
    
    private async void TryAudioFormat(string filePath, AudioType format)
    {
        string url = GetAudioFilePath(filePath);
        
        using (UnityWebRequest www = UnityWebRequestMultimedia.GetAudioClip(url, format))
        {
            www.SendWebRequest();
            
            DateTime startTime = DateTime.Now;
            while (!www.isDone)
            {
                await Task.Delay(100);
                if ((DateTime.Now - startTime).TotalSeconds > 10)
                {
                    Log($"Format {format} timed out");
                    return;
                }
            }
            
            if (www.result != UnityWebRequest.Result.Success || www.downloadHandler == null)
            {
                Log($"Format {format} failed: {www.error}");
                return;
            }
            
            AudioClip clip = ((DownloadHandlerAudioClip)www.downloadHandler).audioClip;
            if (clip != null)
            {
                audioSource.clip = clip;
                audioSource.Play();
                Log($"Success with format: {format}");
            }
        }
    }
    
    private void CleanupCacheFiles(string fileNamePrefix)
    {
        try
        {
            string prefix = Path.GetFileNameWithoutExtension(fileNamePrefix);
            var files = Directory.GetFiles(cacheDirectory, $"{prefix}*")
                .OrderByDescending(f => new FileInfo(f).CreationTime)
                .ToList();
                
            if (files.Count > MAX_CACHE_FILES)
            {
                for (int i = MAX_CACHE_FILES; i < files.Count; i++)
                {
                    try
                    {
                        File.Delete(files[i]);
                        Log($"Deleted old cache file: {Path.GetFileName(files[i])}");
                    }
                    catch (Exception e)
                    {
                        LogWarning($"Failed to delete cache file: {e.Message}");
                    }
                }
            }
        }
        catch (Exception e)
        {
            LogError($"Cache cleanup error: {e.Message}");
        }
    }
    
    private void PlayButtonFeedback()
    {
        if (buttonPressSound != null && audioSource != null)
        {
            audioSource.PlayOneShot(buttonPressSound);
        }
    }
    
    private void Log(string message)
    {
        if (enableDebugLog) Debug.Log($"[VRClient] {message}");
    }
    
    private void LogError(string message)
    {
        if (errorSound != null && audioSource != null)
        {
            audioSource.PlayOneShot(errorSound);
        }
        Debug.LogError($"[VRClient] {message}");
    }
    
    private void LogWarning(string message)
    {
        Debug.LogWarning($"[VRClient] {message}");
    }
}
