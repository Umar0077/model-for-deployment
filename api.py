"""
FastAPI backend for Emotion Detection Model
Exposes emotion detection as an HTTP service for Flutter interview app
"""

import os
import uuid
import base64
import logging
import threading
import io
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict, Counter

import cv2
import numpy as np
import tensorflow as tf
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Header, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel
from PIL import Image

from src.face_detector import detect_faces
from src.utils import preprocess_face, emotion_labels

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s , %(name)s , %(levelname)s , %(message)s"
)
logger = logging.getLogger(__name__)

# Thread lock for session access
session_lock = threading.Lock()

# Environment configuration
API_KEY = os.environ.get("API_KEY", None)
MAX_FRAMES_PER_EMOTION = int(os.environ.get("MAX_FRAMES_PER_EMOTION", "10"))
SESSION_TIMEOUT_MINUTES = int(os.environ.get("SESSION_TIMEOUT_MINUTES", "30"))
INPUT_FRAME_MAX_WIDTH = int(os.environ.get("INPUT_FRAME_MAX_WIDTH", "1280"))

# Load model once on startup
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "model", "emotion_efficientnet.keras")

logger.info(f"Loading model from {MODEL_PATH}")
model = tf.keras.models.load_model(MODEL_PATH)
logger.info("Model loaded successfully")


# Pydantic models
class StartSessionResponse(BaseModel):
    session_id: str
    started_at: str


class StopSessionRequest(BaseModel):
    session_id: str


class ResetSessionRequest(BaseModel):
    session_id: str


class FaceResult(BaseModel):
    emotion: str
    confidence: float
    bbox: Tuple[int, int, int, int]


class PredictFrameResponse(BaseModel):
    faces_found: int
    top_result: Optional[FaceResult]
    results: List[FaceResult]
    stored_frame_update: Optional[Dict[str, int]]


class SavedFrame(BaseModel):
    timestamp: str
    confidence: float
    frame_base64: str


class SessionReport(BaseModel):
    session_id: str
    duration_seconds: float
    emotion_counts: Dict[str, int]
    average_confidence: Dict[str, float]
    timeline: List[Dict[str, Any]]
    saved_frames: Dict[str, List[SavedFrame]]
    summary: Dict[str, Any]


class SessionData:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.started_at = datetime.now()
        self.last_activity = datetime.now()
        self.timeline: List[Dict[str, Any]] = []
        self.emotion_counts: Counter = Counter()
        self.emotion_confidences: Dict[str, List[float]] = defaultdict(list)
        self.saved_frames: Dict[str, List[Tuple[float, datetime, bytes]]] = defaultdict(list)

    def is_expired(self) -> bool:
        return datetime.now() - self.last_activity > timedelta(minutes=SESSION_TIMEOUT_MINUTES)

    def update_activity(self) -> None:
        self.last_activity = datetime.now()


sessions: Dict[str, SessionData] = {}


async def verify_api_key(x_api_key: Optional[str] = Header(None)):
    if API_KEY is not None:
        if x_api_key is None or x_api_key != API_KEY:
            raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return True


def cleanup_expired_sessions() -> None:
    expired_ids = [sid for sid, sess in sessions.items() if sess.is_expired()]
    for sid in expired_ids:
        del sessions[sid]
        logger.info(f"Cleaned up expired session: {sid}")


def detect_image_format(file_bytes: bytes) -> Optional[str]:
    if len(file_bytes) < 4:
        return None

    if file_bytes[0:3] == b"\xff\xd8\xff":
        return "JPEG"

    if file_bytes[0:8] == b"\x89\x50\x4e\x47\x0d\x0a\x1a\x0a":
        return "PNG"

    if file_bytes[0:4] == b"RIFF" and file_bytes[8:12] == b"WEBP":
        return "WEBP"

    return None


