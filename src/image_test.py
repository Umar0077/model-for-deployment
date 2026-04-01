import cv2
import tensorflow as tf
import numpy as np

from utils import preprocess_face, emotion_labels
from face_detector import detect_faces

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "..", "model", "emotion_efficientnet.keras")

model = tf.keras.models.load_model(MODEL_PATH)

img_path = input("Enter image path: ")

img = cv2.imread(img_path)

faces = detect_faces(img)

for (x, y, w, h) in faces:
    face = img[y:y+h, x:x+w]
    face = preprocess_face(face)

    preds = model.predict(face, verbose=0)
    emotion = emotion_labels[np.argmax(preds)]
    confidence = np.max(preds)

    print("Emotion:", emotion)
    print("Confidence:", confidence)
