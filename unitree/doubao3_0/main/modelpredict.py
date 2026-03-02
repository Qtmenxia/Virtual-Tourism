import tensorflow as tf
import numpy as np
import json

# 加载保存的模型
model = tf.keras.models.load_model('/home/unitree/doubao3_0/main/resnet50_model')

# 加载类别标签
with open('/home/unitree/doubao3_0/main/class_labels.json', 'r') as f:
    class_labels = json.load(f)

async def predict_image(img_array):
    predictions = model.predict(img_array)
    predicted_class_index = np.argmax(predictions, axis=1)[0]
    predicted_class_label = class_labels[predicted_class_index]
    predicted_confidence = np.max(predictions, axis=1)[0]
    return predicted_class_label, predicted_confidence
