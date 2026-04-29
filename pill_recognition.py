import cv2
import numpy as np
import urllib.request
import urllib.parse
import json


# ── Colour detection ───────────────────────────────────────────────────────

# (hue_lo, hue_hi, sat_min, val_min, val_max)  — OpenCV HSV: H 0-179, S/V 0-255
_COLOUR_RULES = [
    ("WHITE",      0,   179,  0,   200, 255),
    ("YELLOW",    20,    35, 80,    80, 255),
    ("ORANGE",     8,    19, 80,    80, 255),
    ("RED",        0,     7, 80,    50, 255),   # low hue
    ("RED",      172,   179, 80,    50, 255),   # wrap-around hue
    ("PINK",     155,   179, 30,   100, 255),
    ("BROWN",      8,    20, 30,    40, 150),
    ("GREEN",     36,    85, 60,    40, 255),
    ("TURQUOISE", 86,   100, 60,    40, 255),
    ("BLUE",     101,   130, 60,    40, 255),
    ("PURPLE",   131,   155, 50,    40, 255),
    ("GRAY",       0,   179,  0,    50, 199),
    ("BLACK",      0,   179,  0,     0,  49),
]

_COLOUR_HEX = {
    "WHITE":      "#f5f5f5",
    "YELLOW":     "#e8c830",
    "ORANGE":     "#d86820",
    "RED":        "#c02828",
    "PINK":       "#d87090",
    "BROWN":      "#7a5030",
    "GREEN":      "#30a040",
    "TURQUOISE":  "#20b0a0",
    "BLUE":       "#2858c0",
    "PURPLE":     "#7030b0",
    "GRAY":       "#808080",
    "BLACK":      "#202020",
    "UNKNOWN":    "#404040",
}


def _dominant_colour(frame, cx, cy, r):
    mask = np.zeros(frame.shape[:2], dtype=np.uint8)
    cv2.circle(mask, (cx, cy), int(r * 0.75), 255, -1)

    hsv    = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    pixels = hsv[mask > 0]           # shape (N, 3)
    if len(pixels) == 0:
        return "UNKNOWN"

    votes = {}
    for h, s, v in pixels:
        for name, hlo, hhi, smin, vmin, vmax in _COLOUR_RULES:
            if hlo <= h <= hhi and s >= smin and vmin <= v <= vmax:
                votes[name] = votes.get(name, 0) + 1
                break

    return max(votes, key=votes.get) if votes else "UNKNOWN"


# ── Shape detection ────────────────────────────────────────────────────────

