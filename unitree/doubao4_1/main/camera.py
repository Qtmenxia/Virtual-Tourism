import cv2
import numpy as np
import os
import threading
import time
import matplotlib.pyplot as plt
from datetime import datetime
import tensorflow as tf
from main.params import IMAGE_DIR, IMG_SIZE, MAX_CACHE

class CameraManager:
    def __init__(self):
        self.lock = threading.Lock()
        self.frame_counter = 0
        self.cached_images = []
        os.makedirs(IMAGE_DIR, exist_ok=True)
    
    def cv_resize(self, frame, target_width, target_height):
        frame = cv2.resize(frame, (target_width, target_height), interpolation=cv2.INTER_LANCZOS4)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return frame
    
    def get_image(self, url):
        print("正在获取图片")
        cap = cv2.VideoCapture(url)
        ret, frame = cap.read()
        cap.release()
        if ret:
            self._save_frame(frame)
        return frame if ret else None
    
    def get_images(self, url, k=5):
        frames = []
        cap = cv2.VideoCapture(url)
        for _ in range(k):
            ret, frame = cap.read()
            if ret:
                frames.append(frame)
                self._save_frame(frame)
        cap.release()
        return frames if len(frames) == k else None
    
    def preprocess_image(self, img):
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = cv2.resize(img, (IMG_SIZE[1], IMG_SIZE[0]))
        img_array = tf.keras.utils.img_to_array(img)
        img_array = np.expand_dims(img_array, axis=0)
        img_array /= 255.0
        return img_array
    
    def _save_frame(self, frame):
        with self.lock:
            # 生成唯一文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            filename = f"{timestamp}_{self.frame_counter}.jpg"
            self.frame_counter += 1
            
            # 保存图片
            save_path = os.path.join(IMAGE_DIR, filename)
            cv2.imwrite(save_path, frame)
            
            # 管理缓存
            self.cached_images.append(save_path)
            if len(self.cached_images) > MAX_CACHE:
                try:
                    os.remove(self.cached_images.pop(0))
                except:
                    pass

if __name__ == "__main__":
    cam_manager = CameraManager()
    img = cam_manager.get_image(0)
    if img is not None:
        img = cam_manager.cv_resize(img, 480, 360)
        plt.imshow(img)
        plt.show()