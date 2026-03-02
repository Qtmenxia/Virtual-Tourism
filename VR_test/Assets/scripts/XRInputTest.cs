using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.InputSystem;

public class XRInputTest : MonoBehaviour
{
    // public InputAction testAction;
    public InputActionReference testRightThumbstickValue;
    public InputActionReference testLeftThumbstickValue;

    // Start is called before the first frame update
    void Start()
    {
        testRightThumbstickValue.action.performed += TestRightThumbstickValue;
        testLeftThumbstickValue.action.performed += TestLeftThumbstickValue;
        
    }

    private void Ondestroy()
    {
        testRightThumbstickValue.action.performed -= TestRightThumbstickValue;
    }

    private void TestRightThumbstickValue(InputAction.CallbackContext callback)
    {
        Vector2 value = callback.ReadValue<Vector2>();
        print($"右手柄摇杆输入：{value}");
    }

    private void TestLeftThumbstickValue(InputAction.CallbackContext callback)
    {
        Vector2 value = callback.ReadValue<Vector2>();
        print($"左手柄摇杆输入：{value}");
    }

    // Update is called once per frame
    void Update()
    {
        
    }
}
