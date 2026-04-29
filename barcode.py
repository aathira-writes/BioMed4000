import cv2
import os

def scan_barcode(model_path=None):
    """
    Opens a camera window, scans for any barcode/QR code, returns the
    decoded string.  Press Q to cancel (returns None).
    Mirrors the same pattern used by recognize_user() in faces.py.
    """
    try:
        from pyzbar import pyzbar as pzb
    except ImportError:
        print("pyzbar not installed.")
        return None

    cam = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cam.isOpened():
        cam = cv2.VideoCapture(0)
    if not cam.isOpened():
        print("Could not open camera.")
        return None

    result   = None
    warmup   = 0

    while True:
        ret, frame = cam.read()
        if not ret:
            continue

        # Skip black warmup frames
        if frame.max() < 8:
            warmup += 1
            cv2.imshow("Barcode Scanner – press Q to cancel", frame)
            cv2.waitKey(1)
            continue

        barcodes = pzb.decode(frame)
        for bc in barcodes:
            result = bc.data.decode("utf-8")
            r = bc.rect
            cv2.rectangle(frame,
                          (r.left, r.top),
                          (r.left + r.width, r.top + r.height),
                          (0, 255, 0), 2)
            cv2.putText(frame, result, (r.left, r.top - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        cv2.putText(frame, "Press Q to cancel",
                    (10, frame.shape[0] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 180, 180), 1)
        cv2.imshow("Barcode Scanner – press Q to cancel", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        if result:
            break

    cam.release()
    cv2.destroyAllWindows()
    return result
