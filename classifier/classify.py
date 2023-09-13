import os

import cv2
import numpy as np
import torch
from torchvision import models

from .model_config import *


class Classifier:
    @classmethod
    def predict_label(cls, image, filename):
        model = models.vgg19(pretrained=True).to(DEVICE)
        model.eval()

        image = cls.preprocess_image(image)
        image = torch.from_numpy(image)
        image = image.to(DEVICE)

        print("[INFO] loading labels...")
        image_labels = dict(enumerate(open(IN_LABELS)))
        print("[INFO] classifying image")
        logits = model(image)
        probabilities = torch.nn.Softmax(dim=-1)(logits)
        (label, prob) = (
            image_labels[probabilities.argmax().item()],
            probabilities.max().item(),
        )

        return {"filename": filename, "label": label.strip(), "probability": prob * 100}

    @classmethod
    def classify_image(cls):
        results = []
        folder = "images"
        for filename in os.listdir(folder):
            img = cv2.imread(os.path.join(folder, filename))
            if img is not None:
                prediction = cls.predict_label(img, filename)
                results.append(prediction)

        return results

    @classmethod
    def preprocess_image(cls, image):
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        image = cv2.resize(image, (IMAGE_SIZE, IMAGE_SIZE))
        image = image.astype("float32") / 255.0
        image -= MEAN
        image /= STD
        image = np.transpose(image, (2, 0, 1))
        image = np.expand_dims(image, 0)

        return image

    @classmethod
    def save_image(cls, file_name, image):
        image.save(f"./images/{file_name}")
