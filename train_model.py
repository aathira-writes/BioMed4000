import cv2
import os
import numpy as np

def train_model(dataset_path="dataset", model_path="model.yml"):
    recognizer = cv2.face.LBPHFaceRecognizer_create()

    faces = []
    labels = []

    # Loop through dataset folders
    for folder in os.listdir(dataset_path):
        if not folder.startswith("user_"):
            continue

        user_id = int(folder.split("_")[1])
        folder_path = os.path.join(dataset_path, folder)

        for img_name in os.listdir(folder_path):
            img_path = os.path.join(folder_path, img_name)
            img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)

            if img is None:
                continue

            faces.append(img)
            labels.append(user_id)

    if len(faces) == 0:
        print("No training data found.")
        return

    recognizer.train(faces, np.array(labels))
    recognizer.write(model_path)
    print("Model trained successfully.")
