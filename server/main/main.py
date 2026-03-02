import asyncio
import matplotlib.pyplot as plt
import torch
from tools.camera import get_image, preprocess_image
from doubao import get_msg, get_audio
from tools.modelpredict import predict_image  
from playsoundtest import play_audio_list
from merge import merge_audio_files
from TTSWebSocketDemo import filter_markdown_special_chars
from model.chatdoubaollm import ChatDoubaoLM
from langchain.agents import initialize_agent, AgentType, AgentExecutor, create_openai_tools_agent, Tool

Doubaollm = ChatDoubaoLM(
    model_name="doubao-1-5-pro-32k-250115",
    temperature=0.7,
)

tmp_file = "./main/tmp_image.jpg"

# 设置 PyTorch 设备
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"使用设备: {device}")

async def generate(url="rtsp://192.168.144.25:8554/main.264", target_width=224, target_height=224, audio_path="main/audio"):
    """
    主要生成函数
    
    Args:
        url: 视频源 URL 或摄像头索引
        target_width: 目标图像宽度
        target_height: 目标图像高度
        audio_path: 音频保存路径
    """
    global tmp_file
    
    try:
        # 获取图像
        img = get_image(url)
        
        # 预处理图像
        img_array = preprocess_image(img, target_size=(target_width, target_height))
        
        # 保存临时图像
        plt.imsave(tmp_file, img_array)
        await asyncio.sleep(1.)
        
        # 使用 PyTorch 模型预测
        label, scores = await predict_image(img_array)
        print(f"预测结果: {label}, 置信度: {scores}")
        
        # 检查是否检测到地标建筑
        if label.startswith("others"):
            return "没有检测到地标建筑。"
        
        # 生成介绍文本
        msg = await get_msg(label)
        
        # 限制文本长度
        msg = msg[:250]
        msg = await filter_markdown_special_chars(msg)
        
        # 保存介绍文本
        with open("./main/introduction.txt", "w", encoding='utf-8') as f:
            f.write(msg)
        
        # 生成音频文件
        audio_files = await get_audio(msg, audio_path)
        
        # 合并音频文件
        await merge_audio_files(audio_files, f"{audio_path}/audio.mp3")
        
        return audio_files
        
    except Exception as e:
        print(f"生成过程中出错: {e}")
        raise e

async def batch_generate(urls, target_width=224, target_height=224, audio_base_path="main/audio"):
    """
    批量处理多个视频源
    
    Args:
        urls: 视频源 URL 列表
        target_width: 目标图像宽度
        target_height: 目标图像高度
        audio_base_path: 音频基础保存路径
    """
    results = []
    
    for i, url in enumerate(urls):
        print(f"\n处理第 {i+1}/{len(urls)} 个视频源: {url}")
        audio_path = f"{audio_base_path}/source_{i}"
        
        try:
            result = await generate(url, target_width, target_height, audio_path)
            results.append({
                'url': url,
                'status': 'success',
                'audio_files': result
            })
        except Exception as e:
            results.append({
                'url': url,
                'status': 'failed',
                'error': str(e)
            })
            
    return results

def test_pytorch_setup():
    """测试 PyTorch 环境设置"""
    print("PyTorch 环境测试:")
    print(f"PyTorch 版本: {torch.__version__}")
    print(f"CUDA 可用: {torch.cuda.is_available()}")
    
    if torch.cuda.is_available():
        print(f"CUDA 版本: {torch.version.cuda}")
        print(f"GPU 设备: {torch.cuda.get_device_name(0)}")
        print(f"GPU 数量: {torch.cuda.device_count()}")
    
    # 测试简单的张量操作
    x = torch.randn(3, 3)
    if torch.cuda.is_available():
        x = x.to('cuda')
        print(f"\n在 GPU 上创建的张量设备: {x.device}")
    else:
        print(f"\n在 CPU 上创建的张量设备: {x.device}")

async def continuous_monitoring(url, interval=5, target_width=224, target_height=224, audio_path="main/audio"):
    """
    持续监控视频源
    
    Args:
        url: 视频源 URL
        interval: 检测间隔（秒）
        target_width: 目标图像宽度
        target_height: 目标图像高度
        audio_path: 音频保存路径
    """
    print(f"开始持续监控，检测间隔: {interval} 秒")
    
    while True:
        try:
            print(f"\n执行检测...")
            result = await generate(url, target_width, target_height, audio_path)
            
            if result != "没有检测到地标建筑。":
                print("检测到地标建筑，播放介绍音频")
                await play_audio_list()
            
            # 等待指定间隔
            await asyncio.sleep(interval)
            
        except KeyboardInterrupt:
            print("\n监控已停止")
            break
        except Exception as e:
            print(f"监控过程中出错: {e}")
            await asyncio.sleep(interval)

if __name__ == "__main__":
    # 测试 PyTorch 环境
    test_pytorch_setup()
    
    # 运行主程序
    # 使用本地摄像头测试
    asyncio.run(generate(0))
    
    # 使用 RTSP 流测试
    # asyncio.run(generate("rtsp://192.168.144.25:8554/main.264"))
    
    # 持续监控模式
    # asyncio.run(continuous_monitoring(0, interval=10))