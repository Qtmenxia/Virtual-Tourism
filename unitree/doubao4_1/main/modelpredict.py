import tensorflow as tf
import numpy as np
import json
import threading
from collections import Counter

from main.huawei import predict
from main.params import model, class_labels, huawei_token

class PredictionManager:
    def __init__(self):
        self.lock = threading.Lock()
        self.results = []
        
    async def predict_image(self, img_array, mode = "offline"):
        if mode not in ["offline", "online"]:
            raise ValueError("mode必须是offline，online中的一种")
        with self.lock:
            if mode == "offline":
                predictions = model.predict(img_array)
                predicted_class_index = np.argmax(predictions, axis=1)[0]
                predicted_class_label = class_labels[predicted_class_index]
                predicted_confidence = np.max(predictions, axis=1)[0]
                self.results.append((predicted_class_label, predicted_confidence))
                
                # 当收集到5个结果时进行综合评价
                if len(self.results) >= 5:
                    return self._evaluate_results()
            if mode == "online":
                # TODO
                pass
            return None
    
    def _evaluate_results(self):
        # 获取最常见的预测类别
        labels = [r[0] for r in self.results]
        confidences = [r[1] for r in self.results]
        counter = Counter(labels)
        most_common = counter.most_common(1)[0]
        
        # 如果5个结果中有3个以上相同且置信度>90%，则返回该类别
        if most_common[1] >= 3 and all(c > 0.9 for c in confidences[:most_common[1]]):
            result = most_common[0]
        else:
            result = "others_0"
        
        self.results = []  # 清空结果
        return result, sum(confidences)/len(confidences)
