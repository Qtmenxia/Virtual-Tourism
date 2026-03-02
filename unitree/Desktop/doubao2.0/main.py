import asyncio
import matplotlib.pyplot as plt
from main.camera import get_image, preprocess_image
from main.modelpredict  import predict_image

tmp_file = "./main/tmp_image.jpg"
url = "rtsp://192.168.144.25:8554/main.264"

img = get_image(url)
img_array = preprocess_image(img)
plt.imsave(tmp_file, img)
#预测
label,scores = predict_image(img_array)
print(label, scores)

