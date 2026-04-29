import cv2
import numpy as np
import urllib.request
import urllib.parse
import json


def capture_pill_frame():
    """
    Opens camera with a targeting circle. SPACE to capture, Q to cancel.
    Returns a BGR frame (numpy array) or None.
    """
    cam = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cam.isOpened():
        cam = cv2.VideoCapture(0)
    if not cam.isOpened():
        return None

    cam.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
    cam.set(cv2.CAP_PROP_FRAME_WIDTH,  1280)
    cam.set(cv2.CAP_PROP_FRAME_HEIGHT,  720)

    WIN = "Pill Scanner – SPACE to capture, Q to cancel"
    cv2.namedWindow(WIN, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WIN, 960, 540)
    cv2.setWindowProperty(WIN, cv2.WND_PROP_TOPMOST, 1)

    result = None
    while True:
        ret, frame = cam.read()
        if not ret or frame is None:
            continue

        h, w = frame.shape[:2]
        cx, cy = w // 2, h // 2
        r = min(w, h) // 5

        display = frame.copy()
        cv2.circle(display, (cx, cy), r, (0, 200, 255), 2)
        # Cross-hair guides
        cv2.line(display, (cx - r, cy), (cx + r, cy), (0, 200, 255), 1)
        cv2.line(display, (cx, cy - r), (cx, cy + r), (0, 200, 255), 1)
        cv2.putText(display, "Place pill inside circle — hold steady",
                    (10, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 200, 255), 2)
        cv2.putText(display, "SPACE = capture    Q = cancel",
                    (10, h - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (160, 160, 160), 1)

        cv2.imshow(WIN, display)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        if key == ord(' '):
            result = frame.copy()
            break

    cam.release()
    cv2.destroyAllWindows()
    return result


def read_imprint(frame):
    """
    Uses EasyOCR to extract imprint text from the pill in the frame center.
    Raises ImportError with message 'easyocr' if the library is missing.
    Returns a list of unique uppercase strings.
    """
    try:
        import easyocr
    except ImportError:
        raise ImportError("easyocr")

    h, w = frame.shape[:2]
    cx, cy = w // 2, h // 2
    r = min(w, h) // 5
    x1, y1 = max(0, cx - r), max(0, cy - r)
    x2, y2 = min(w, cx + r), min(h, cy + r)
    crop = frame[y1:y2, x1:x2]

    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)

    # Three preprocessings for best imprint coverage
    variants = [
        gray,
        cv2.equalizeHist(gray),
        cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2),
    ]

    reader = easyocr.Reader(['en'], gpu=False, verbose=False)
    seen, results = set(), []
    for img in variants:
        for text in reader.readtext(
                img, detail=0,
                allowlist='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'):
            t = text.strip().upper()
            if t and t not in seen:
                seen.add(t)
                results.append(t)
    return results


def lookup_rximage(imprint_text):
    """
    Queries NIH RxImage API for pills matching the given imprint.
    Returns a list of result dicts (may be empty on no match or network error).
    """
    params = urllib.parse.urlencode({"imprint": imprint_text})
    url = f"https://rximage.nlm.nih.gov/api/rximage/1/rxnav?{params}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "BioMed4000/1.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode())
        return data.get("nlmRxImages", [])
    except Exception:
        return []
