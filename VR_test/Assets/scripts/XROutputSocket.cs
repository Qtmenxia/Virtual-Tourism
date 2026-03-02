using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.InputSystem;

using System.Net.Sockets;
using System.Text;

using Newtonsoft.Json;
using Newtonsoft.Json.Linq;

public class XROutputSocket : MonoBehaviour
{
    private TcpClient client;
    private NetworkStream stream;
    private byte[] data;

    // public InputAction testAction;
    public InputActionReference testRightPrimaryButton;
    public InputActionReference testLeftPrimaryButton;

    public InputActionReference testRightSecondaryButton;
    public InputActionReference testLeftSecondaryButton;

    public InputActionReference testRightThumbstickValue;
    public InputActionReference testLeftThumbstickValue;

    // Start is called before the first frame update
    void Start()
    {
        client = new TcpClient("192.168.123.18", 5555); // 连接到Socket服务器
        stream = client.GetStream();

        testRightPrimaryButton.action.performed += TestRightPrimaryButton;
        //testLeftPrimaryButton.action.performed += TestLeftPrimaryButton;

        testRightSecondaryButton.action.performed += TestRightSecondaryButton;
        //testLeftSecondaryButton.action.performed += TestLeftSecondaryButton;

        testRightThumbstickValue.action.performed += TestRightThumbstickValue;
        testLeftThumbstickValue.action.performed += TestLeftThumbstickValue;

        
    }

    private void TestRightPrimaryButton(InputAction.CallbackContext callback)
    {
        print($"右手柄A按钮");

        string jsonData = "{\"action\":\"a_button\"}";
        byte[] data = Encoding.UTF8.GetBytes(jsonData + "\n");
        stream.Write(data, 0, data.Length);
    }
    private void TestLeftPrimaryButton(InputAction.CallbackContext callback)
    {
        print($"左手柄A按钮");

        string jsonData = "{\"action\":\"a_button\"}";
        byte[] data = Encoding.UTF8.GetBytes(jsonData + "\n");
        stream.Write(data, 0, data.Length);
    }
    private void TestRightSecondaryButton(InputAction.CallbackContext callback)
    {
        print($"右手柄B按钮");

        string jsonData = "{\"action\":\"b_button\"}";
        byte[] data = Encoding.UTF8.GetBytes(jsonData + "\n");
        stream.Write(data, 0, data.Length);
    }
    private void TestLeftSecondaryButton(InputAction.CallbackContext callback)
    {
        print($"左手柄B按钮");

        string jsonData = "{\"action\":\"b_button\"}";
        byte[] data = Encoding.UTF8.GetBytes(jsonData + "\n");
        stream.Write(data, 0, data.Length);
    }
    private void TestRightThumbstickValue(InputAction.CallbackContext callback)
    {
        Vector2 value = callback.ReadValue<Vector2>();
        var jsonObj = new JObject{["move"] = new JObject{["x"] = 0.0,["y"] = 0.0,["z"] = value.x}};

        string jsonData = jsonObj.ToString(Formatting.None);
        //stream.Write(value, 0, value.Length); // 发送数据
        byte[] data = Encoding.UTF8.GetBytes(jsonData + "\n");
        stream.Write(data, 0, data.Length);
    }

    private void TestLeftThumbstickValue(InputAction.CallbackContext callback)
    {
        Vector2 value = callback.ReadValue<Vector2>();
        var jsonObj = new JObject{["move"] = new JObject{["x"] = value.x,["y"] = value.y,["z"] = 0.0}};
        
        string jsonData = jsonObj.ToString(Formatting.None);
        byte[] data = Encoding.UTF8.GetBytes(jsonData + "\n");
        stream.Write(data, 0, data.Length);
    }

    private void OnDestroy()
    {
        testRightThumbstickValue.action.performed -= TestRightThumbstickValue;
        testLeftThumbstickValue.action.performed -= TestLeftThumbstickValue;

        testRightPrimaryButton.action.performed -= TestRightPrimaryButton;
        //testLeftPrimaryButton.action.performed -= TestLeftPrimaryButton;

        testRightSecondaryButton.action.performed -= TestRightSecondaryButton;
        //testLeftSecondaryButton.action.performed -= TestLeftSecondaryButton;

        client.Close();
    }

    // Update is called once per frame
    void Update()
    {
        
    }
}
