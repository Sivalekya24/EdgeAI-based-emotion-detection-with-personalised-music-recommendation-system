import cv2
import numpy as np
import base64
import time
from fer import FER
import mediapipe as mp
from config import (
    CONFIDENCE_THRESHOLD, MIN_FACE_AREA, MAX_FACE_AREA,
    MIN_BRIGHTNESS, ALIGNMENT_TOLERANCE, STABILITY_TOLERANCE, COUNTDOWN_SECONDS
)
from emotion.validation import check_brightness, check_landmark_stability

# Initialize once to save memory
detector = FER(mtcnn=True)
mp_face_mesh = mp.solutions.face_mesh


# =============================================================================
# NEW — used by Flask / web frontend
# Browser captures a frame, converts to base64, POSTs it here.
# No cv2.imshow / cv2.waitKey / webcam needed.
# =============================================================================
def detect_emotion_from_image(image_data: str) -> dict:
    """
    Accept a base64-encoded image string (with or without data-URI prefix),
    run the same FER + MediaPipe validation pipeline, and return a result dict.

    Returns on success:
        {"status": "success", "emotion": str, "confidence": float, "all_emotions": dict}

    Returns on failure:
        {"status": "fail", "reason": str}
    """
    # ── 1. Decode base64 → OpenCV frame ──────────────────────────────────────
    try:
        if "," in image_data:
            image_data = image_data.split(",", 1)[1]
        img_bytes = base64.b64decode(image_data)
        np_arr    = np.frombuffer(img_bytes, dtype=np.uint8)
        frame     = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if frame is None:
            return {"status": "fail", "reason": "Could not decode image from browser."}
    except Exception as e:
        return {"status": "fail", "reason": f"Image decode error: {str(e)}"}

    height, width = frame.shape[:2]
    center_x, center_y = width // 2, height // 2

    # ── 2. Brightness check ───────────────────────────────────────────────────
    if not check_brightness(frame, MIN_BRIGHTNESS):
        return {"status": "fail", "reason": "Low Light! Please increase your room lighting."}

    # ── 3. FER detection ──────────────────────────────────────────────────────
    result = detector.detect_emotions(frame)
    if not result:
        return {"status": "fail", "reason": "No face detected. Centre your face and try again."}

    # ── 4. MediaPipe face mesh (stability / tilt check) ───────────────────────
    rgb_frame    = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    with mp_face_mesh.FaceMesh(refine_landmarks=True, max_num_faces=1) as face_mesh:
        mesh_results = face_mesh.process(rgb_frame)

    if not mesh_results.multi_face_landmarks:
        return {"status": "fail", "reason": "Face landmarks not detected. Look straight at the camera."}

    # ── 5. Geometry checks ────────────────────────────────────────────────────
    box = result[0]["box"]
    x, y, w, h   = box
    face_area     = w * h
    face_center_x = x + w // 2
    face_center_y = y + h // 2
    dist_from_center = np.sqrt((face_center_x - center_x)**2 + (face_center_y - center_y)**2)
    stable = check_landmark_stability(mesh_results, STABILITY_TOLERANCE)

    if face_area < MIN_FACE_AREA:
        return {"status": "fail", "reason": "Move Closer — your face is too far from the camera."}
    if face_area > MAX_FACE_AREA:
        return {"status": "fail", "reason": "Move Back Slightly — your face is too close."}
    if dist_from_center > ALIGNMENT_TOLERANCE:
        return {"status": "fail", "reason": "Align Face in Center of the frame."}
    if not stable:
        return {"status": "fail", "reason": "Keep Face Straight — slight tilt detected."}

    # ── 6. Confidence check ───────────────────────────────────────────────────
    emotions   = result[0]["emotions"]
    emotion    = max(emotions, key=emotions.get)
    confidence = emotions[emotion]

    if confidence < CONFIDENCE_THRESHOLD:
        return {
            "status": "fail",
            "reason": f"Expression unclear (confidence {confidence:.0%}). Try a stronger expression."
        }

    # ── 7. Build all_emotions dict (normalised 0-1) ───────────────────────────
    total = sum(emotions.values()) or 1.0
    all_emotions = {k: round(v / total, 4) for k, v in emotions.items()}

    return {
        "status":      "success",
        "emotion":     emotion,
        "confidence":  round(float(confidence), 2),
        "all_emotions": all_emotions,
    }


# =============================================================================
# ORIGINAL — kept intact for local / CLI testing only.
# Do NOT call this from Flask; cv2.imshow crashes in headless environments.
# =============================================================================
def detect_emotion():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        return {"status": "fail", "reason": "Camera Not Accessible"}

    countdown_started = False
    start_time = None

    with mp_face_mesh.FaceMesh(refine_landmarks=True, max_num_faces=1) as face_mesh:
        while True:
            ret, frame = cap.read()
            if not ret: break

            height, width, _ = frame.shape
            center_x, center_y = width // 2, height // 2

            brightness_ok = check_brightness(frame, MIN_BRIGHTNESS)
            result        = detector.detect_emotions(frame)
            rgb_frame     = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mesh_results  = face_mesh.process(rgb_frame)

            message = "Looking for face..."

            if not brightness_ok:
                message = "Low Light! Increase lighting."
                countdown_started = False
            elif result and mesh_results.multi_face_landmarks:
                box = result[0]["box"]
                x, y, w, h = box
                face_area     = w * h
                face_center_x = x + (w // 2)
                face_center_y = y + (h // 2)
                dist_from_center = np.sqrt((face_center_x - center_x)**2 + (face_center_y - center_y)**2)
                stable = check_landmark_stability(mesh_results, STABILITY_TOLERANCE)

                if face_area < MIN_FACE_AREA:
                    message = "Move Closer"; countdown_started = False
                elif face_area > MAX_FACE_AREA:
                    message = "Move Back Slightly"; countdown_started = False
                elif dist_from_center > ALIGNMENT_TOLERANCE:
                    message = "Align Face in Center"; countdown_started = False
                elif not stable:
                    message = "Keep Face Straight"; countdown_started = False
                else:
                    if not countdown_started:
                        countdown_started = True
                        start_time = time.time()
                    remaining = COUNTDOWN_SECONDS - int(time.time() - start_time)
                    if remaining > 0:
                        message = f"Capturing in {remaining}..."
                    else:
                        emotions   = result[0]["emotions"]
                        emotion    = max(emotions, key=emotions.get)
                        confidence = emotions[emotion]
                        if confidence < CONFIDENCE_THRESHOLD:
                            message = "Expression unclear. Retrying..."
                            countdown_started = False
                        else:
                            cap.release()
                            cv2.destroyAllWindows()
                            return {
                                "status":     "success",
                                "emotion":    emotion,
                                "confidence": round(float(confidence), 2)
                            }
            else:
                countdown_started = False

            color = (0, 255, 0) if countdown_started else (0, 0, 255)
            cv2.putText(frame, message, (30, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
            cv2.circle(frame, (center_x, center_y), ALIGNMENT_TOLERANCE, (0, 255, 0), 2)
            cv2.imshow("Edge AI Capture", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'): break

    cap.release()
    cv2.destroyAllWindows()
    return {"status": "fail", "reason": "User Interrupted"}