import cv2
import numpy as np

IMAGE_SIZE = (224, 224)

emotion_labels = [
    "angry",
    "disgust",
    "fear",
    "happy",
    "neutral",
    "sad",
    "surprise"
]

def preprocess_face(face):
    face = cv2.resize(face, IMAGE_SIZE)
    face = cv2.cvtColor(face, cv2.COLOR_BGR2RGB)
    face = face.astype("float32")
    face = np.expand_dims(face, axis=0)
    return face
