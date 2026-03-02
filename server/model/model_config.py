import os
import torch
from pathlib import Path
import datetime

class ModelConfig:
    """模型配置管理类"""
    
    # 默认模型路径
    DEFAULT_MODEL_DIR = "./models"
    DEFAULT_MODEL_NAME = "landmark_classifier.pth"
    
    # 不同类型模型的路径配置
    MODEL_PATHS = {
        "production": "./models/landmark_classifier.pth",           # 生产环境模型
        "best": "./checkpoints/best_model.pth",                    # 训练得到的最佳模型
        "latest": "./checkpoints/latest_checkpoint.pth",           # 最新检查点
        "quantized": "./models/landmark_classifier_quantized.pth", # 量化模型
        "onnx": "./models/landmark_classifier.onnx",              # ONNX 格式
        "torchscript": "./models/landmark_classifier_traced.pt"   # TorchScript 格式
    }
    
    @staticmethod
    def get_model_path(model_type="production"):
        """
        获取模型路径
        
        Args:
            model_type: 模型类型 (production, best, latest, quantized, onnx, torchscript)
            
        Returns:
            模型文件的完整路径
        """
        if model_type in ModelConfig.MODEL_PATHS:
            return ModelConfig.MODEL_PATHS[model_type]
        else:
            # 如果类型不存在，返回默认路径
            return os.path.join(ModelConfig.DEFAULT_MODEL_DIR, ModelConfig.DEFAULT_MODEL_NAME)
    
    @staticmethod
    def find_latest_checkpoint(checkpoint_dir="./checkpoints"):
        """
        查找最新的检查点文件
        
        Args:
            checkpoint_dir: 检查点目录
            
        Returns:
            最新检查点的路径，如果没有找到则返回 None
        """
        checkpoint_dir = Path(checkpoint_dir)
        if not checkpoint_dir.exists():
            return None
            
        # 查找所有 .pth 文件
        checkpoints = list(checkpoint_dir.glob("*.pth"))
        
        if not checkpoints:
            return None
            
        # 按修改时间排序，返回最新的
        latest = max(checkpoints, key=lambda p: p.stat().st_mtime)
        return str(latest)
    
    @staticmethod
    def setup_model_directory():
        """创建必要的模型目录结构"""
        directories = [
            "./models",
            "./checkpoints",
            "./models/backups",
            "./models/experiments"
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
            print(f"确保目录存在: {directory}")
    
    @staticmethod
    def verify_model_path(model_path):
        """
        验证模型路径是否有效
        
        Args:
            model_path: 模型文件路径
            
        Returns:
            (is_valid, message): 是否有效和相关信息
        """
        if not os.path.exists(model_path):
            return False, f"模型文件不存在: {model_path}"
        
        if not model_path.endswith(('.pth', '.pt', '.onnx')):
            return False, f"不支持的文件格式: {model_path}"
        
        # 检查文件大小
        file_size = os.path.getsize(model_path) / (1024 * 1024)  # MB
        if file_size < 1:
            return False, f"模型文件太小 ({file_size:.2f} MB)，可能已损坏"
        
        # 尝试加载模型以验证
        try:
            if model_path.endswith(('.pth', '.pt')):
                # 只加载到 CPU 进行验证
                checkpoint = torch.load(model_path, map_location='cpu')
                
                # 检查是否包含必要的键
                if isinstance(checkpoint, dict):
                    if 'model_state_dict' not in checkpoint and 'state_dict' not in checkpoint:
                        # 可能直接是 state_dict
                        pass
                
            return True, f"模型验证成功: {model_path} ({file_size:.2f} MB)"
            
        except Exception as e:
            return False, f"无法加载模型: {str(e)}"

# 更新后的 inference_server.py 相关部分
def load_model_with_config():
    """使用配置加载模型"""
    from tools.modelpredict import ImageClassifier
    
    # 1. 设置模型目录
    ModelConfig.setup_model_directory()
    
    # 2. 确定模型路径（按优先级尝试）
    model_path = None
    
    # 优先级 1: 环境变量
    env_model_path = os.environ.get('MODEL_PATH')
    if env_model_path and os.path.exists(env_model_path):
        model_path = env_model_path
        print(f"使用环境变量指定的模型: {model_path}")
    
    # 优先级 2: 最新的检查点
    if not model_path:
        latest_checkpoint = ModelConfig.find_latest_checkpoint()
        if latest_checkpoint:
            model_path = latest_checkpoint
            print(f"使用最新检查点: {model_path}")
    
    # 优先级 3: 最佳模型
    if not model_path:
        best_model_path = ModelConfig.get_model_path("best")
        if os.path.exists(best_model_path):
            model_path = best_model_path
            print(f"使用最佳模型: {model_path}")
    
    # 优先级 4: 生产模型
    if not model_path:
        prod_model_path = ModelConfig.get_model_path("production")
        if os.path.exists(prod_model_path):
            model_path = prod_model_path
            print(f"使用生产模型: {model_path}")
    
    # 优先级 5: 默认路径
    if not model_path:
        model_path = os.path.join(ModelConfig.DEFAULT_MODEL_DIR, ModelConfig.DEFAULT_MODEL_NAME)
        print(f"使用默认模型路径: {model_path}")
    
    # 3. 验证模型路径
    is_valid, message = ModelConfig.verify_model_path(model_path)
    if not is_valid:
        print(f"错误: {message}")
        print("提示: 请先训练模型或下载预训练模型")
        return None
    
    print(message)
    
    # 4. 加载模型
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = ImageClassifier(model_path=model_path, device=device)
    
    return model

# 示例：如何在训练后保存模型
def save_trained_model(model, save_type="production"):
    """
    保存训练好的模型
    
    Args:
        model: PyTorch 模型
        save_type: 保存类型
    """
    save_path = ModelConfig.get_model_path(save_type)
    
    # 创建目录
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    label2name = {
        "zhulou":"一校区主楼",
        "xiaobulou":"校部楼",
        "xingzhenglou":"行政楼",
        "hangtianguan":"科学园航天馆",
        "xiaobowuguan":"校部楼",
        "tushuguan":"一校区图书馆",
        "wozhencangqiong":"科学园卧震苍穹",        
    }
    
    # 保存模型
    checkpoint = {
        'model_state_dict': model.state_dict(),
        'model_config': {
            'num_classes': model.fc.out_features if hasattr(model, 'fc') else 8,
            'architecture': model.__class__.__name__,
            'input_size': [224, 224, 3]
        },
        'labels': list(label2name.keys()),  # 保存标签信息
        'timestamp': str(datetime.now())
    }
    
    torch.save(checkpoint, save_path)
    print(f"模型已保存到: {save_path}")

# 示例：如何使用不同的模型
if __name__ == "__main__":
    # 设置模型目录
    ModelConfig.setup_model_directory()
    
    # 显示所有配置的模型路径
    print("配置的模型路径:")
    for model_type, path in ModelConfig.MODEL_PATHS.items():
        exists = "✓" if os.path.exists(path) else "✗"
        print(f"  {model_type}: {path} [{exists}]")
    
    # 查找最新检查点
    latest = ModelConfig.find_latest_checkpoint()
    if latest:
        print(f"\n最新检查点: {latest}")
    
    # 验证特定模型
    test_path = "./models/landmark_classifier.pth"
    is_valid, message = ModelConfig.verify_model_path(test_path)
    print(f"\n验证 {test_path}: {message}")