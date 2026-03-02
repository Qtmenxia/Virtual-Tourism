import asyncio
import matplotlib.pyplot as plt
from main.camera import get_image, preprocess_image
from main.doubao import get_msg, get_audio
#from main.huawei import get_token, predict
from main.modelpredict  import predict_image
from main.merge import merge_audio_files
from main.TTSWebSocketDemo import filter_markdown_special_chars

tmp_file = "/home/unitree/doubao3_0/main/tmp_image.jpg"
#huawei_token = get_token()

async def generate(url = "rtsp://192.168.144.25:8554/main.264", target_width  = 224, target_height = 224, audio_path = "/home/unitree/doubao3_0/main/audio"):
    #global huawei_token
    global tmp_file
    img = get_image(url)
    img_array = preprocess_image(img)
    #img = cv_resize(img, target_width, target_height)
    # plt.imshow(img)
    # plt.show()
    plt.imsave(tmp_file, img)
    #预测
    label,scores = await predict_image(img_array)
    print(label, scores)

    # if float(scores) < 0.9:
    #     label = "others_0"
    # label = 'tushuguan_0'
    if label.startswith("others"):
        return "没有检测到地标建筑。"
    # label = "hangtianguan_0"
    msg = await get_msg(label)
    
    # msg = msg[:250]
    msg = await filter_markdown_special_chars(msg)
    with open("/home/unitree/doubao3_0/main/introduction.txt", "w") as f:
        f.write(msg)
    audio_files = await get_audio(msg, audio_path)
    merge_audio_files(audio_files, f"{audio_path}/audio.mp3")

    # await play_audio_list()
    return audio_files
if __name__ == "__main__":
    # generate()
    # 本地摄像头测试
    generate(0)
