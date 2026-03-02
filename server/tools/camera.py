import cv2
import numpy as np
from PIL import Image
import torch
from torchvision import transforms

def get_image(source):
    """
    从视频源获取图像
    
    Args:
        source: 视频源，可以是：
            - 0: 本地摄像头
            - rtsp://...: RTSP 流地址
            - 文件路径: 视频文件
            
    Returns:
        numpy array 格式的图像
    """
    cap = cv2.VideoCapture(source)
    
    if not cap.isOpened():
        raise ValueError(f"无法打开视频源: {source}")
    
    ret, frame = cap.read()
    cap.release()
    
    if not ret:
        raise ValueError("无法读取视频帧")
    
    # BGR 转 RGB
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    return frame

def preprocess_image(image, target_size=(224, 224)):
    """
    预处理图像以适配 PyTorch 模型
    
    Args:
        image: numpy array 格式的图像
        target_size: 目标尺寸 (width, height)
        
    Returns:
        预处理后的 numpy array
    """
    # 调整大小
    if image.shape[:2] != target_size[::-1]:  # OpenCV 使用 (height, width)
        image = cv2.resize(image, target_size)
    
    return image

def image_to_tensor(image, normalize=True):
    """
    将图像转换为 PyTorch tensor
    
    Args:
        image: numpy array 格式的图像 (H, W, C)
        normalize: 是否进行标准化
        
    Returns:
        PyTorch tensor (C, H, W)
    """
    # 确保图像是 uint8 类型
    if image.dtype != np.uint8:
        image = (image * 255).astype(np.uint8)
    
    # 转换为 PIL Image
    pil_image = Image.fromarray(image)
    
    # 定义变换
    transform_list = [transforms.ToTensor()]
    
    if normalize:
        transform_list.append(
            transforms.Normalize(mean=[0.485, 0.456, 0.406], 
                               std=[0.229, 0.224, 0.225])
        )
    
    transform = transforms.Compose(transform_list)
    
    # 应用变换
    tensor = transform(pil_image)
    
    return tensor

def tensor_to_image(tensor, denormalize=True):
    """
    将 PyTorch tensor 转换回图像
    
    Args:
        tensor: PyTorch tensor (C, H, W) 或 (B, C, H, W)
        denormalize: 是否反标准化
        
    Returns:
        numpy array 格式的图像
    """
    # 如果有 batch 维度，取第一个
    if tensor.dim() == 4:
        tensor = tensor[0]
    
    # 确保在 CPU 上
    tensor = tensor.cpu()
    
    # 反标准化
    if denormalize:
        mean = torch.tensor([0.485, 0.456, 0.406]).view(3, 1, 1)
        std = torch.tensor([0.229, 0.224, 0.225]).view(3, 1, 1)
        tensor = tensor * std + mean
    
    # 限制范围到 [0, 1]
    tensor = torch.clamp(tensor, 0, 1)
    
    # 转换为 numpy
    image = tensor.numpy()
    
    # 转换维度顺序：(C, H, W) -> (H, W, C)
    image = np.transpose(image, (1, 2, 0))
    
    # 转换为 uint8
    image = (image * 255).astype(np.uint8)
    
    return image

def batch_preprocess(images, target_size=(224, 224), normalize=True):
    """
    批量预处理图像
    
    Args:
        images: 图像列表（numpy arrays）
        target_size: 目标尺寸
        normalize: 是否标准化
        
    Returns:
        PyTorch tensor (B, C, H, W)
    """
    tensors = []
    
    for image in images:
        # 预处理
        image = preprocess_image(image, target_size)
        # 转换为 tensor
        tensor = image_to_tensor(image, normalize)
        tensors.append(tensor)
    
    # 堆叠为 batch
    batch = torch.stack(tensors)
    
    return batch

class VideoCapture:
    """增强的视频捕获类，支持 PyTorch"""
    
    def __init__(self, source, transform=None):
        """
        Args:
            source: 视频源
            transform: torchvision transform（可选）
        """
        self.source = source
        self.transform = transform
        self.cap = cv2.VideoCapture(source)
        
        if not self.cap.isOpened():
            raise ValueError(f"无法打开视频源: {source}")
    
    def read(self):
        """读取一帧"""
        ret, frame = self.cap.read()
        
        if not ret:
            return None
        
        # BGR 转 RGB
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        return frame
    
    def read_tensor(self):
        """读取一帧并转换为 tensor"""
        frame = self.read()
        
        if frame is None:
            return None
        
        # 转换为 PIL Image
        pil_image = Image.fromarray(frame)
        
        # 应用变换
        if self.transform:
            tensor = self.transform(pil_image)
        else:
            tensor = transforms.ToTensor()(pil_image)
        
        return tensor
    
    def release(self):
        """释放资源"""
        self.cap.release()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()

# 兼容性函数（保持与原代码的接口一致）
def cv_resize(image, width, height):
    """
    调整图像大小（兼容性函数）
    
    Args:
        image: numpy array 格式的图像
        width: 目标宽度
        height: 目标高度
        
    Returns:
        调整大小后的图像
    """
    return cv2.resize(image, (width, height))

# 测试代码
if __name__ == "__main__":
    # 测试从摄像头获取图像
    try:
        # 获取图像
        img = get_image(0)  # 使用本地摄像头
        print(f"图像形状: {img.shape}")
        
        # 预处理
        img_processed = preprocess_image(img)
        print(f"预处理后形状: {img_processed.shape}")
        
        # 转换为 tensor
        tensor = image_to_tensor(img_processed)
        print(f"Tensor 形状: {tensor.shape}")
        
        # 转换回图像
        img_back = tensor_to_image(tensor)
        print(f"转换回图像形状: {img_back.shape}")
        
        # 显示图像
        import matplotlib.pyplot as plt
        fig, axes = plt.subplots(1, 2, figsize=(10, 5))
        axes[0].imshow(img)
        axes[0].set_title("原始图像")
        axes[1].imshow(img_back)
        axes[1].set_title("处理后图像")
        plt.show()
        
    except Exception as e:
        print(f"错误: {e}")