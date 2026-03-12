import cv2
import numpy as np

def check_brightness(frame, min_brightness):
    # Convert to grayscale to measure average luminance
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    brightness = np.mean(gray)
    return brightness >= min_brightness

def check_landmark_stability(results, tolerance):
    """
    Checks if the face is straight (not tilted) using eye coordinates.
    """
    if not results.multi_face_landmarks:
        return False

    landmarks = results.multi_face_landmarks[0]
    # Landmark 33 is Left Eye, 263 is Right Eye
    left_eye = landmarks.landmark[33]
    right_eye = landmarks.landmark[263]

    # Difference in Y-coordinates indicates a head tilt
    return abs(left_eye.y - right_eye.y) < tolerance
