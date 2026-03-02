import torch
import tensorflow as tf
import tf2onnx
import onnx
from onnx2torch import convert
import sys
import os

def convert_h5_to_pth(h5_path, pth_output_path):
    print(f"1. 加载 Keras 模型: {h5_path}")
    try:
        keras_model = tf.keras.models.load_model(h5_path)
    except Exception as e:
        print(f"加载失败: {e}")
        return

    # 定义输入签名 (假设 ResNet50 输入是 224x224 RGB)
    # 如果您的模型输入尺寸不同，请修改这里
    spec = (tf.TensorSpec((None, 224, 224, 3), tf.float32, name="input"),)

    print("2. 转换为 ONNX 格式...")
    model_proto, _ = tf2onnx.convert.from_keras(keras_model, input_signature=spec, opset=13)
    
    # 临时保存 onnx 用于调试 (可选)
    onnx_path = h5_path.replace(".h5", ".onnx")
    onnx.save(model_proto, onnx_path)

    print("3. 将 ONNX 转换为 PyTorch 模型...")
    # onnx2torch 会自动构建对应的 PyTorch 图结构
    pytorch_model = convert(onnx_path)

    print(f"4. 保存 PyTorch 模型到: {pth_output_path}")
    # 这里我们保存整个模型对象，这样在机器人上加载时不需要重新定义网络结构
    # 注意：这要求机器人上也安装 onnx2torch
    torch.save(pytorch_model, pth_output_path)
    
    print("\n=== 转换成功 ===")
    print(f"请将 '{pth_output_path}' 上传到机器人 /home/unitree/ 目录")
    print("并在机器人上安装: pip install onnx2torch")

if __name__ == "__main__":
    h5_file = "resnet50_model.h5"
    pth_file = "resnet50_model.pth"
    
    if not os.path.exists(h5_file):
        print(f"错误: 找不到文件 {h5_file}")
    else:
        convert_h5_to_pth(h5_file, pth_file)
