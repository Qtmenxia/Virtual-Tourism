import torch
import torch.nn as nn
from flask import Flask, request, jsonify
import numpy as np
from PIL import Image
import io
import base64
import time
from tools.modelpredict import ImageClassifier

app = Flask(__name__)

# 全局模型实例
model = None
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

def load_model():
    """加载 PyTorch 模型"""
    global model
    model = ImageClassifier(
        model_path='./models/landmark_classifier.pth',
        device=device
    )
    print(f"模型已加载到 {device}")

@app.route('/predict', methods=['POST'])
def predict():
    """图像预测端点"""
    try:
        # 获取图像数据
        data = request.json
        
        if 'image' not in data:
            return jsonify({'error': '未提供图像数据'}), 400
        
        # 解码 base64 图像
        image_data = base64.b64decode(data['image'])
        image = Image.open(io.BytesIO(image_data))
        
        # 转换为 numpy array
        image_array = np.array(image)
        
        # 预测
        start_time = time.time()
        label, confidence = model.predict(image_array)
        inference_time = time.time() - start_time
        
        # 获取 top-k 预测（如果请求）
        top_k = data.get('top_k', 1)
        if top_k > 1:
            predictions = model.predict_top_k(image_array, k=top_k)
            result = {
                'predictions': [
                    {'label': label, 'confidence': float(conf)}
                    for label, conf in predictions
                ],
                'inference_time': inference_time
            }
        else:
            result = {
                'label': label,
                'confidence': float(confidence),
                'inference_time': inference_time
            }
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/predict_batch', methods=['POST'])
def predict_batch():
    """批量图像预测端点"""
    try:
        data = request.json
        
        if 'images' not in data:
            return jsonify({'error': '未提供图像数据'}), 400
        
        results = []
        total_time = 0
        
        for img_data in data['images']:
            # 解码图像
            image_data = base64.b64decode(img_data)
            image = Image.open(io.BytesIO(image_data))
            image_array = np.array(image)
            
            # 预测
            start_time = time.time()
            label, confidence = model.predict(image_array)
            inference_time = time.time() - start_time
            total_time += inference_time
            
            results.append({
                'label': label,
                'confidence': float(confidence)
            })
        
        return jsonify({
            'results': results,
            'total_inference_time': total_time,
            'average_inference_time': total_time / len(results)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/model_info', methods=['GET'])
def model_info():
    """获取模型信息"""
    if model is None:
        return jsonify({'error': '模型未加载'}), 500
    
    info = {
        'device': str(device),
        'model_type': model.model.__class__.__name__,
        'num_classes': model.num_classes,
        'input_size': [224, 224],
        'pytorch_version': torch.__version__,
        'cuda_available': torch.cuda.is_available()
    }
    
    if torch.cuda.is_available():
        info['gpu_name'] = torch.cuda.get_device_name(0)
        info['gpu_memory'] = {
            'allocated': torch.cuda.memory_allocated(0) / 1024**2,  # MB
            'reserved': torch.cuda.memory_reserved(0) / 1024**2     # MB
        }
    
    return jsonify(info)

@app.route('/health', methods=['GET'])
def health():
    """健康检查端点"""
    return jsonify({
        'status': 'healthy',
        'model_loaded': model is not None,
        'device': str(device)
    })

# PyTorch 模型优化工具
class ModelOptimizer:
    """PyTorch 模型优化器"""
    
    @staticmethod
    def quantize_model(model, dtype=torch.qint8):
        """量化模型以减少内存使用"""
        model.eval()
        quantized_model = torch.quantization.quantize_dynamic(
            model,
            {nn.Linear, nn.Conv2d},
            dtype=dtype
        )
        return quantized_model
    
    @staticmethod
    def export_onnx(model, dummy_input, output_path):
        """导出模型为 ONNX 格式"""
        model.eval()
        torch.onnx.export(
            model,
            dummy_input,
            output_path,
            export_params=True,
            opset_version=11,
            do_constant_folding=True,
            input_names=['input'],
            output_names=['output'],
            dynamic_axes={
                'input': {0: 'batch_size'},
                'output': {0: 'batch_size'}
            }
        )
        print(f"模型已导出到: {output_path}")
    
    @staticmethod
    def trace_model(model, example_input):
        """使用 TorchScript 追踪模型"""
        model.eval()
        traced_model = torch.jit.trace(model, example_input)
        return traced_model
    
    @staticmethod
    def optimize_for_inference(model):
        """优化模型用于推理"""
        model.eval()
        
        # 禁用梯度计算
        for param in model.parameters():
            param.requires_grad = False
        
        # 如果在 CUDA 上，启用 cudnn 优化
        if next(model.parameters()).is_cuda:
            torch.backends.cudnn.benchmark = True
        
        return model

# 性能监控
class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self):
        self.inference_times = []
        self.request_count = 0
        
    def record_inference(self, time):
        """记录推理时间"""
        self.inference_times.append(time)
        self.request_count += 1
        
        # 只保留最近 1000 次的记录
        if len(self.inference_times) > 1000:
            self.inference_times.pop(0)
    
    def get_stats(self):
        """获取统计信息"""
        if not self.inference_times:
            return {}
        
        times = np.array(self.inference_times)
        return {
            'total_requests': self.request_count,
            'average_time': float(np.mean(times)),
            'min_time': float(np.min(times)),
            'max_time': float(np.max(times)),
            'p50_time': float(np.percentile(times, 50)),
            'p90_time': float(np.percentile(times, 90)),
            'p99_time': float(np.percentile(times, 99))
        }

# 创建性能监控器实例
perf_monitor = PerformanceMonitor()

@app.route('/stats', methods=['GET'])
def stats():
    """获取性能统计"""
    return jsonify(perf_monitor.get_stats())

if __name__ == '__main__':
    # 加载模型
    load_model()
    
    # 运行服务器
    app.run(host='0.0.0.0', port=5001, debug=False)