def decode_image_from_upload(
    file_bytes: bytes,
    content_type: Optional[str] = None,
    filename: Optional[str] = None
) -> Tuple[Optional[np.ndarray], Optional[Dict[str, Any]]]:
    if len(file_bytes) == 0:
        return None, {
            "error_code": "EMPTY_FILE",
            "message": "Received empty file with 0 bytes",
            "content_type": content_type,
            "filename": filename,
            "size_bytes": 0,
            "first_32_bytes_hex": "",
            "detected_format": None,
        }

    detected_format = detect_image_format(file_bytes)
    first_32_hex = file_bytes[:32].hex()

    logger.info(
        f"Image analysis: size={len(file_bytes)} bytes, content_type={content_type}, "
        f"filename={filename}, detected_format={detected_format}"
    )
    logger.info(f"First 32 bytes hex: {first_32_hex}")

    try:
        nparr = np.frombuffer(file_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            logger.warning("OpenCV decode failed, trying PIL fallback")
            pil_img = Image.open(io.BytesIO(file_bytes))
            if pil_img.mode != "RGB":
                pil_img = pil_img.convert("RGB")
            img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

        if img is None:
            raise ValueError("Image decode returned None")

        height, width = img.shape[:2]
        if width > INPUT_FRAME_MAX_WIDTH:
            scale = INPUT_FRAME_MAX_WIDTH / width
            new_width = INPUT_FRAME_MAX_WIDTH
            new_height = int(height * scale)
            img = cv2.resize(img, (new_width, new_height))
            logger.info(f"Resized frame from {width}x{height} to {new_width}x{new_height}")

        logger.info(f"Image decode successful: shape={img.shape}")
        return img, None

    except Exception as e:
        logger.error(f"Image decode failed: {e}", exc_info=True)
        return None, {
            "error_code": "DECODE_FAILED",
            "message": f"Failed to decode image. Error: {str(e)}",
            "content_type": content_type,
            "filename": filename,
            "size_bytes": len(file_bytes),
            "first_32_bytes_hex": first_32_hex,
            "detected_format": detected_format,
        }


def store_frame_for_emotion(
    session: SessionData,
    emotion: str,
    confidence: float,
    timestamp: datetime,
    frame: np.ndarray
) -> None:
    success, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
    if not success:
        return

    frame_bytes = buffer.tobytes()
    frames_list = session.saved_frames[emotion]
    frames_list.append((confidence, timestamp, frame_bytes))
    frames_list.sort(key=lambda x: (-x[0], x[1]))

    if len(frames_list) > MAX_FRAMES_PER_EMOTION:
        filtered: List[Tuple[float, datetime, bytes]] = []
        last_timestamp: Optional[datetime] = None
        min_time_gap = timedelta(seconds=2)

        for conf, ts, fb in frames_list:
            if last_timestamp is None or (ts - last_timestamp) >= min_time_gap:
                filtered.append((conf, ts, fb))
                last_timestamp = ts
                if len(filtered) >= MAX_FRAMES_PER_EMOTION:
                    break

        if len(filtered) < MAX_FRAMES_PER_EMOTION:
            filtered = frames_list[:MAX_FRAMES_PER_EMOTION]

        session.saved_frames[emotion] = filtered


def get_session_or_error(session_id: str) -> SessionData:
    cleanup_expired_sessions()

    if session_id not in sessions:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found or expired")

    session = sessions[session_id]
    session.update_activity()
    return session


app = FastAPI(
    title="Emotion Detection API",
    description="Real time emotion detection for interview analysis",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    logger.info("=" * 60)
    logger.info("Emotion Detection API Server Starting")
    logger.info(f"Model: {MODEL_PATH}")
    logger.info(f"API Key Protection: {'ENABLED' if API_KEY else 'DISABLED'}")
    logger.info(f"Max Frames per Emotion: {MAX_FRAMES_PER_EMOTION}")
    logger.info(f"Session Timeout: {SESSION_TIMEOUT_MINUTES} minutes")
    logger.info("Registered Routes:")
    for route in app.routes:
        if hasattr(route, "methods"):
            methods = ", ".join(route.methods)
            logger.info(f"  {methods:8s} {route.path}")
    logger.info("=" * 60)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = datetime.now()
    client_host = request.client.host if request.client else "unknown"
    logger.info(f"REQUEST: {request.method} {request.url.path} from {client_host}")

    try:
        response = await call_next(request)
        duration = (datetime.now() - start_time).total_seconds()
        logger.info(
            f"RESPONSE: {request.method} {request.url.path} -> "
            f"Status {response.status_code} ({duration:.3f}s)"
        )
        return response
    except Exception as e:
        duration = (datetime.now() - start_time).total_seconds()
        logger.error(
            f"ERROR: {request.method} {request.url.path} -> {str(e)} ({duration:.3f}s)",
            exc_info=True
        )
        raise


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error(f"Validation error on {request.method} {request.url.path}")
    logger.error(f"Details: {exc.errors()}")
    logger.error(f"Body: {exc.body}")

    return JSONResponse(
        status_code=422,
        content={
            "detail": "Validation error. Check request format.",
            "errors": exc.errors(),
            "message": "Request does not match expected format.",
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error": str(exc),
        },
    )


@app.get("/health")
async def health_check():
    cleanup_expired_sessions()
    with session_lock:
        active_count = len(sessions)

    logger.info(f"Health check: {active_count} active sessions")

    return {
        "status": "healthy",
        "model_loaded": model is not None,
        "active_sessions": active_count,
        "timestamp": datetime.now().isoformat(),
    }


@app.post("/start_session", response_model=StartSessionResponse, dependencies=[Depends(verify_api_key)])
async def start_session():
    cleanup_expired_sessions()

    session_id = str(uuid.uuid4())
    session = SessionData(session_id)

    with session_lock:
        sessions[session_id] = session

    logger.info(f"Session started: {session_id}")

    return StartSessionResponse(
        session_id=session_id,
        started_at=session.started_at.isoformat(),
    )


@app.post("/predict_frame", response_model=PredictFrameResponse, dependencies=[Depends(verify_api_key)])
async def predict_frame(
    session_id: str = Form(...),
    frame: Optional[UploadFile] = File(None),
    file: Optional[UploadFile] = File(None),
    image: Optional[UploadFile] = File(None),
):
    session = get_session_or_error(session_id)

    uploaded_image = frame or file or image
    if uploaded_image is None:
        return JSONResponse(
            status_code=400,
            content={
                "error_code": "MISSING_FILE",
                "message": "No image file provided. Use field name frame, file, or image.",
                "accepted_field_names": ["frame", "file", "image"],
            },
        )

    try:
        file_bytes = await uploaded_image.read()

        logger.info(f"FRAME RECEIVED: Session {session_id}")
        logger.info(f"Content Type: {uploaded_image.content_type}")
        logger.info(f"Filename: {uploaded_image.filename}")
        logger.info(f"Size: {len(file_bytes)} bytes")

        decoded_frame, error_info = decode_image_from_upload(
            file_bytes=file_bytes,
            content_type=uploaded_image.content_type,
            filename=uploaded_image.filename,
        )

        if decoded_frame is None:
            logger.error(f"Invalid image format for session {session_id}")
            return JSONResponse(status_code=400, content=error_info)

        frame_img = decoded_frame

    except Exception as e:
        logger.error(f"Error reading frame for session {session_id}: {e}", exc_info=True)
        return JSONResponse(
            status_code=400,
            content={
                "error_code": "PROCESSING_ERROR",
                "message": f"Error processing image: {str(e)}",
            },
        )

    faces = detect_faces(frame_img)
    timestamp = datetime.now()

    if len(faces) == 0:
        logger.info(f"No faces detected in frame for session {session_id}")
        return PredictFrameResponse(
            faces_found=0,
            top_result=None,
            results=[],
            stored_frame_update=None,
        )

    results: List[FaceResult] = []
    top_result: Optional[FaceResult] = None
    top_confidence = 0.0
    stored_update: Dict[str, int] = defaultdict(int)

    for (x, y, w, h) in faces:
        face = frame_img[y:y + h, x:x + w]
        face_input = preprocess_face(face)

        preds = model.predict(face_input, verbose=0)
        emotion_idx = int(np.argmax(preds))
        emotion = emotion_labels[emotion_idx]
        confidence = float(np.max(preds))

        with session_lock:
            session.emotion_counts[emotion] += 1
            session.emotion_confidences[emotion].append(confidence)
            session.timeline.append({
                "timestamp": timestamp.isoformat(),
                "emotion": emotion,
                "confidence": confidence,
            })

            store_frame_for_emotion(session, emotion, confidence, timestamp, face)
            stored_update[emotion] = len(session.saved_frames[emotion])

        face_result = FaceResult(
            emotion=emotion,
            confidence=confidence,
            bbox=(int(x), int(y), int(w), int(h)),
        )
        results.append(face_result)

        if confidence > top_confidence:
            top_confidence = confidence
            top_result = face_result

        logger.info(
            f"EMOTION DETECTED: Session {session_id}, Emotion: {emotion}, Confidence: {confidence:.2f}"
        )

    with session_lock:
        total_frames = sum(session.emotion_counts.values())

    if total_frames > 0 and total_frames % 10 == 0:
        logger.info(
            f"PROGRESS: Session {session_id}, Processed {total_frames} frames, "
            f"Emotions: {dict(session.emotion_counts)}"
        )

    return PredictFrameResponse(
        faces_found=len(faces),
        top_result=top_result,
        results=results,
        stored_frame_update=dict(stored_update) if stored_update else None,
    )


@app.post("/stop_session", response_model=SessionReport, dependencies=[Depends(verify_api_key)])
async def stop_session(request: StopSessionRequest):
    session = get_session_or_error(request.session_id)
    duration = (datetime.now() - session.started_at).total_seconds()

    with session_lock:
        avg_confidence: Dict[str, float] = {}
        for emotion, confidences in session.emotion_confidences.items():
            if confidences:
                avg_confidence[emotion] = sum(confidences) / len(confidences)

        saved_frames_output: Dict[str, List[SavedFrame]] = {}
        for emotion, frames_list in session.saved_frames.items():
            saved_frames_output[emotion] = [
                SavedFrame(
                    timestamp=ts.isoformat(),
                    confidence=conf,
                    frame_base64=base64.b64encode(fb).decode("utf-8"),
                )
                for conf, ts, fb in frames_list
            ]

        dominant_emotions: List[Dict[str, Any]] = []
        if session.emotion_counts:
            most_common = session.emotion_counts.most_common(3)
            total_count = sum(session.emotion_counts.values())
            dominant_emotions = [
                {
                    "emotion": emotion,
                    "count": count,
                    "percentage": (count / total_count) * 100,
                }
                for emotion, count in most_common
            ]

        total_conf_sum = sum(sum(c) for c in session.emotion_confidences.values())
        total_conf_len = sum(len(c) for c in session.emotion_confidences.values())
        average_confidence_overall = round(total_conf_sum / total_conf_len, 3) if total_conf_len > 0 else 0.0

        session_quality = "moderate"
        if avg_confidence:
            session_quality = "good" if (sum(avg_confidence.values()) / len(avg_confidence)) > 0.7 else "moderate"

        summary = {
            "total_duration_seconds": round(duration, 2),
            "total_frames_processed": sum(session.emotion_counts.values()),
            "dominant_emotions": dominant_emotions,
            "emotion_distribution": dict(session.emotion_counts),
            "average_confidence_overall": average_confidence_overall,
            "unique_emotions_detected": len(session.emotion_counts),
            "session_quality": session_quality,
        }

        report = SessionReport(
            session_id=request.session_id,
            duration_seconds=round(duration, 2),
            emotion_counts=dict(session.emotion_counts),
            average_confidence=avg_confidence,
            timeline=session.timeline,
            saved_frames=saved_frames_output,
            summary=summary,
        )

        logger.info(f"SESSION STOPPED: {request.session_id}")
        logger.info(f"REPORT GENERATED: Duration={duration:.1f}s, Total frames={sum(session.emotion_counts.values())}")
        logger.info(f"FINAL EMOTIONS: {dict(session.emotion_counts)}")
        logger.info(f"DOMINANT: {dominant_emotions[0] if dominant_emotions else 'None'}")

    with session_lock:
        del sessions[request.session_id]

    return report


@app.post("/reset_session", dependencies=[Depends(verify_api_key)])
async def reset_session(request: ResetSessionRequest):
    session = get_session_or_error(request.session_id)

    with session_lock:
        session.last_activity = datetime.now()
        session.timeline = []
        session.emotion_counts = Counter()
        session.emotion_confidences = defaultdict(list)
        session.saved_frames = defaultdict(list)

    logger.info(f"SESSION RESET: {request.session_id}")

    return {
        "status": "success",
        "message": f"Session {request.session_id} has been reset",
        "session_id": request.session_id,
    }


@app.get("/")
async def root():
    return {
        "name": "Emotion Detection API",
        "version": "1.0.0",
        "endpoints": {
            "health": "GET /health",
            "start_session": "POST /start_session",
            "predict_frame": "POST /predict_frame",
            "stop_session": "POST /stop_session",
            "reset_session": "POST /reset_session",
        },
        "documentation": "/docs",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, log_level="info")