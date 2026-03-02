# check_and_setup_existing_model.py - 检查并设置现有的 resnet50_model

import torch
import torch.nn as nn
from torchvision import models
import os
import sys
import shutil
from datetime import datetime

# 添加模型目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

def analyze_model(model_path):
    """
    分析模型文件的详细信息
    """
    print(f"\n分析模型: {model_path}")
    print("=" * 70)

    if not os.path.exists(model_path):
        print(f"错误: 找不到模型文件 {model_path}")
        return None
        
    # 获取文件信息
    file_size = os.path.getsize(model_path) / (1024 * 1024)  # MB
    print(f"文件大小: {file_size:.2f} MB")
    
    try:
        # 尝试加载模型
        print("\n尝试加载模型...")
        checkpoint = torch.load(model_path, map_location='cpu')
        
        # 分析模型内容
        if isinstance(checkpoint, dict):
            print("✓ 模型是字典格式")
            print(f"  包含的键: {list(checkpoint.keys())}")
            
            # 查找 state_dict
            state_dict = None
            if 'state_dict' in checkpoint:
                state_dict = checkpoint['state_dict']
                print("  使用 'state_dict' 键")
            elif 'model_state_dict' in checkpoint:
                state_dict = checkpoint['model_state_dict']
                print("  使用 'model_state_dict' 键")
            elif 'model' in checkpoint:
                state_dict = checkpoint['model']
                print("  使用 'model' 键")
            else:
                # 检查是否直接是 state_dict
                first_key = list(checkpoint.keys())[0] if checkpoint else ''
                if 'conv' in first_key or 'fc' in first_key or 'layer' in first_key:
                    state_dict = checkpoint
                    print("  字典本身就是 state_dict")
                    
            # 检查其他信息
            if 'labels' in checkpoint:
                print(f"\n标签信息: {checkpoint['labels']}")
            if 'num_classes' in checkpoint:
                print(f"类别数: {checkpoint['num_classes']}")
            if 'model_config' in checkpoint:
                print(f"模型配置: {checkpoint['model_config']}")
                
        else:
            print("✓ 模型是直接的 state_dict 或其他格式")
            state_dict = checkpoint
            
        # 分析 state_dict
        if state_dict:
            print("\n分析模型结构:")
            
            # 检查是否是 ResNet50
            resnet_indicators = ['conv1.weight', 'layer1.0.conv1.weight', 'layer4.2.conv3.weight']
            is_resnet = all(key in state_dict for key in resnet_indicators)
            
            if is_resnet:
                print("✓ 确认是 ResNet 架构")
                
                # 检查 fc 层
                fc_key = None
                for key in ['fc.weight', 'classifier.weight', 'head.weight']:
                    if key in state_dict:
                        fc_key = key
                        break
                        
                if fc_key:
                    fc_shape = state_dict[fc_key].shape
                    num_classes = fc_shape[0]
                    print(f"✓ 输出类别数: {num_classes}")
                    
                    if num_classes == 1000:
                        print("  → 这是 ImageNet 预训练模型")
                        return {'type': 'imagenet', 'num_classes': 1000, 'state_dict': state_dict}
                    elif num_classes == 8:
                        print("  → 这是地标识别模型（8类）")
                        return {'type': 'landmark', 'num_classes': 8, 'state_dict': state_dict}
                    else:
                        print(f"  → 自定义分类模型（{num_classes}类）")
                        return {'type': 'custom', 'num_classes': num_classes, 'state_dict': state_dict}
                else:
                    print("⚠ 未找到全连接层")
                    
            else:
                print("⚠ 可能不是标准的 ResNet50 架构")
                
            # 显示一些层的信息
            print("\n部分层信息:")
            layer_count = 0
            for name, param in state_dict.items():
                if layer_count < 5:
                    print(f"  {name}: {list(param.shape)}")
                    layer_count += 1
                    
            total_params = sum(p.numel() for p in state_dict.values())
            print(f"\n总参数量: {total_params:,}")
            
        return {'type': 'unknown', 'checkpoint': checkpoint}
        
    except Exception as e:
        print(f"\n加载模型时出错: {e}")
        return None

