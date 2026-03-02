using UnityEngine;
using UnityEngine.Networking;
using System.Collections;
using UnityEngine.InputSystem;
[System.Serializable]

public class FlaskMediaResponse
{
    public string status;
    public string message;
    public int size;
    public string[] audio_files;
}

public class PythonHttpClient : MonoBehaviour
{
    public int count_frames = 0;
    [Header("Server Settings")]
    public string serverUrl = "http://192.168.10.110:5000";
    public AudioSource audioSource;
    public FlaskMediaResponse response;

    public InputActionReference testLeftPrimaryButton;
    void Start()
    {
        SendToPython("are you ok");
        testLeftPrimaryButton.action.performed += TestLeftPrimaryButton;
    }

    void Update()
    {
        count_frames += 1;
        if (count_frames % 3000 == 0)
        {
            SendToPython("are you running");
        }
    }
    private void TestLeftPrimaryButton(InputAction.CallbackContext callback)
    {
        print($"左手柄A按钮");

        SendToPython("update");
        GetFromPython();
        PlayAudio();
    }
    public void SendToPython(string inputData)
    {
        StartCoroutine(PostRequest(inputData));
    }
    public void GetFromPython()
    {
        StartCoroutine(GetRequest());
    }
    public void PlayAudio()
    {

        StartCoroutine(DownloadAndPlayAudio());
    }

    IEnumerator PostRequest(string data)
    {
        // 创建JSON数据
        string json = "{\"input\":\"" + data + "\"}";
        byte[] postData = System.Text.Encoding.UTF8.GetBytes(json);

        // 设置请求
        UnityWebRequest request = new UnityWebRequest(serverUrl + "/message", "POST");
        request.uploadHandler = new UploadHandlerRaw(postData);
        request.downloadHandler = new DownloadHandlerBuffer();
        request.SetRequestHeader("Content-Type", "application/json");

        // 发送请求
        yield return request.SendWebRequest();

        if (request.result == UnityWebRequest.Result.Success)
        {
            string info = request.downloadHandler.text;

            Debug.Log("message响应: " + info);
        }
        else
        {
            Debug.LogError("请求错误: " + request.error);
        }
    }
    private FlaskMediaResponse ParseFlaskResponse(string jsonResponse)
    {
        try
        {
            // 使用 JsonUtility 解析 JSON
            FlaskMediaResponse response = JsonUtility.FromJson<FlaskMediaResponse>(jsonResponse);

            // 检查关键字段是否存在（可选）
            if (response == null)
            {
                Debug.LogError("Failed to parse JSON: Response is null.");
                return null;
            }

            if (string.IsNullOrEmpty(response.status))
            {
                Debug.LogWarning("Parsed JSON but 'status' field is missing or empty.");
            }

            return response;
        }
        catch (System.Exception ex)
        {
            Debug.LogError($"Failed to parse JSON: {ex.Message}");
            return null;
        }
    }
    IEnumerator GetRequest()
    {
        // 设置请求
        UnityWebRequest request = new UnityWebRequest(serverUrl + "/get_audio_data", "GET");
        request.downloadHandler = new DownloadHandlerBuffer();
        request.SetRequestHeader("Content-Type", "application/json");

        // 发送请求
        yield return request.SendWebRequest();

        if (request.result == UnityWebRequest.Result.Success)
        {
            string jsondata = request.downloadHandler.text;
            response = ParseFlaskResponse(jsondata);
            Debug.Log("response status:" + response.status);
            Debug.Log("message:" + response.message);
        }
        else
        {
            Debug.LogError("请求错误: " + request.error);
        }
    }
    IEnumerator DownloadAndPlayAudio()
    {

        using (UnityWebRequest www = UnityWebRequestMultimedia.GetAudioClip(serverUrl + "/download_audio", AudioType.MPEG))
        {
            yield return www.SendWebRequest();

            if (www.result == UnityWebRequest.Result.ConnectionError ||
                www.result == UnityWebRequest.Result.ProtocolError)
            {
                Debug.LogError(www.error);
            }
            else
            {
                AudioClip clip = DownloadHandlerAudioClip.GetContent(www);
                audioSource.clip = clip;
                audioSource.Play();
            }
        }
    }
}