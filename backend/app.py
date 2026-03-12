"""
app.py  —  Flask backend for Edge AI Emotion + Music Recommendation
============================================================
Wires together:
  • emotion/detector.py   → detect_emotion()
      returns: {"status": "success"|"fail", "emotion": str, "confidence": float}
               OR {"status": "fail", "reason": str}

  • music/spotify_engine.py → get_music_recommendation(language, emotion)
      returns: list of {
          "song_name", "artist_name", "movie_name",
          "preview_url", "full_song_url"
      }

API endpoints:
  GET  /                          → system status
  POST /detect-emotion            → triggers webcam capture & FER detection
  GET  /recommend-music           → ?emotion=&language=  → song list
  GET  /status                    → health check JSON
"""

import os
import sys
import logging

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

# ── Path setup ────────────────────────────────────────────────────────────────
BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR     = os.path.dirname(BASE_DIR)
FRONTEND_DIR = os.path.join(ROOT_DIR, "frontend")

sys.path.insert(0, BASE_DIR)   # lets Python find emotion/ and music/ packages

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("app")

# ── Flask app ─────────────────────────────────────────────────────────────────
app = Flask(
    __name__,
    static_folder=FRONTEND_DIR,   # serves frontend/ as the web root
    static_url_path="",
)
CORS(app)   # allow browser JS on the same host to call the API

# ── Import your modules (lazy-safe; errors surface as 500 at call-time) ───────
try:
    from emotion.detector import detect_emotion_from_image
    logger.info("emotion.detector loaded OK")
except Exception as e:
    logger.error(f"Could not import emotion.detector: {e}")
    detect_emotion_from_image = None

try:
    from music.spotify_engine import get_music_recommendation
    logger.info("music.spotify_engine loaded OK")
except Exception as e:
    logger.error(f"Could not import music.spotify_engine: {e}")
    get_music_recommendation = None


# ── Helpers ───────────────────────────────────────────────────────────────────
VALID_EMOTIONS = {"happy", "sad", "angry", "fear", "disgust", "surprise", "neutral"}

def _ok(payload: dict, code: int = 200):
    payload["success"] = True
    return jsonify(payload), code

def _err(message: str, code: int = 400):
    return jsonify({"success": False, "error": message}), code


# ── Frontend routes ───────────────────────────────────────────────────────────
@app.route("/")
def index():
    """Serve the main UI."""
    return send_from_directory(FRONTEND_DIR, "index.html")

@app.route("/<path:filename>")
def static_files(filename):
    """Serve CSS / JS / images."""
    return send_from_directory(FRONTEND_DIR, filename)


# ── Health check ─────────────────────────────────────────────────────────────
@app.route("/status", methods=["GET"])
def status():
    """
    GET /status
    Quick health check — lets the frontend verify the server is reachable.
    """
    return _ok({
        "server": "online",
        "detector_ready":  detect_emotion is not None,
        "spotify_ready":   get_music_recommendation is not None,
        "version": "1.0.0",
    })


# ── Detect Emotion ────────────────────────────────────────────────────────────
@app.route("/detect-emotion", methods=["POST"])
def api_detect_emotion():
    """
    POST /detect-emotion
    Body: { "image": "<base64 string with or without data-URI prefix>" }

    The browser captures a frame from the live video, converts it to base64,
    and sends it here. detect_emotion_from_image() runs FER + MediaPipe on
    that single frame — no server-side webcam, no cv2.imshow, no GUI needed.

    Success response:
    {
        "success": true,
        "emotion": "happy",
        "confidence": 0.87,
        "all_emotions": { "happy":0.87, "neutral":0.05, ... }
    }

    Failure response:
    {
        "success": false,
        "error": "human-readable reason"
    }
    """
    if detect_emotion_from_image is None:
        return _err("Emotion detector module failed to load. Check server logs.", 500)

    # ── Parse request body ────────────────────────────────────────────────────
    body = request.get_json(silent=True) or {}
    image_data = body.get("image", "").strip()

    if not image_data:
        return _err("No image received. Ensure the browser sent a base64 frame.", 400)

    try:
        logger.info("Running detect_emotion_from_image()…")
        result = detect_emotion_from_image(image_data)
        logger.info(f"Result: {result.get('status')} / {result.get('emotion','—')}")

        # ── SUCCESS ───────────────────────────────────────────────────────────
        if result.get("status") == "success":
            emotion      = result["emotion"].lower()
            confidence   = float(result.get("confidence", 0.0))
            all_emotions = result.get("all_emotions", {})

            # If detector didn't return all_emotions, build a minimal version
            if not all_emotions:
                remaining_pool = max(0.0, round(1.0 - confidence, 4))
                other_emotions = [e for e in VALID_EMOTIONS if e != emotion]
                per_other      = round(remaining_pool / len(other_emotions), 4) if other_emotions else 0.0
                all_emotions   = {e: per_other for e in other_emotions}
                all_emotions[emotion] = confidence

            return _ok({
                "emotion":      emotion,
                "confidence":   confidence,
                "all_emotions": all_emotions,
            })

        # ── FAIL ──────────────────────────────────────────────────────────────
        else:
            reason = result.get("reason", "Detection failed. Please try again.")
            logger.warning(f"Detection failed: {reason}")
            return _err(reason, 422)

    except Exception as e:
        logger.exception("Unexpected error in /detect-emotion")
        return _err(f"Internal error: {str(e)}", 500)


