"""
config.py  —  All tunable constants for the Edge AI Emotion project.
detector.py imports: CONFIDENCE_THRESHOLD, MIN_FACE_AREA, MAX_FACE_AREA,
                     MIN_BRIGHTNESS, ALIGNMENT_TOLERANCE, STABILITY_TOLERANCE,
                     COUNTDOWN_SECONDS
"""

# ── Emotion Detection ─────────────────────────────────────────────────────────
CONFIDENCE_THRESHOLD  = 0.45   # Minimum FER confidence to accept a result
MIN_FACE_AREA         = 8000   # px² — face too small → "Move Closer"
MAX_FACE_AREA         = 120000 # px² — face too large → "Move Back"
MIN_BRIGHTNESS        = 60     # 0–255 grayscale mean — below this: low light
ALIGNMENT_TOLERANCE   = 120    # px — max allowed distance from frame centre
STABILITY_TOLERANCE   = 0.04   # normalised Y-diff between eyes (head tilt)
COUNTDOWN_SECONDS     = 3      # seconds the face must stay stable before capture

# ── Flask Server ──────────────────────────────────────────────────────────────
FLASK_HOST  = "0.0.0.0"
FLASK_PORT  = 5000
FLASK_DEBUG = True