def _pill_shape(frame, cx, cy, r):
    gray    = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (7, 7), 0)

    # Isolate pill region
    mask = np.zeros_like(blurred)
    cv2.circle(mask, (cx, cy), r, 255, -1)
    roi  = cv2.bitwise_and(blurred, blurred, mask=mask)

    # Threshold — Otsu inside the circle
    _, thresh = cv2.threshold(roi, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    thresh    = cv2.bitwise_and(thresh, mask)

    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return "UNKNOWN"

    cnt  = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(cnt)
    if area < 200:
        return "UNKNOWN"

    perim        = cv2.arcLength(cnt, True)
    circularity  = (4 * np.pi * area / perim ** 2) if perim > 0 else 0
    _, (bw, bh), _ = cv2.minAreaRect(cnt)
    aspect       = max(bw, bh) / (min(bw, bh) + 1e-5)

    if circularity > 0.82:
        return "ROUND"
    elif aspect < 1.45:
        return "OVAL"
    elif aspect < 2.2:
        return "OBLONG"
    else:
        return "CAPSULE"


def detect_pill_attributes(frame):
    """
    Returns (colour_name, shape_name, colour_hex) from the centre of the frame.
    Works on blurry images — does not require a sharp macro shot.
    """
    h, w   = frame.shape[:2]
    cx, cy = w // 2, h // 2
    r      = min(w, h) // 5
    colour = _dominant_colour(frame, cx, cy, r)
    shape  = _pill_shape(frame, cx, cy, r)
    return colour, shape, _COLOUR_HEX.get(colour, "#404040")


# ── Camera capture ─────────────────────────────────────────────────────────

def capture_pill_frame():
    """
    Split-view camera window — left: full frame, right: 4× zoom of pill area.
    SPACE to capture, Q to cancel. Returns BGR frame or None.
    """
    cam = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cam.isOpened():
        cam = cv2.VideoCapture(0)
    if not cam.isOpened():
        return None

    cam.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
    cam.set(cv2.CAP_PROP_FRAME_WIDTH,  1920)
    cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

    WIN = "Pill Scanner  |  SPACE = capture    Q = cancel"
    cv2.namedWindow(WIN, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WIN, 1280, 500)
    cv2.setWindowProperty(WIN, cv2.WND_PROP_TOPMOST, 1)

    PANEL_H = 480
    result  = None

    while True:
        ret, frame = cam.read()
        if not ret or frame is None:
            continue

        fh, fw = frame.shape[:2]
        cx, cy = fw // 2, fh // 2
        r      = min(fw, fh) // 5

        # Left: full frame with circle overlay
        left_disp = frame.copy()
        cv2.circle(left_disp, (cx, cy), r, (0, 200, 255), 2)
        cv2.line(left_disp, (cx - r, cy), (cx + r, cy), (0, 200, 255), 1)
        cv2.line(left_disp, (cx, cy - r), (cx, cy + r), (0, 200, 255), 1)
        cv2.putText(left_disp, "Centre pill in circle",
                    (10, fh - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (180, 180, 180), 1)

        lw         = int(fw * PANEL_H / fh)
        left_panel = cv2.resize(left_disp, (lw, PANEL_H), interpolation=cv2.INTER_AREA)

        # Right: zoomed pill region
        pad  = 20
        rx1  = max(0, cx - r - pad);  rx2 = min(fw, cx + r + pad)
        ry1  = max(0, cy - r - pad);  ry2 = min(fh, cy + r + pad)
        crop = frame[ry1:ry2, rx1:rx2]
        cw, ch = rx2 - rx1, ry2 - ry1
        rw         = int(cw * PANEL_H / ch) if ch > 0 else PANEL_H
        right_panel = cv2.resize(crop, (rw, PANEL_H), interpolation=cv2.INTER_CUBIC)
        cv2.putText(right_panel, "Zoomed",
                    (8, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 200, 255), 2)

        divider  = np.full((PANEL_H, 4, 3), 60, dtype=np.uint8)
        combined = np.hstack([left_panel, divider, right_panel])
        cv2.putText(combined, "Place pill inside circle, then press SPACE to capture",
                    (8, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 200, 255), 2)

        cv2.imshow(WIN, combined)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        if key == ord(' '):
            result = frame.copy()
            break

    cam.release()
    cv2.destroyAllWindows()
    return result


# ── OpenFDA pill lookup ────────────────────────────────────────────────────

def lookup_rximage(imprint="", colour="", shape=""):
    """
    Searches the OpenFDA drug label database via the how_supplied field,
    which contains imprint, colour, and shape descriptions.
    Returns a list of normalised result dicts.
    """
    if not imprint and (not colour or colour == "UNKNOWN"):
        return []

    # Build query — imprint is the most specific; add colour as extra filter
    parts = []
    if imprint:
        parts.append(f'how_supplied:"{urllib.parse.quote(imprint)}"')
    if colour and colour not in ("UNKNOWN", ""):
        parts.append(f'how_supplied:"{urllib.parse.quote(colour.lower())}"')

    query  = "+AND+".join(parts)
    url    = f"https://api.fda.gov/drug/label.json?search={query}&limit=10"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "BioMed4000/1.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode())
        results = data.get("results", [])
    except Exception:
        return []

    normalised = []
    seen = set()
    for r in results:
        ofd         = r.get("openfda", {})
        brand       = (ofd.get("brand_name")   or [""])[0]
        generic     = (ofd.get("generic_name") or [""])[0]
        dosage_form = (ofd.get("dosage_form")  or [""])[0]
        route       = (ofd.get("route")        or [""])[0]
        strength    = (ofd.get("strength")     or [""])[0]
        supplied    = (r.get("how_supplied")   or [""])[0]

        name = brand or generic
        key  = (name, strength)
        if key in seen:
            continue
        seen.add(key)

        # Trim the how_supplied text to a readable excerpt
        supplied_short = supplied[:220].replace("\n", " ").strip()
        if len(supplied) > 220:
            supplied_short += "…"

        normalised.append({
            "name":         name,
            "generic":      generic,
            "brand":        brand,
            "strength":     strength,
            "dosage_form":  dosage_form,
            "route":        route,
            "how_supplied": supplied_short,
        })

    return normalised
