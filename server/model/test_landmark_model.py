# test_landmark_model.py - 测试地标识别模型
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
        
        print("\n所有类别的预测概率:")
        for i, (label, prob) in enumerate(predictions):
            label_name = label.replace("_0", "")
            print(f"  {i+1}. {label_name}: {prob:.4f}")
            
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        
def test_with_real_image(image_path):
    """使用真实图像测试"""
    print(f"\n使用真实图像测试: {image_path}")
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
        print("\n提示: 可以使用真实图像测试")
        print("用法: python test_landmark_model.py <图像路径>")
