import torch
import torch.nn as nn
from torchvision import models
import os
import shutil
from pathlib import Path

def adapt_existing_resnet50(existing_model_path, num_classes=8, save_path="./models/landmark_classifier.pth"):
    """
    适配现有的 ResNet50 模型用于地标识别
    
    Args:
        existing_model_path: 现有 ResNet50 模型的路径
        num_classes: 目标类别数（哈工大地标为 8 类）
        save_path: 保存适配后模型的路径
    """
    print(f"加载现有模型: {existing_model_path}")
    
    # 检查文件是否存在
    if not os.path.exists(existing_model_path):
        raise FileNotFoundError(f"找不到模型文件: {existing_model_path}")
    
    # 尝试加载现有模型
    try:
        # 情况 1: 模型是完整的 checkpoint（包含 state_dict）
        checkpoint = torch.load(existing_model_path, map_location='cpu')
        
        if isinstance(checkpoint, dict):
            print("检测到 checkpoint 格式")
            
            # 检查是否包含 state_dict
            if 'state_dict' in checkpoint:
                state_dict = checkpoint['state_dict']
            elif 'model_state_dict' in checkpoint:
                state_dict = checkpoint['model_state_dict']
            else:
                # 可能整个 checkpoint 就是 state_dict
                state_dict = checkpoint
                
            # 检查是否已经是 8 分类的模型
            if 'fc.weight' in state_dict and state_dict['fc.weight'].shape[0] == num_classes:
                print(f"模型已经适配为 {num_classes} 分类，直接使用")
                
                # 创建保存目录
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                
                # 保存为标准格式
                new_checkpoint = {
                    'model_state_dict': state_dict,
                    'model_config': {
                        'num_classes': num_classes,
                        'architecture': 'ResNet50',
                        'input_size': [224, 224, 3]
                    },
                    'labels': ['zhulou', 'xiaobulou', 'xingzhenglou', 'hangtianguan', 
                              'xiaobowuguan', 'tushuguan', 'wozhencangqiong', 'others'],
                    'training_completed': True
                }
                
                torch.save(new_checkpoint, save_path)
                print(f"模型已保存到: {save_path}")
                return
                
        else:
            # 情况 2: 直接是 state_dict
            state_dict = checkpoint
            
    except Exception as e:
        print(f"加载模型时出错: {e}")
        print("尝试作为 torchvision 预训练模型处理...")
        
        # 情况 3: 可能是标准的 torchvision 模型
        model = models.resnet50(pretrained=False)
        model.load_state_dict(torch.load(existing_model_path, map_location='cpu'))
        state_dict = model.state_dict()
    
    # 创建新的 ResNet50 模型
    print(f"创建新的 ResNet50 模型，输出类别数: {num_classes}")
    new_model = models.resnet50(pretrained=False)
    
    # 加载除了最后一层之外的所有权重
    # 获取原始 fc 层的输入特征数
    num_ftrs = new_model.fc.in_features
    
    # 替换最后的全连接层
    new_model.fc = nn.Linear(num_ftrs, num_classes)
    
    # 加载预训练权重（除了 fc 层）
    pretrained_dict = {k: v for k, v in state_dict.items() if not k.startswith('fc.')}
    model_dict = new_model.state_dict()
    model_dict.update(pretrained_dict)
    new_model.load_state_dict(model_dict, strict=False)
    
    print("已加载预训练权重（除了最后的分类层）")
    
    # 初始化新的 fc 层
    nn.init.xavier_uniform_(new_model.fc.weight)
    nn.init.zeros_(new_model.fc.bias)
    print("已初始化新的分类层")
    
    # 保存适配后的模型
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    
    checkpoint = {
        'model_state_dict': new_model.state_dict(),
        'model_config': {
            'num_classes': num_classes,
            'architecture': 'ResNet50',
            'input_size': [224, 224, 3],
            'adapted_from': existing_model_path
        },
        'labels': ['zhulou', 'xiaobulou', 'xingzhenglou', 'hangtianguan', 
                  'xiaobowuguan', 'tushuguan', 'wozhencangqiong', 'others'],
        'training_completed': False,  # 标记为需要微调
        'note': '这是从预训练模型适配的，建议在目标数据集上进行微调'
    }
    
    torch.save(checkpoint, save_path)
    print(f"适配后的模型已保存到: {save_path}")
    print("\n注意: 最后的分类层是随机初始化的，需要在您的数据集上进行训练或微调！")
    
    return new_model

