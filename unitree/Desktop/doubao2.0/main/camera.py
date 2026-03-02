import tensorflow as tf
import cv2
import numpy as np

IMG_SIZE = (224, 224)

def cv_resize(frame, 
    target_width,
    target_height ):
    
    frame = cv2.resize(frame, (target_width, target_height), interpolation= cv2.INTER_LANCZOS4)
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    return frame

def get_image(url):
    print("正在获取图片")
    cap = cv2.VideoCapture(url)
    ret, frame = cap.read()
    cap.release()
    return frame

def preprocess_image(img):
    # 将 OpenCV 的 BGR 图像转换为 RGB
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    # 调整图像大小到模型所期望的尺寸
    img = cv2.resize(img, (IMG_SIZE[1], IMG_SIZE[0]))
    img_array = tf.keras.utils.img_to_array(img)
    img_array = np.expand_dims(img_array, axis=0)
    img_array /= 255.0
    return img_array

if __name__ == "__main__":
    import matplotlib.pyplot as plt
    img = get_image(0)
    img = cv_resize(img, 480, 360)
    plt.imshow(img)
    plt.show()