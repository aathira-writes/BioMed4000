import cv2
import os

def recognize_user(model_path="model.yml"):
    if not os.path.exists(model_path):
        print("Model not found.")
        return None

    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.read(model_path)

    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    cam = cv2.VideoCapture(0)

    detected_id = None
    confidence_threshold = 50

    while True:
        ret, frame = cam.read()
        if not ret:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)

        for (x, y, w, h) in faces:
            face_img = gray[y:y+h, x:x+w]
            label, confidence = recognizer.predict(face_img)

            if confidence < confidence_threshold:
                detected_id = label
            else:
                detected_id = None  # unknown face

            cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)
            cv2.putText(frame, f"ID: {detected_id}", (x, y-10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,255,0), 2)

        cv2.imshow("Identity Verification", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

        if detected_id is not None:
            break
        frame = None  # clear frame for next capture

    cam.release()
    cv2.destroyAllWindows()
    return detected_id
