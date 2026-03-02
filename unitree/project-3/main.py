import cv2
import threading
import os
import shutil
import time
import video_preprocessing
import image_classification
import information_retrieval
import texttospeech
import numpy as np

# RTSP 流地址
rtsp_url = "rtsp://192.168.144.25:8554/main.264"

def main(vr_interaction_obj=None, stop_event=None):
    deepseek_api_key = "sk-7bbd9bd7ae0c46f58f7c5e9413c425ab"

    cap = cv2.VideoCapture(rtsp_url)

    if not cap.isOpened():
        print("无法打开 RTSP 流")
        exit()

    frame_count = 0
    image_count = 0
    frame_interval = 30  # 每30帧取一帧
    images = []
    temp_folder = "temp_images"  # 临时文件夹
    os.makedirs(temp_folder, exist_ok=True)  # 确保文件夹存在

    previous_class = None  # 用于存储上一次的分类结果

    while True:
        # 检查是否收到停止信号
        if stop_event is not None and stop_event.is_set():
            break

        ret, frame = cap.read()
        if not ret:
            print("无法读取帧")
            break

        frame_count += 1
        if frame_count % frame_interval != 0:
            continue

        # 保存图像到临时文件夹
        img_index = (frame_count // frame_interval) - 1  # 计算图像索引
        img_path = os.path.join(temp_folder, f"image_{img_index}.jpg")
        cv2.imwrite(img_path, frame)

        print(f"已保存图像: {img_path}")

        image_count += 1  # 增加计数器

        # 当保存满5张图像时进行预测
        if image_count >= 5:
            class_names, confidences = image_classification.classify_images(temp_folder)

            # 打印所有预测结果
            for i, (cls, conf) in enumerate(zip(class_names, confidences)):
                print(f'Image {i}: {cls} (Confidence: {conf:.4f})')

            # 检查是否所有预测结果相同且平均置信度超过90%
            if all(c == class_names[0] for c in class_names) and np.mean(confidences) > 0.9:
                predicted_class = class_names[0]
                print(f"一致分类结果: {predicted_class}，平均置信度: {np.mean(confidences):.4f}")

                # 如果本次分类结果与上次相同，则跳过后续处理
                if previous_class == predicted_class:
                    print("本次分类结果与上次相同，重新监测中...")
                    # 清空图像列表并删除临时文件夹中的图像
                    images = []
                    for img_file in os.listdir(temp_folder):
                        os.remove(os.path.join(temp_folder, img_file))
                    print("已清空临时文件夹")
                    continue  # 跳过后续处理，重新监测

                previous_class = predicted_class  # 更新上一次的分类结果

                introduction_text = information_retrieval.get_introduction_text(predicted_class, deepseek_api_key)
                print("已调用deepseek大模型生成介绍文本")
            else:
                print("分类结果不一致或置信度不足")
                introduction_text = "未检测到校园景点"

            # 语音合成
            audio_file = texttospeech.text_to_speech(introduction_text)
            print("已生成mp3语音文件")

            if audio_file is not None:
                # VR 眼镜播放语音
                vr_interaction_obj.play_audio("/home/unitree/project-3/output.mp3")
                print("等待五分钟后...")
                time.sleep(300)
            else:
                print("语音合成失败")

            # 清空图像列表并删除临时文件夹中的图像
            images = []
            for img_file in os.listdir(temp_folder):
                os.remove(os.path.join(temp_folder, img_file))
            print("已清空临时文件夹")

            image_count=0

            # 如果未检测到校园景点，等待三分钟
            if introduction_text == "未检测到校园景点":
                print("未检测到校园景点，等待三分钟后继续监测...")
                time.sleep(180)  # 等待三分钟

    cap.release()
    # 最后删除临时文件夹
    shutil.rmtree(temp_folder)

    pass

if __name__ == "__main__":
    # 创建 VRInteraction 类的实例
    from vr_interaction import VRInteraction

    vr_interaction_obj = VRInteraction()
    vr_interaction_obj.connect_vr_glasses()

    # 启动服务器监听
    vr_interaction_thread = threading.Thread(target=vr_interaction_obj.start_listening)
    vr_interaction_thread.daemon = True  # 设置为守护线程
    vr_interaction_thread.start()

    # 运行主函数
    main(vr_interaction_obj)