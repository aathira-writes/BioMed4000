import cv2
import os

CONFIDENCE_THRESHOLD = 65   # LBPH distance: lower = stricter. 65 rejects lookalikes.
REQUIRED_FRAMES      = 5    # Must match this many consecutive frames before accepting.
FACE_SIZE            = (200, 200)

def _preprocess(face_img):
    face_img = cv2.resize(face_img, FACE_SIZE)
    face_img = cv2.equalizeHist(face_img)
    return face_img

def recognize_user(model_path="model.yml"):
    if not os.path.exists(model_path):
        print("Model not found.")
        return None

    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.read(model_path)

    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )
    cam = cv2.VideoCapture(0)

    detected_id       = None
    consecutive       = 0
    last_id           = None

    while True:
        ret, frame = cam.read()
        if not ret:
            break

        gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=3)

        for (x, y, w, h) in faces:
            face_img           = _preprocess(gray[y:y+h, x:x+w])
            label, confidence  = recognizer.predict(face_img)

            if confidence < CONFIDENCE_THRESHOLD:
                if label == last_id:
                    consecutive += 1
                else:
                    consecutive  = 1
                    last_id      = label
                color  = (0, 255, 0)
                status = f"ID {label}  conf:{confidence:.1f}  ({consecutive}/{REQUIRED_FRAMES})"
            else:
                consecutive = 0
                last_id     = None
                color  = (0, 0, 255)
                status = f"Unknown  conf:{confidence:.1f}"

            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
            cv2.putText(frame, status, (x, y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2)

            if consecutive >= REQUIRED_FRAMES:
                detected_id = label

        cv2.putText(frame, "Press Q to cancel", (10, frame.shape[0] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 180, 180), 1)
        cv2.imshow("Identity Verification", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

        if detected_id is not None:
            break

    cam.release()
    cv2.destroyAllWindows()
    return detected_id
