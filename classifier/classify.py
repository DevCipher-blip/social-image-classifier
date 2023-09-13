import os

import torch
from PIL import Image, UnidentifiedImageError
from torchvision import models, transforms

from .model_config import DEVICE, IMAGE_SIZE, IN_LABELS, MEAN, STD

PREPROCESS = transforms.Compose(
    [
        transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
        transforms.ToTensor(),
        transforms.Normalize(MEAN, STD),
    ]
)


class Classifier:
    @classmethod
    def predict_label(cls, image, filename):
        model = models.vgg19(weights=models.VGG19_Weights.IMAGENET1K_V1).to(DEVICE)
        model.eval()

        batch = PREPROCESS(image.convert("RGB")).unsqueeze(0).to(DEVICE)
        with open(IN_LABELS) as labels_file:
            image_labels = dict(enumerate(labels_file))
        probabilities = torch.softmax(model(batch), dim=-1)
        label, prob = image_labels[probabilities.argmax().item()], probabilities.max().item()

        return {"filename": filename, "label": label.strip(), "probability": prob * 100}

    @classmethod
    def classify_image(cls):
        results = []
        folder = "images"
        for filename in os.listdir(folder):
            try:
                image = Image.open(os.path.join(folder, filename))
            except (UnidentifiedImageError, OSError):
                continue
            results.append(cls.predict_label(image, filename))

        return results

    @classmethod
    def save_image(cls, file_name, image):
        image.save(f"./images/{file_name}")
