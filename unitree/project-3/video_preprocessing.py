import tensorflow as tf
import cv2
import numpy as np

IMG_SIZE = (224, 224)
BATCH_SIZE = 32
NUM_CLASSES = 17

# 定义预处理函数
def preprocess_image(img):
    # 将 OpenCV 的 BGR 图像转换为 RGB
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    # 调整图像大小到模型所期望的尺寸
    img = cv2.resize(img,IMG_SIZE)
    img_array = tf.keras.utils.img_to_array(img)
    img_array = np.expand_dims(img_array, axis=0)
    img_array /= 255.0
    return img_array