# ── Music Recommendation ──────────────────────────────────────────────────────
@app.route("/recommend-music", methods=["GET"])
def api_recommend_music():
    """
    GET /recommend-music?emotion=happy&language=hindi

    Calls get_music_recommendation(language, emotion)  ← note argument order
    Your spotify_engine returns list of:
        { song_name, artist_name, movie_name, preview_url, full_song_url }

    We re-map to frontend-friendly keys AND keep the originals so nothing breaks:
        name        ← song_name
        artist      ← artist_name
        album       ← movie_name
        album_image ← "" (Spotify search doesn't return images in your engine)
        spotify_url ← full_song_url
        preview_url ← preview_url
    """
    emotion  = request.args.get("emotion",  "").strip().lower()
    language = request.args.get("language", "").strip().lower()

    if not emotion:
        return _err("'emotion' query parameter is required.")
    if emotion not in VALID_EMOTIONS:
        return _err(f"Invalid emotion '{emotion}'. Must be one of: {', '.join(sorted(VALID_EMOTIONS))}.")
    if not language:
        return _err("'language' query parameter is required.")

    if get_music_recommendation is None:
        return _err("Music recommendation module failed to load. Check server logs.", 500)

    try:
        logger.info(f"Fetching music: emotion={emotion}, language={language}")
        # ← your function signature is get_music_recommendation(language, emotion)
        raw_songs = get_music_recommendation(language, emotion)

        if not raw_songs:
            logger.warning("Spotify returned an empty list.")
            return _ok({"emotion": emotion, "language": language, "songs": [], "count": 0})

        # Normalise keys so the frontend has a stable contract
        songs = []
        for s in raw_songs:
            songs.append({
                # frontend-contract keys
                "name":        s.get("song_name", "Unknown"),
                "artist":      s.get("artist_name", "Unknown Artist"),
                "album":       s.get("movie_name", ""),
                "album_image": s.get("album_image", ""),   # empty unless engine adds it
                "spotify_url": s.get("full_song_url", ""),
                "preview_url": s.get("preview_url", ""),
                # originals kept alongside (harmless)
                "song_name":   s.get("song_name", ""),
                "artist_name": s.get("artist_name", ""),
                "movie_name":  s.get("movie_name", ""),
                "full_song_url": s.get("full_song_url", ""),
            })

        logger.info(f"Returning {len(songs)} songs.")
        return _ok({
            "emotion":  emotion,
            "language": language,
            "songs":    songs,
            "count":    len(songs),
        })

    except Exception as e:
        logger.exception("Unexpected error in /recommend-music")
        return _err(f"Internal error: {str(e)}", 500)


# ── Error handlers ────────────────────────────────────────────────────────────
@app.errorhandler(404)
def not_found(e):
    return _err("Endpoint not found.", 404)

@app.errorhandler(405)
def method_not_allowed(e):
    return _err("Method not allowed.", 405)

@app.errorhandler(500)
def server_error(e):
    return _err("Internal server error.", 500)


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    from config import FLASK_HOST, FLASK_PORT, FLASK_DEBUG
    logger.info("=" * 55)
    logger.info("  Edge AI Emotion + Music  —  starting server")
    logger.info(f"  http://{FLASK_HOST}:{FLASK_PORT}")
    logger.info("=" * 55)
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=FLASK_DEBUG)