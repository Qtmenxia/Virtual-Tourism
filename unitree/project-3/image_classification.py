# -*- coding: utf-8 -*-
"""
image_classification.py
第一阶段：稳定加载 landmark_classifier.pth
要求：
- class_labels.json 与 landmark_classifier.pth 放在同目录
- 采用标准 ResNet50 结构加载 state_dict
"""

import os
import json
import cv2
import torch
import torch.nn as nn
import torchvision.transforms as transforms
from torchvision import models

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "landmark_classifier.pth")
LABEL_PATH = os.path.join(BASE_DIR, "class_labels.json")

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


# =========================
# 标签映射
# =========================
pinyin_to_spot_name = {
    "hangtianguan_0": "航天馆",
    "hangtianguan_1": "航天馆",
    "others_0": "未知景点",
    "tushuguan_0": "图书馆",
    "tushuguan_1": "图书馆",
    "tushuguan_2": "图书馆",
    "wozhencangqiong_0": "卧震苍穹",
    "wozhencangqiong_1": "卧震苍穹",
    "xiaobowuguan_0": "小博物馆",
    "xiaobulou_0": "小博物馆",
    "xiaobulou_1": "校部楼",
    "xingzhenglou_0": "行政楼",
    "xingzhenglou_1": "行政楼",
    "xingzhenglou_2": "行政楼",
    "zhulou_0": "主楼",
    "zhulou_1": "主楼",
    "zhulou_2": "主楼",
}


def pinyin_to_name(predicted_pinyin: str) -> str:
    return pinyin_to_spot_name.get(predicted_pinyin, "未知景点")


def load_class_labels():
    if not os.path.exists(LABEL_PATH):
        print(f"[image_classification] 找不到标签文件: {LABEL_PATH}")
        return []
    with open(LABEL_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


class_labels = load_class_labels()


class Classifier:
    def __init__(self, model_path=MODEL_PATH):
        self.model = None
        self.transforms = transforms.Compose([
            transforms.ToPILImage(),
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225]
            )
        ])
        self.load_model(model_path)

    def _build_model(self, num_classes: int):
        model = models.resnet50(weights=None)
        in_features = model.fc.in_features
        model.fc = nn.Linear(in_features, num_classes)
        return model

    def load_model(self, model_path):
        if not class_labels:
            print("[image_classification] class_labels 为空，模型不加载")
            return

        if not os.path.exists(model_path):
            print(f"[image_classification] 模型文件不存在: {model_path}")
            return

        try:
            checkpoint = torch.load(model_path, map_location=device)

            model = self._build_model(len(class_labels))

            # 兼容多种保存格式
            if isinstance(checkpoint, dict):
                if "state_dict" in checkpoint and isinstance(checkpoint["state_dict"], dict):
                    state_dict = checkpoint["state_dict"]
                else:
                    state_dict = checkpoint
            else:
                # 如果真的存的是整个模型对象
                self.model = checkpoint.to(device)
                self.model.eval()
                print("[image_classification] 直接加载完整模型成功")
                return

            # 去掉 DataParallel 前缀
            cleaned_state_dict = {}
            for k, v in state_dict.items():
                if k.startswith("module."):
                    cleaned_state_dict[k[7:]] = v
                else:
                    cleaned_state_dict[k] = v

            model.load_state_dict(cleaned_state_dict, strict=False)
            model.to(device)
            model.eval()

            self.model = model
            print("[image_classification] landmark_classifier.pth 加载成功")

        except Exception as e:
            self.model = None
            print(f"[image_classification] 模型加载失败: {e}")

    def predict(self, img_array):
        if self.model is None:
            return "others_0", 0.0

        if img_array is None:
            return "others_0", 0.0

        try:
            img_rgb = cv2.cvtColor(img_array, cv2.COLOR_BGR2RGB)
            input_tensor = self.transforms(img_rgb).unsqueeze(0).to(device)

            with torch.no_grad():
                outputs = self.model(input_tensor)
                probabilities = torch.softmax(outputs, dim=1)
                confidence, predicted_idx = torch.max(probabilities, dim=1)

            idx = predicted_idx.item()
            score = float(confidence.item())

            if 0 <= idx < len(class_labels):
                return class_labels[idx], score

            return "others_0", score

        except Exception as e:
            print(f"[image_classification] 推理失败: {e}")
            return "others_0", 0.0


classifier = Classifier()


def predict_cv2_image(frame):
    return classifier.predict(frame)


def predict_image(img_array):
    return classifier.predict(img_array)


def classify_images(image_folder):
    results = []
    confidences = []

    if not os.path.isdir(image_folder):
        return results, confidences

    for img_name in os.listdir(image_folder):
        img_path = os.path.join(image_folder, img_name)
        img = cv2.imread(img_path)
        if img is None:
            continue
        label, conf = classifier.predict(img)
        results.append(pinyin_to_name(label))
        confidences.append(conf)

    return results, confidences


class video_preprocessing:
    @staticmethod
    def preprocess_image(img):
        return img