
import cv2

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

if __name__ == "__main__":
    import matplotlib.pyplot as plt
    img = get_image(0)
    img = cv_resize(img, 480, 360)
    plt.imshow(img)
    plt.show()