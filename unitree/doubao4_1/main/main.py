import asyncio
import numpy as np
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import matplotlib.pyplot as plt
from pathlib import Path

# 模块导入
from main.camera import CameraManager
from main.doubao import get_msg, get_audio
from main.modelpredict import PredictionManager
from main.merge import merge_audio_files
from main.TTSWebSocketDemo import filter_markdown_special_chars
from main.params import VOTE_COUNT, TMP_IMAGE, CONSENSUS_THRESHOLD, INTRO_FILE, AUDIO_DIR,CONFIDENCE_THRESHOLD
# 初始化管理器
camera_manager = CameraManager()
predictor = PredictionManager()


class RecognitionSystem:
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=4)

    async def capture_and_predict(self, url):
        """并发捕获多帧并进行预测"""
        # 获取多帧图像
        frames = camera_manager.get_images(url, k=VOTE_COUNT)
        if not frames or len(frames) != VOTE_COUNT:
            raise ValueError(
                f"获取图像失败，实际获取 {len(frames) if frames else 0} 帧"
            )

        # 预处理图像
        img_arrays = [camera_manager.preprocess_image(frame) for frame in frames]

        # 保存最后一帧用于调试
        plt.imsave(TMP_IMAGE, frames[-1])

        # 并发预测
        loop = asyncio.get_event_loop()
        tasks = [
            loop.run_in_executor(
                self.executor, lambda img=img: asyncio.run(predictor.predict_image(img))
            )
            for img in img_arrays
        ]
        return await asyncio.gather(*tasks)

    @staticmethod
    def evaluate_results(results):
        """评估预测结果"""
        if not results:
            return "others_0", 0.0

        labels = [r[0] for r in results if r]
        confidences = [r[1] for r in results if r]

        if not labels:
            return "others_0", 0.0

        counter = Counter(labels)
        most_common = counter.most_common(1)[0]

        # 计算相同标签的平均置信度
        avg_conf = np.mean(
            [c for l, c in zip(labels, confidences) if l == most_common[0]]
        )

        if most_common[1] >= CONSENSUS_THRESHOLD and avg_conf >= CONFIDENCE_THRESHOLD:
            return most_common[0], avg_conf

        return "others_0", max(confidences)


async def generate(url="rtsp://192.168.144.25:8554/main.264"):
    """主处理流程"""
    system = RecognitionSystem()

    try:
        # 1. 图像捕获与识别
        results = await system.capture_and_predict(url)
        print(f"原始预测结果: {results}")

        # 2. 结果评估
        label, confidence = system.evaluate_results(results)
        print(f"最终识别: {label} (置信度: {confidence:.2f})")

        # 3. 处理识别结果
        if label == "others_0":
            return "没有检测到地标建筑"

        # 4. 生成解说
        msg = await get_msg(label)
        msg = await filter_markdown_special_chars(msg[:250])  # 限制长度并过滤特殊字符

        INTRO_FILE.write_text(msg, encoding="utf-8")

        # 5. 生成音频
        audio_files = await get_audio(msg, str(AUDIO_DIR))
        merge_audio_files(audio_files, str(AUDIO_DIR / "audio.mp3"))

        return {
            "status": "success",
            "label": label,
            "confidence": float(confidence),
            "audio_files": audio_files,
        }

    except Exception as e:
        print(f"处理失败: {str(e)}")
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    # 测试流程
    async def test():
        result = await generate(0)  # 使用本地摄像头测试
        print("测试结果:", result)

    asyncio.run(test())
