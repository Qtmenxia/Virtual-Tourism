"""
file: image_classification.py
基于 PyTorch 重构，用于 Unitree Go2
"""
import torch
import torch.nn as nn
import torchvision.transforms as transforms
from torchvision import models
import numpy as np
import json
import cv2
import os
from PIL import Image

# 检查设备 (Unitree Go2 通常使用 CPU，除非有外接算力棒)
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# ========== 1. 标签映射配置 ==========
pinyin_to_spot_name = {
    'hangtianguan_0': '航天馆',
    'hangtianguan_1': '航天馆',
    'tushuguan_0': '图书馆',
    'tushuguan_1': '图书馆',
    'tushuguan_2': '图书馆',
    'wozhencangqiong_0': '卧震苍穹',
    'wozhencangqiong_1': '卧震苍穹',
    'xiaobowuguan_0': '小博物馆',
    'xiaobulou_0': '小博物馆',
    'xiaobulou_1': '校部楼',
    'xingzhenglou_0': '行政楼',
    'xingzhenglou_1': '行政楼',
    'xingzhenglou_2': '行政楼',
    'zhulou_0': '主楼',
    'zhulou_1': '主楼',
    'zhulou_2': '主楼',
}

def pinyin_to_name(predicted_pinyin):
    return pinyin_to_spot_name.get(predicted_pinyin, "未知景点")

# 加载类别标签
try:
    with open('class_labels.json', 'r') as f:
        class_labels = json.load(f)
except FileNotFoundError:
    print("[错误] 找不到 class_labels.json")
    class_labels = []

# ========== 2. 模型定义与加载 ==========
# 注意：这里我们需要构建一个能加载 onnx2torch 转换权重的结构，
# 或者如果上面的转换脚本生成的是标准 ResNet 结构，则使用标准加载。
# 为了最大兼容性，我们这里使用动态加载器。

class Classifier:
    def __init__(self, model_path='resnet50_model.pth'):
        self.model = None
        self.transforms = self._get_transforms()
        self.load_model(model_path)

    def _get_transforms(self):
        # 定义标准的 ImageNet 预处理流程
        return transforms.Compose([
            transforms.ToPILImage(),         # 转换为 PIL 图片
            transforms.Resize((224, 224)),   # 调整大小
            transforms.ToTensor(),           # 转换为 Tensor (归一化到 0-1)
            # ResNet 标准均值和方差
            transforms.Normalize(mean=[0.485, 0.456, 0.406], 
                                 std=[0.229, 0.224, 0.225])
        ])

    def load_model(self, model_path):
        if not os.path.exists(model_path):
            print(f"[错误] 模型文件不存在: {model_path}")
            return

        try:
            # 尝试加载整个模型架构 (如果转换脚本保存的是 full model)
            # 或者我们需要重新定义架构。
            # 鉴于 onnx2torch 转换后的结构可能不完全等同于 torchvision.resnet50
            # 我们这里采用一种通用的加载方式：
            
            # 方案 A: 如果通过 onnx2torch 转换，它实际上保存了一个特殊的 GraphModule
            # 我们需要加载那个特定的结构。但是为了简单，
            # 如果你在第一步成功转换，你得到的 .pth 可能是一个字典。
            
            # 这里我们尝试构建一个标准的 ResNet50 并加载权重
            # 如果因为层命名不匹配导致失败，请使用转换脚本生成的模型文件直接加载
            
            # --- 使用 onnx2torch 转换后的加载逻辑 ---
            from onnx2torch import convert
            # 这是一个占位，实际上在推理时不需要 onnx 库
            # 如果第一步转换正确，我们这里直接加载
            
            # 【重要】为了确保万无一失，如果你上面的转换脚本使用的是 onnx2torch，
            # 生成的 pth 其实是 state_dict。但是 onnx2torch 生成的层名称和 torchvision 不一样。
            # 所以最简单的方法是：直接在转换时保存整个模型对象，而不是 state_dict。
            
            # 假设你在转换时使用了 torch.save(pytorch_model, PTH_OUTPUT) (保存整个对象)
            self.model = torch.load(model_path, map_location=device)
            self.model.eval()
            self.model.to(device)
            print("[系统] PyTorch 模型加载成功")
            
        except Exception as e:
            print(f"[错误] 加载模型失败: {e}")
            print("尝试方案B：构建标准 ResNet50 并加载...")
            try:
                self.model = models.resnet50(pretrained=False)
                # 修改全连接层以匹配分类数量
                num_ftrs = self.model.fc.in_features
                self.model.fc = nn.Linear(num_ftrs, len(class_labels))
                self.model.load_state_dict(torch.load(model_path, map_location=device))
                self.model.eval()
                self.model.to(device)
            except Exception as e2:
                 print(f"[严重错误] 无法加载模型权重: {e2}")

    def predict(self, img_array):
        """
        img_array: OpenCV 读取的图像 (BGR numpy array)
        """
        if self.model is None:
            return "模型未加载", 0.0

        # OpenCV (BGR) -> RGB
        img_rgb = cv2.cvtColor(img_array, cv2.COLOR_BGR2RGB)
        
        # 预处理
        input_tensor = self.transforms(img_rgb).unsqueeze(0).to(device)

        with torch.no_grad():
            outputs = self.model(input_tensor)
            
            # 应用 Softmax 获取概率
            probabilities = torch.nn.functional.softmax(outputs, dim=1)
            
            # 获取最大概率的索引
            confidence, predicted_idx = torch.max(probabilities, 1)
            
            idx = predicted_idx.item()
            score = confidence.item()

            if idx < len(class_labels):
                return class_labels[idx], score
            else:
                return "Unknown", score

# ========== 3. 全局实例 (供外部调用) ==========
classifier = Classifier('resnet50_model.pth')

# 兼容旧代码的接口
def predict_image(img_array):
    # 这里不需要预处理了，因为 Classifier 内部处理了
    # 但原来的逻辑是外部调用了 video_preprocessing
    # 我们为了兼容，忽略传入的已处理数据，建议直接传原始 cv2 图像
    pass 

# 实际使用的接口 (在 unified_server.py 中调用)
def predict_cv2_image(frame):
    """
    接收一个 cv2 frame，返回 (标签拼音, 置信度)
    """
    return classifier.predict(frame)

def classify_images(image_folder):
    """
    测试用：遍历文件夹分类
    """
    results = []
    confidences = []
    for img_name in os.listdir(image_folder):
        img_path = os.path.join(image_folder, img_name)
        img = cv2.imread(img_path)
        if img is not None:
            label, conf = classifier.predict(img)
            name = pinyin_to_name(label)
            results.append(name)
            confidences.append(conf)
    return results, confidences

# 移除旧的 video_preprocessing 依赖
class video_preprocessing:
    @staticmethod
    def preprocess_image(img):
        # 这是一个空实现，仅为了防止旧代码报错
        # 新逻辑已经在 Classifier 内部处理
        return img 
