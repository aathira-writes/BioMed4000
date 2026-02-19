import cv2
import os

def capture_faces(user_id, num_images=50):
    dataset_path = os.path.join("dataset", f"user_{user_id}")
    os.makedirs(dataset_path, exist_ok=True)


    cam = cv2.VideoCapture(0)
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

    count = 0
    print("Starting face capture...")

    while count < num_images:
        ret, frame = cam.read()
        if not ret:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)

        for (x, y, w, h) in faces:
            count += 1
            face_img = gray[y:y+h, x:x+w]

            file_path = os.path.join(dataset_path, f"{count}.jpg")
            cv2.imwrite(file_path, face_img)

            cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)
            cv2.putText(frame, f"{count}/{num_images}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        cv2.imshow("Capturing Faces", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cam.release()
    cv2.destroyAllWindows()
    print("Face capture complete.")
