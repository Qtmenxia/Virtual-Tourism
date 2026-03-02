using UnityEngine;
using UnityEngine.Networking;
using System.Collections;

public class PythonHttpClient : MonoBehaviour
{
    public int count_frames = 0;
    [Header("Server Settings")]
    public string serverUrl = "http://localhost:5000";
    public string introduction = "";
    void Start()
    {
        SendToPython("are you ok");
        SendToPython("update");
    }

    void Update()
    {
        count_frames += 1;
        if (count_frames % 1000 == 0)
            SendToPython("are you running");
        if (count_frames % 1000000 == 0 && count_frames <= 2000000)
        {
            SendToPython("update");
        } 
    }
    public void SendToPython(string inputData)
    {
        StartCoroutine(PostRequest(inputData));
    }

    IEnumerator PostRequest(string data)
    {
        // 创建JSON数据
        string json = "{\"input\":\"" + data + "\"}";
        byte[] postData = System.Text.Encoding.UTF8.GetBytes(json);

        // 设置请求
        UnityWebRequest request = new UnityWebRequest(serverUrl+"/message", "POST");
        request.uploadHandler = new UploadHandlerRaw(postData);
        request.downloadHandler = new DownloadHandlerBuffer();
        request.SetRequestHeader("Content-Type", "application/json");

        // 发送请求
        yield return request.SendWebRequest();

        if (request.result == UnityWebRequest.Result.Success)
        {
            introduction = request.downloadHandler.text;
            Debug.Log("Python响应: " + introduction);
        }
        else
        {
            Debug.LogError("请求错误: " + request.error);
        }
    }
    [System.Serializable]
    private class FlaskMediaResponse
    {
        public string status;
        public int timestamp;
        public string message;
        public string[] audio_files;
        public string instructions;
    }
}