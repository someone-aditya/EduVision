import cv2
import os
import json
import numpy as np


DATASET_DIR = "data/student_images"
MODEL_DIR = "data/model"

os.makedirs(MODEL_DIR, exist_ok=True)


# OpenCV face detector
face_detector = cv2.CascadeClassifier(
    cv2.data.haarcascades
    + "haarcascade_frontalface_default.xml"
)

faces = []
labels = []

label_map = {}
current_label = 0


print("\n==============================")
print("     VISIONED AI TRAINER")
print("==============================\n")


for student_id in os.listdir(DATASET_DIR):

    student_folder = os.path.join(
        DATASET_DIR,
        student_id
    )

    if not os.path.isdir(student_folder):
        continue

    print(f"Student: {student_id}")

    label_map[current_label] = student_id

    for filename in os.listdir(student_folder):

        image_path = os.path.join(
            student_folder,
            filename
        )

        image = cv2.imread(image_path)

        if image is None:
            print(f"Could not read: {filename}")
            continue

        gray = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2GRAY
        )

        detected_faces = face_detector.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(80, 80)
        )

        if len(detected_faces) == 0:
            print(f"❌ No face found: {filename}")
            continue

        # Pick largest face
        x, y, w, h = max(
            detected_faces,
            key=lambda box: box[2] * box[3]
        )

        face = gray[y:y+h, x:x+w]

        face = cv2.resize(
            face,
            (200, 200)
        )

        faces.append(face)
        labels.append(current_label)

        print(f"✓ Added: {filename}")

    current_label += 1


if len(faces) == 0:

    print("\n❌ ERROR")
    print("No usable faces were found.")

else:

    recognizer = cv2.face.LBPHFaceRecognizer_create()

    recognizer.train(
        faces,
        np.array(labels)
    )

    model_path = os.path.join(
        MODEL_DIR,
        "face_model.yml"
    )

    recognizer.write(model_path)

    label_path = os.path.join(
        MODEL_DIR,
        "labels.json"
    )

    with open(label_path, "w") as file:
        json.dump(label_map, file)

    print("\n==============================")
    print("     TRAINING COMPLETE ✓")
    print("==============================")

    print(f"Students trained: {len(label_map)}")
    print(f"Faces used: {len(faces)}")
    print(f"Model saved: {model_path}")