import cv2
import tensorflow as tf
import numpy as np
import os
from collections import Counter

from utils import preprocess_face, emotion_labels
from face_detector import detect_faces

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "..", "model", "emotion_efficientnet.keras")

model = tf.keras.models.load_model(MODEL_PATH)

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Webcam not accessible")
    exit()

print("Press Q or ESC to exit")

# store all predictions
all_predictions = []

while True:
    ret, frame = cap.read()
    if not ret:
        break

    faces = detect_faces(frame)

    for (x, y, w, h) in faces:
        face = frame[y:y+h, x:x+w]
        face_input = preprocess_face(face)

        preds = model.predict(face_input, verbose=0)
        emotion = emotion_labels[np.argmax(preds)]
        confidence = float(np.max(preds))

        all_predictions.append(emotion)

        text = f"{emotion} {confidence:.2f}"

        cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
        cv2.putText(
            frame,
            text,
            (x, y - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 0),
            2
        )

    cv2.imshow("Emotion Detection", frame)

    key = cv2.waitKey(1)
    if key == ord("q") or key == 27:  # q or ESC
        break

cap.release()
cv2.destroyAllWindows()

# show final results
print("\nSESSION RESULTS")
print("---------------")

if len(all_predictions) == 0:
    print("No face detected during session")
else:
    emotion_count = Counter(all_predictions)

    for emotion, count in emotion_count.items():
        print(f"{emotion}: {count} frames")

    final_emotion = emotion_count.most_common(1)[0][0]
    print("\nFinal Detected Emotion:", final_emotion)
