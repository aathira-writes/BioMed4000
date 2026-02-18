import cv2

MODEL_PATH = "model.yml"

# Load Haar cascade
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

def load_model():
    model = cv2.face.LBPHFaceRecognizer_create()
    model.read(MODEL_PATH)
    return model

def recognize_user():
    model = load_model()
    cap = cv2.VideoCapture(0)

    print("Camera active. Look at the screen...")

    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        faces = face_cascade.detectMultiScale(gray, 1.3, 5)

        for (x, y, w, h) in faces:
            face = gray[y:y+h, x:x+w]

            label, confidence = model.predict(face)

            # Draw rectangle for feedback
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            cv2.putText(frame, f"ID: {label}  Conf: {confidence:.1f}",
                        (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                        (0, 255, 0), 2)

            cv2.imshow("Recognition", frame)

            # Return the predicted user ID
            cap.release()
            cv2.destroyAllWindows()
            return label

        cv2.imshow("Recognition", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    return None
