import asyncio
import matplotlib.pyplot as plt
from main.camera import get_image, preprocess_image
from main.doubao import get_msg, get_audio
#from main.huawei import get_token, predict
from main.playsoundtest import play_audio_list
from main.modelpredict  import predict_image

tmp_file = "./main/tmp_image.jpg"
#huawei_token = get_token()

async def generate(url = "rtsp://192.168.144.25:8554/main.264", target_width  = 224, target_height = 224, audio_path = "main/audio"):
    #global huawei_token
    global tmp_file
    img = get_image(url)
    img_array = preprocess_image(img)
    #img = cv_resize(img, target_width, target_height)
    # plt.imshow(img)
    # plt.show()
    plt.imsave(tmp_file, img)
    asyncio.sleep(1.)
    #预测
    label,scores = predict_image(img_array)
    print(label, scores)

    # if float(scores) < 0.9:
    #     label = "others_0"
    # label = 'tushuguan_0'
    if label.startswith("others"):
        return "没有检测到地标建筑。"
    msg = await get_msg(label)
    
    msg = msg[:250]
    audio_files = await get_audio(msg, audio_path)
    
    await play_audio_list()
    return audio_files

if __name__ == "__main__":
    # generate()
    # 本地摄像头测试
    asyncio.run(generate(0，224，224)
    asyncio.run(play_audio_list())