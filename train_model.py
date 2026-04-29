import cv2
import os
import numpy as np
from faces import _preprocess

def train_model(dataset_path="dataset", model_path="model.yml"):
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    faces  = []
    labels = []

    for folder in os.listdir(dataset_path):
        if not folder.startswith("user_"):
            continue
        user_id     = int(folder.split("_")[1])
        folder_path = os.path.join(dataset_path, folder)

        for img_name in os.listdir(folder_path):
            img = cv2.imread(os.path.join(folder_path, img_name), cv2.IMREAD_GRAYSCALE)
            if img is None:
                continue
            faces.append(_preprocess(img))
            labels.append(user_id)

    if not faces:
        print("No training data found.")
        return

    recognizer.train(faces, np.array(labels))
    recognizer.write(model_path)
    print(f"Model trained on {len(faces)} images across {len(set(labels))} user(s).")
