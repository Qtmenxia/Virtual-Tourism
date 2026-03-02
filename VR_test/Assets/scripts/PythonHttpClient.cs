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
    public string label; // 添加label字段
}

public class PythonHttpClient : MonoBehaviour
{
    public int count_frames = 0; //帧计数器
    [Header("Server Settings")]
    public string serverUrl = "http://192.168.10.110:5000";
    public AudioSource audioSource;
    public FlaskMediaResponse response;

    // 状态控制变量
    private enum RequestState { Idle, Updating, GettingAudioData, PlayingAudio }
    private RequestState currentState = RequestState.Idle;
    private bool shouldRetry = false;
    private string currentLabel = "";

    public InputActionReference testLeftPrimaryButton;

    void Start()
    {
        SendToPython("are you ok");
        testLeftPrimaryButton.action.performed += TestLeftPrimaryButton;
    }

    void Update()
    {
        count_frames += 1;
        if (count_frames % 3000 == 0 && currentState == RequestState.Idle)
        {
            SendToPython("are you running");
        }
    }

    private void TestLeftPrimaryButton(InputAction.CallbackContext callback)
    {
        if (currentState != RequestState.Idle) return;

        print($"左手柄A按钮");
        StartCoroutine(FullProcessCoroutine());
    }

    IEnumerator FullProcessCoroutine()
    {
        // 1. 更新数据
        currentState = RequestState.Updating;
        yield return StartCoroutine(UpdateProcess());
        if (response.status == "success")
        {
        // 2. 获取音频数据
        currentState = RequestState.GettingAudioData;
        yield return StartCoroutine(GetAudioDataProcess());

        // 3. 播放音频
        currentState = RequestState.PlayingAudio;
        yield return StartCoroutine(PlayAudioProcess());

        }
        currentState = RequestState.Idle;
    }

    IEnumerator UpdateProcess()
    {
        int retryCount = 0;
        bool updateSuccess = false;

        while (!updateSuccess && retryCount < 3)
        {
            yield return StartCoroutine(PostRequest("update"));
            updateSuccess = !shouldRetry;
            
            if (!updateSuccess)
            {
                retryCount++;
                Debug.LogWarning($"更新失败，正在重试 ({retryCount}/3)");
                yield return new WaitForSeconds(1.0f); // 等待1秒后重试
            }
        }

        if (!updateSuccess)
        {
            Debug.LogError("更新失败，已达到最大重试次数");
        }
    }

    IEnumerator GetAudioDataProcess()
    {
        UnityWebRequest request = UnityWebRequest.Get(serverUrl + "/get_audio_data?label=" + currentLabel);
        yield return request.SendWebRequest();

        if (request.result == UnityWebRequest.Result.Success)
        {
            response = ParseFlaskResponse(request.downloadHandler.text);
            Debug.Log("Response status: " + response.status);
            
            if (response.status == "fail")
            {
                // 如果失败，使用others标签
                currentLabel = "others";
                Debug.Log("将播放未检测到的语音");
            }
        }
        else
        {
            Debug.LogError("获取音频数据错误: " + request.error);
            currentLabel = "others"; // 出错时也播放未检测语音
        }
    }

    IEnumerator PlayAudioProcess()
    {
        string audioUrl = $"{serverUrl}/download_audio?label={currentLabel}";
        if (currentLabel == "others")
        {
            audioUrl += "&filename=others_not_detected.mp3";
        }
        else
        {
            audioUrl += "&filename=audio_0.mp3";
        }

        using (UnityWebRequest www = UnityWebRequestMultimedia.GetAudioClip(audioUrl, AudioType.MPEG))
        {
            yield return www.SendWebRequest();

            if (www.result == UnityWebRequest.Result.Success)
            {
                AudioClip clip = DownloadHandlerAudioClip.GetContent(www);
                audioSource.clip = clip;
                audioSource.Play();
                Debug.Log($"正在播放 {currentLabel} 的语音");
            }
            else
            {
                Debug.LogError("音频播放失败: " + www.error);
            }
        }
    }

    public void SendToPython(string inputData)
    {
        StartCoroutine(PostRequest(inputData));
    }

    IEnumerator PostRequest(string data)
    {
        string json = "{\"input\":\"" + data + "\"}";
        byte[] postData = System.Text.Encoding.UTF8.GetBytes(json);// 转换为字节数组

        UnityWebRequest request = new UnityWebRequest(serverUrl + "/message", "POST");
        request.uploadHandler = new UploadHandlerRaw(postData);
        request.downloadHandler = new DownloadHandlerBuffer();
        request.SetRequestHeader("Content-Type", "application/json");

        yield return request.SendWebRequest();

        if (request.result == UnityWebRequest.Result.Success)
        {
            shouldRetry = false;
            Debug.Log("message响应: " + request.downloadHandler.text);
        }
        else
        {
            shouldRetry = true;
            Debug.LogError("请求错误: " + request.error);
        }
    }

    private FlaskMediaResponse ParseFlaskResponse(string jsonResponse)
    {
        try
        {
            FlaskMediaResponse response = JsonUtility.FromJson<FlaskMediaResponse>(jsonResponse);
            
            if (response == null)
            {
                Debug.LogError("Failed to parse JSON: Response is null.");
                return new FlaskMediaResponse { status = "fail", message = "解析响应失败" };
            }

            if (string.IsNullOrEmpty(response.status))
            {
                Debug.LogWarning("Parsed JSON but 'status' field is missing or empty.");
                response.status = "fail";
            }

            return response;
        }
        catch (System.Exception ex)
        {
            Debug.LogError($"Failed to parse JSON: {ex.Message}");
            return new FlaskMediaResponse { status = "fail", message = "解析响应时出错" };
        }
    }
}