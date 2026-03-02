import torch
import torchvision.models as models
from torchvision.models import ResNet50_Weights

# 使用新的方式加载预训练权重
model = models.resnet50(weights=ResNet50_Weights.IMAGENET1K_V1)

checkpoint = {
    'model_state_dict': model.state_dict(),
    'num_classes': 1000,
    'architecture': 'ResNet50',
    'source': 'torchvision_imagenet_pretrained'
}

torch.save(checkpoint, "resnet50_model.pth")
