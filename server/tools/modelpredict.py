import torch
import torch.nn as nn
import torch.nn.functional as F
from torchvision import models, transforms
import numpy as np
from PIL import Image

# 定义类别标签映射
label2name = {
    "zhulou": "一校区主楼",
    "xiaobulou": "校部楼", 
    "xingzhenglou": "行政楼",
    "hangtianguan": "科学园航天馆",
    "xiaobowuguan": "校部楼",
    "tushuguan": "一校区图书馆",
    "wozhencangqiong": "科学园卧震苍穹",
    "others": "其他"
}

# 反向映射
name2label = {v: k for k, v in label2name.items()}

class ImageClassifier:
    def __init__(self, model_path=None, num_classes=8, device=None):
        """
        初始化 PyTorch 图像分类器
        
        Args:
            model_path: 预训练模型权重路径
            num_classes: 分类数量
            device: 运行设备 (cuda/cpu)
        """
        self.device = device if device else torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.num_classes = num_classes
        
        # 创建模型（使用 ResNet50 作为示例，可以替换为其他模型）
        self.model = models.resnet50(pretrained=True)
        
        # 修改最后一层以适应分类数量
        num_ftrs = self.model.fc.in_features
        self.model.fc = nn.Linear(num_ftrs, num_classes)
        
        # 将模型移到设备上
        self.model = self.model.to(self.device)
        
        # 加载预训练权重
        if model_path:
            self.load_model(model_path)
            
        # 设置为评估模式
        self.model.eval()
        
        # 定义预处理变换
        self.transform = transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])
    
    def load_model(self, model_path):
        """加载模型权重"""
        try:
            checkpoint = torch.load(model_path, map_location=self.device)
            if isinstance(checkpoint, dict) and 'model_state_dict' in checkpoint:
                self.model.load_state_dict(checkpoint['model_state_dict'])
            else:
                self.model.load_state_dict(checkpoint)
            print(f"成功加载模型权重: {model_path}")
        except Exception as e:
            print(f"加载模型权重失败: {e}")
    
    def preprocess_image(self, image):
        """
        预处理图像
        
        Args:
            image: PIL Image 或 numpy array
            
        Returns:
            预处理后的 tensor
        """
        if isinstance(image, np.ndarray):
            # 将 numpy array 转换为 PIL Image
            image = Image.fromarray(image)
        
        # 确保是 RGB 图像
        if image.mode != 'RGB':
            image = image.convert('RGB')
            
        # 应用预处理变换
        image_tensor = self.transform(image)
        
        # 添加 batch 维度
        image_tensor = image_tensor.unsqueeze(0)
        
        return image_tensor
    
    def predict(self, image):
        """
        预测图像类别
        
        Args:
            image: PIL Image 或 numpy array
            
        Returns:
            (label, confidence): 预测标签和置信度
        """
        # 预处理图像
        image_tensor = self.preprocess_image(image)
        image_tensor = image_tensor.to(self.device)
        
        # 预测
        with torch.no_grad():
            outputs = self.model(image_tensor)
            probabilities = F.softmax(outputs, dim=1)
            
            # 获取最高概率的类别
            confidence, predicted_idx = torch.max(probabilities, 1)
            
        # 转换为 numpy
        confidence = confidence.cpu().numpy()[0]
        predicted_idx = predicted_idx.cpu().numpy()[0]
        
        # 获取标签
        labels = list(label2name.keys())
        if predicted_idx < len(labels):
            label = labels[predicted_idx]
        else:
            label = "others"
            
        return label + "_0", float(confidence)
    
    def predict_top_k(self, image, k=5):
        """
        获取 top-k 预测结果
        
        Args:
            image: PIL Image 或 numpy array
            k: 返回的 top k 结果数量
            
        Returns:
            [(label, confidence), ...]: top k 预测结果列表
        """
        # 预处理图像
        image_tensor = self.preprocess_image(image)
        image_tensor = image_tensor.to(self.device)
        
        # 预测
        with torch.no_grad():
            outputs = self.model(image_tensor)
            probabilities = F.softmax(outputs, dim=1)
            
            # 获取 top k
            top_probs, top_indices = torch.topk(probabilities, k, dim=1)
            
        # 转换为列表
        results = []
        labels = list(label2name.keys())
        
        for i in range(k):
            idx = top_indices[0, i].cpu().numpy()
            prob = top_probs[0, i].cpu().numpy()
            
            if idx < len(labels):
                label = labels[idx]
            else:
                label = "others"
                
            results.append((label + "_0", float(prob)))
            
        return results

# 全局分类器实例
classifier = None

async def predict_image(image_array, model_path="./models/resnet50_model.pth"):
    """
    预测图像（兼容原有接口）
    
    Args:
        image_array: numpy array 或 PIL Image 格式的图像
        model_path: 模型权重路径
        
    Returns:
        (label, confidence): 预测标签和置信度
    """
    global classifier
    
    # 初始化分类器（如果还没有初始化）
    if classifier is None:
        classifier = ImageClassifier(model_path=model_path)
    
    # 预测
    label, confidence = classifier.predict(image_array)
    
    print(f"预测结果: {label}, 置信度: {confidence:.4f}")
    
    return label, confidence

# 用于训练的辅助函数
def create_model(num_classes=8, pretrained=True):
    """
    创建用于训练的模型
    
    Args:
        num_classes: 分类数量
        pretrained: 是否使用预训练权重
        
    Returns:
        PyTorch 模型
    """
    model = models.resnet50(pretrained=pretrained)
    num_ftrs = model.fc.in_features
    model.fc = nn.Linear(num_ftrs, num_classes)
    return model

def save_model(model, path, optimizer=None, epoch=None, loss=None):
    """
    保存模型
    
    Args:
        model: PyTorch 模型
        path: 保存路径
        optimizer: 优化器（可选）
        epoch: 当前 epoch（可选）
        loss: 当前损失（可选）
    """
    checkpoint = {
        'model_state_dict': model.state_dict(),
        'num_classes': model.fc.out_features
    }
    
    if optimizer:
        checkpoint['optimizer_state_dict'] = optimizer.state_dict()
    if epoch is not None:
        checkpoint['epoch'] = epoch
    if loss is not None:
        checkpoint['loss'] = loss
        
    torch.save(checkpoint, path)
    print(f"模型已保存到: {path}")

# 数据增强和预处理（用于训练）
train_transform = transforms.Compose([
    transforms.RandomResizedCrop(224),
    transforms.RandomHorizontalFlip(),
    transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2, hue=0.1),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

val_transform = transforms.Compose([
    transforms.Resize(256),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])