def check_resnet50_model(model_path):
    """
    检查 ResNet50 模型的详细信息
    
    Args:
        model_path: 模型文件路径
    """
    print(f"检查模型: {model_path}")
    print("-" * 60)
    
    try:
        # 加载模型
        checkpoint = torch.load(model_path, map_location='cpu')
        
        # 分析模型结构
        if isinstance(checkpoint, dict):
            # 查找 state_dict
            if 'state_dict' in checkpoint:
                state_dict = checkpoint['state_dict']
            elif 'model_state_dict' in checkpoint:
                state_dict = checkpoint['model_state_dict']
            else:
                state_dict = checkpoint
        else:
            state_dict = checkpoint
        
        # 检查是否是 ResNet50
        resnet50_layers = ['conv1.weight', 'layer1.0.conv1.weight', 'layer4.2.conv3.weight', 'fc.weight']
        is_resnet50 = all(layer in state_dict for layer in resnet50_layers[:-1])
        
        if is_resnet50:
            print("✓ 确认是 ResNet50 架构")
        else:
            print("⚠ 可能不是标准的 ResNet50 架构")
        
        # 检查 fc 层
        if 'fc.weight' in state_dict:
            fc_shape = state_dict['fc.weight'].shape
            print(f"✓ 全连接层输出维度: {fc_shape[0]}")
            print(f"✓ 全连接层输入维度: {fc_shape[1]}")
            
            if fc_shape[0] == 1000:
                print("  → 这是 ImageNet 预训练模型（1000 类）")
            elif fc_shape[0] == 8:
                print("  → 这已经是适配后的地标识别模型（8 类）")
            else:
                print(f"  → 自定义分类数: {fc_shape[0]}")
        
        # 显示所有层的信息
        print("\n模型层统计:")
        layer_types = {}
        for name, tensor in state_dict.items():
            layer_type = name.split('.')[0]
            if layer_type not in layer_types:
                layer_types[layer_type] = 0
            layer_types[layer_type] += 1
        
        for layer_type, count in sorted(layer_types.items()):
            print(f"  {layer_type}: {count} 个参数张量")
        
        # 计算模型大小
        total_params = sum(p.numel() for p in state_dict.values())
        print(f"\n总参数量: {total_params:,}")
        print(f"模型大小: ~{total_params * 4 / 1024 / 1024:.1f} MB (假设 float32)")
        
    except Exception as e:
        print(f"检查模型时出错: {e}")

def quick_setup(existing_model_path="resnet50_model"):
    """
    快速设置：使用现有的 ResNet50 模型
    
    Args:
        existing_model_path: 现有模型的路径
    """
    print("快速设置地标识别模型")
    print("=" * 60)
    
    # 1. 检查现有模型
    if not os.path.exists(existing_model_path):
        print(f"错误: 找不到模型文件 '{existing_model_path}'")
        print("\n请确保模型文件在正确的位置，或提供完整路径")
        return
    
    # 2. 检查模型信息
    print("\n步骤 1: 检查现有模型")
    check_resnet50_model(existing_model_path)
    
    # 3. 创建必要的目录
    print("\n步骤 2: 创建项目目录结构")
    directories = ["./models", "./checkpoints", "./data/landmarks/train", "./data/landmarks/val"]
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"  ✓ {directory}")
    
    # 4. 适配模型
    print("\n步骤 3: 适配模型用于地标识别")
    try:
        adapt_existing_resnet50(
            existing_model_path=existing_model_path,
            num_classes=8,
            save_path="./models/landmark_classifier.pth"
        )
    except Exception as e:
        print(f"适配模型时出错: {e}")
        return
    
    # 5. 创建测试脚本
    print("\n步骤 4: 创建测试脚本")
    test_script = '''# test_model.py - 测试模型是否正常工作
import torch
import numpy as np
from PIL import Image
from tools.modelpredict import predict_image

async def test():
    # 创建一个测试图像（224x224 的随机图像）
    test_image = np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8)
    
    # 预测
    label, confidence = await predict_image(test_image)
    print(f"测试预测结果: {label}, 置信度: {confidence:.4f}")
    print("模型加载成功！")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test())
'''
    
    with open("test_model.py", "w") as f:
        f.write(test_script)
    print("  ✓ 创建了 test_model.py")
    
    # 6. 下一步指引
    print("\n设置完成！")
    print("\n下一步操作：")
    print("1. 测试模型加载: python test_model.py")
    print("2. 准备训练数据放到 ./data/landmarks/ 目录")
    print("3. 微调模型: python train_pytorch.py")
    print("4. 启动推理服务: python inference_server.py")
    
    print("\n重要提示：")
    print("- 如果您的 resnet50_model 已经是 8 分类的，可以直接使用")
    print("- 如果是 ImageNet 预训练模型（1000 类），需要在您的数据上微调")
    print("- 微调时，可以冻结前面的层，只训练最后的分类层")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # 如果提供了模型路径作为参数
        model_path = sys.argv[1]
        quick_setup(model_path)
    else:
        # 使用默认路径
        print("使用方法:")
        print("python use_existing_resnet50.py [模型路径]")
        print("\n示例:")
        print("python use_existing_resnet50.py resnet50_model")
        print("python use_existing_resnet50.py ./path/to/your/model.pth")
        
        # 如果当前目录有 resnet50_model，直接使用
        if os.path.exists("resnet50_model"):
            print("\n检测到当前目录的 'resnet50_model'，开始设置...")
            quick_setup("resnet50_model")
        else:
            print("\n在当前目录未找到 'resnet50_model'")
            
            # 搜索可能的模型文件
            possible_models = list(Path(".").glob("*resnet50*.pth")) + \
                            list(Path(".").glob("*resnet50*.pt")) + \
                            list(Path(".").glob("resnet50_model"))
            
            if possible_models:
                print("\n找到可能的模型文件:")
                for i, model in enumerate(possible_models):
                    print(f"{i+1}. {model}")
                print("\n请使用: python use_existing_resnet50.py <模型路径>")