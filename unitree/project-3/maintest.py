import cv2
import time
import video_preprocessing
import image_classification
import informationtest
import texttospeech
import vr_interaction

# RTSP 流地址
rtsp_url = "rtsp://192.168.144.25:8554/main.264"
# Socket 配置
server_ip = "192.168.10.110"
server_port = 5566

pinyin_to_spot_name = {
    'hangtianguan_0': '航天馆',
    'hangtianguan_1': '航天馆',
    'tushuguan_0': '图书馆',
    'tushuguan_1': '图书馆',
    'tushuguan_2': '图书馆',
    'wozhencangqiong_0': '卧震苍穹',
    'wozhencangqiong_1': '卧震苍穹',
    'xiaobowuguan_0': '小博物馆',
    'xiaobulou_0': '小博物馆',
    'xiaobulou_1': '校部楼',
    'xingzhenglou_0': '行政楼',
    'xingzhenglou_1': '行政楼',
    'xingzhenglou_2': '行政楼',
    'zhulou_0': '主楼',
    'zhulou_1': '主楼',
    'zhulou_2': '主楼',
}

def pinyin_to_name(predicted_pinyin):
    # 使用字典的get方法获取对应的文字名称，如果拼音不在字典中，则返回"未知景点"
    return pinyin_to_spot_name.get(predicted_pinyin, "未知景点")

def main():
    # 初始化
    deepseek_api_key = "sk-7bbd9bd7ae0c46f58f7c5e9413c425ab"
    #vr_glasses = vr_interaction.connect_vr_glasses()

    # 读取图像
    image_path = './test_image.jpg'  # 图像的路径
    img = cv2.imread(image_path)

    # 预处理帧
    preprocessed_frame = video_preprocessing.preprocess_image(img)

    # 预测
    predicted_class, confidence = image_classification.predict_image(preprocessed_frame)

    # 打印预测结果
    print(f'Predicted class: {predicted_class} (Confidence: {confidence:.4f})')

    predicted_spot_name = pinyin_to_name(predicted_class)

    # 获取景点介绍
    introduction_text = informationtest.get_introduction_text(predicted_spot_name, deepseek_api_key)
    
    print(f'{introduction_text}')

    # 语音合成
    audio_file = texttospeech.text_to_speech(introduction_text)

    # VR 眼镜播放语音
    #vr_glasses.play_audio(audio_file)

if __name__ == "__main__":
    main()