def setup_landmark_model(source_path, model_info):
    """
    设置地标识别模型
    """
    target_path = "./models/landmark_classifier.pth"
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    
    print(f"\n设置地标识别模型...")
    
    if model_info['type'] == 'landmark' and model_info['num_classes'] == 8:
        # 已经是地标模型，直接复制
        print("模型已经是 8 类地标识别模型，直接使用")
        shutil.copy2(source_path, target_path)
        print(f"✓ 模型已复制到: {target_path}")
        
    elif model_info['type'] == 'imagenet':
        # ImageNet 模型，需要适配
        print("检测到 ImageNet 预训练模型，需要适配为 8 类")
        
        # 创建新模型
        model = models.resnet50(pretrained=False)
        
        # 加载预训练权重（除了 fc 层）
        state_dict = model_info['state_dict']
        pretrained_dict = {k: v for k, v in state_dict.items() if not k.startswith('fc.')}
        model_dict = model.state_dict()
        model_dict.update(pretrained_dict)
        model.load_state_dict(model_dict, strict=False)
        
        # 替换 fc 层
        num_ftrs = model.fc.in_features
        model.fc = nn.Linear(num_ftrs, 8)
        nn.init.xavier_uniform_(model.fc.weight)
        nn.init.zeros_(model.fc.bias)
        
        # 保存
        checkpoint = {
            'model_state_dict': model.state_dict(),
            'model_config': {
                'num_classes': 8,
                'architecture': 'ResNet50',
                'input_size': [224, 224, 3],
                'adapted_from': 'ImageNet'
            },
            'labels': ['zhulou', 'xiaobulou', 'xingzhenglou', 'hangtianguan', 
                      'xiaobowuguan', 'tushuguan', 'wozhencangqiong', 'others'],
            'timestamp': str(datetime.now()),
            'training_completed': False,
            'note': '从 ImageNet 预训练模型适配，需要在地标数据集上微调'
        }
        
        torch.save(checkpoint, target_path)
        print(f"✓ 适配后的模型已保存到: {target_path}")
        print("\n⚠ 注意: 最后一层是随机初始化的，需要训练！")
        
    else:
        print(f"未知的模型类型或自定义模型（{model_info.get('num_classes', '?')} 类）")
        print("将尝试直接使用...")
        shutil.copy2(source_path, target_path)
        
    return target_path

def create_test_script():
    """
    创建测试脚本
    """
    test_code = '''# test_landmark_model.py - 测试地标识别模型
import sys
import os
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

import asyncio
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
from tools.modelpredict import predict_image, ImageClassifier

async def test_model():
    """测试模型加载和预测"""
    print("测试地标识别模型...")
    print("-" * 50)
    
    # 创建测试图像（彩色随机图像）
    test_image = np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8)
    
    try:
        # 测试预测
        label, confidence = await predict_image(test_image)
        print(f"✓ 模型加载成功！")
        print(f"  预测结果: {label}")
        print(f"  置信度: {confidence:.4f}")
        
        # 显示所有类别
        classifier = ImageClassifier(model_path="./models/landmark_classifier.pth")
        predictions = classifier.predict_top_k(test_image, k=8)
        
        print("\\n所有类别的预测概率:")
        for i, (label, prob) in enumerate(predictions):
            label_name = label.replace("_0", "")
            print(f"  {i+1}. {label_name}: {prob:.4f}")
            
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        
def test_with_real_image(image_path):
    """使用真实图像测试"""
    print(f"\\n使用真实图像测试: {image_path}")
    print("-" * 50)
    
    try:
        # 加载图像
        image = Image.open(image_path).convert('RGB')
        image_array = np.array(image)
        
        # 预测
        import asyncio
        from tools.modelpredict import predict_image
        
        async def predict():
            return await predict_image(image_array)
            
        label, confidence = asyncio.run(predict())
        
        print(f"预测结果: {label}")
        print(f"置信度: {confidence:.4f}")
        
        # 显示图像和预测结果
        plt.figure(figsize=(8, 6))
        plt.imshow(image)
        plt.title(f"预测: {label} (置信度: {confidence:.2%})")
        plt.axis('off')
        plt.show()
        
    except Exception as e:
        print(f"测试失败: {e}")

if __name__ == "__main__":
    # 运行基础测试
    asyncio.run(test_model())
    
    # 如果提供了图像路径，进行真实图像测试
    if len(sys.argv) > 1:
        test_with_real_image(sys.argv[1])
    else:
        print("\\n提示: 可以使用真实图像测试")
        print("用法: python test_landmark_model.py <图像路径>")
'''
    
    with open("test_landmark_model.py", "w", encoding='utf-8') as f:
        f.write(test_code)
    print("✓ 创建了测试脚本: test_landmark_model.py")

def main():
    """主函数"""
    print("ResNet50 模型设置工具")
    print("=" * 70)
    
    # 查找模型文件
    model_path = "./model/resnet50_model.pth"
    
    if not os.path.exists(model_path):
        print(f"错误: 找不到模型文件 {model_path}")
        # 尝试其他可能的路径
        alternative_paths = [
            "resnet50_model",
            "./resnet50_model",
            "../model/resnet50_model",
            "./model/resnet50_model.pth",
            "./model/resnet50_model.pt"
        ]
        
        for alt_path in alternative_paths:
            if os.path.exists(alt_path):
                model_path = alt_path
                print(f"找到模型文件: {model_path}")
                break
        else:
            print("未找到 resnet50_model 文件")
            return
    
    # 分析模型
    model_info = analyze_model(model_path)
    
    if model_info:
        # 设置模型
        target_path = setup_landmark_model(model_path, model_info)
        
        # 创建测试脚本
        create_test_script()
        
        # 创建必要的目录
        print("\n创建项目目录结构...")
        directories = [
            "./models",
            "./checkpoints", 
            "./tools",
            "./data/landmarks/train",
            "./data/landmarks/val"
        ]
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
            print(f"  ✓ {directory}")
        
        print("\n设置完成！")
        print("\n下一步操作:")
        print("1. 测试模型: python test_landmark_model.py")
        print("2. 启动推理服务: python inference_server.py")
        
        if model_info.get('type') == 'imagenet' or not model_info.get('training_completed', True):
            print("3. 训练/微调模型: python train.py")
            print("\n⚠ 重要: 模型需要在地标数据集上训练才能正确识别！")

if __name__ == "__main__":
    main()