import cv2
import numpy as np
import contextlib
import os


@contextlib.contextmanager
def _silence_zbar():
    """
    Suppress ZBar assertion warnings on Windows.
    ZBar's DLL writes via the MSVC runtime's own stderr handle, which bypasses
    Python's fd 2 redirect, so we must also redirect at the Win32 HANDLE level.
    """
    import ctypes
    kernel32       = ctypes.windll.kernel32
    STD_ERROR      = -12
    GENERIC_WRITE  = 0x40000000
    OPEN_EXISTING  = 3

    # Open NUL at both levels
    nul_fd     = os.open(os.devnull, os.O_WRONLY)
    nul_handle = kernel32.CreateFileW("NUL", GENERIC_WRITE, 0, None,
                                      OPEN_EXISTING, 0, None)
    # Save originals
    saved_fd     = os.dup(2)
    saved_handle = kernel32.GetStdHandle(STD_ERROR)

    os.dup2(nul_fd, 2)
    kernel32.SetStdHandle(STD_ERROR, nul_handle)
    try:
        yield
    finally:
        kernel32.SetStdHandle(STD_ERROR, saved_handle)
        os.dup2(saved_fd, 2)
        kernel32.CloseHandle(nul_handle)
        os.close(nul_fd)
        os.close(saved_fd)


def scan_barcode():
    """
    Opens a camera window with a targeting guide.
    User positions the barcode inside the green box.
    Returns the decoded string, or None if cancelled (Q).
    """
    try:
        from pyzbar import pyzbar as pzb
        from pyzbar.pyzbar import ZBarSymbol
    except ImportError:
        print("pyzbar not installed.")
        return None

    SYMBOLS = [
        ZBarSymbol.UPCA, ZBarSymbol.UPCE,
        ZBarSymbol.EAN8, ZBarSymbol.EAN13,
        ZBarSymbol.CODE128, ZBarSymbol.CODE39,
        ZBarSymbol.QRCODE,
    ]

    cam = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cam.isOpened():
        cam = cv2.VideoCapture(0)
    if not cam.isOpened():
        print("Could not open camera.")
        return None

    cam.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
    cam.set(cv2.CAP_PROP_FRAME_WIDTH,  1280)
    cam.set(cv2.CAP_PROP_FRAME_HEIGHT,  720)

    WIN = "Barcode Scanner – press Q to cancel"
    cv2.namedWindow(WIN, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WIN, 960, 540)
    cv2.setWindowProperty(WIN, cv2.WND_PROP_TOPMOST, 1)

    result      = None
    last_seen   = None
    consecutive = 0
    REQUIRED    = 2          # accept after 2 matching frames in a row

    while True:
        ret, frame = cam.read()
        if not ret or frame is None:
            continue
        if frame.max() < 8:
            cv2.imshow(WIN, frame)
            cv2.waitKey(1)
            continue

        h, w = frame.shape[:2]

        # Targeting box — generous: 80% wide, 60% tall
        bx1 = int(w * 0.10);  bx2 = int(w * 0.90)
        by1 = int(h * 0.20);  by2 = int(h * 0.80)

        gray_full = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        with _silence_zbar():
            # Pass 1: full frame — widest net
            barcodes = pzb.decode(gray_full, symbols=SYMBOLS)

            # Pass 2: sharpened full frame
            if not barcodes:
                kernel   = np.array([[-1,-1,-1],[-1,9,-1],[-1,-1,-1]])
                barcodes = pzb.decode(cv2.filter2D(gray_full, -1, kernel), symbols=SYMBOLS)

            # Pass 3: adaptive threshold (helps with glare / uneven lighting)
            if not barcodes:
                thresh   = cv2.adaptiveThreshold(
                    gray_full, 255,
                    cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                    cv2.THRESH_BINARY, 51, 11)
                barcodes = pzb.decode(thresh, symbols=SYMBOLS)

            # Pass 4: try without symbol filter in case it's an unusual type
            if not barcodes:
                barcodes = pzb.decode(gray_full)

        detected = barcodes[0].data.decode("utf-8") if barcodes else None

        if detected:
            if detected == last_seen:
                consecutive += 1
            else:
                last_seen   = detected
                consecutive = 1
        else:
            consecutive = 0

        # Draw targeting box
        box_color = (0, 255, 0) if consecutive > 0 else (0, 200, 255)
        cv2.rectangle(frame, (bx1, by1), (bx2, by2), box_color, 2)
        # Corner accents
        L = 30
        for (cx, cy, dx, dy) in [(bx1,by1,1,1),(bx2,by1,-1,1),(bx1,by2,1,-1),(bx2,by2,-1,-1)]:
            cv2.line(frame, (cx, cy), (cx+dx*L, cy), box_color, 3)
            cv2.line(frame, (cx, cy), (cx, cy+dy*L), box_color, 3)

        # Draw polygon for detected barcode (offset into full frame)
        if barcodes and hasattr(barcodes[0], 'polygon') and barcodes[0].polygon:
            bc  = barcodes[0]
            # check if it came from ROI or full frame
            if bc.rect.left < (bx2 - bx1):   # came from ROI
                pts = np.array(
                    [[p.x + bx1, p.y + by1] for p in bc.polygon], np.int32)
            else:
                pts = np.array([[p.x, p.y] for p in bc.polygon], np.int32)
            cv2.polylines(frame, [pts], True, (0, 255, 0), 3)

        # HUD
        if consecutive > 0:
            status = f"Confirming: {consecutive}/{REQUIRED}  ({last_seen})"
            color  = (0, 255, 0)
        else:
            status = "Position barcode inside the box"
            color  = (0, 200, 255)

        cv2.putText(frame, status, (10, 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
        cv2.putText(frame, "Press Q to cancel", (10, h - 12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (160, 160, 160), 1)

        cv2.imshow(WIN, frame)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break

        if consecutive >= REQUIRED:
            result = last_seen
            cv2.waitKey(700)
            break

    cam.release()
    cv2.destroyAllWindows()
    return result
