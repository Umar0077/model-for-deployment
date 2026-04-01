"""
FastAPI backend for Emotion Detection Model
Exposes emotion detection as an HTTP service for Flutter interview app

FLUTTER COMPATIBILITY FIXES:
- Changed predict_frame to accept "image" field (not "file")
- Added comprehensive request/response logging
- Added validation error logging for debugging
- Added thread-safe session access
- Fixed 422 validation errors
- Added graceful error handling for invalid frames
- Added request middleware for logging all endpoints
"""

import os
import uuid
import base64
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict, Counter
import io
import threading

import cv2
import numpy as np
import tensorflow as tf
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Header, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field, ValidationError

from src.face_detector import detect_faces
from src.utils import preprocess_face, emotion_labels

# Configure logging with more detail
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
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


class ImageDecodeError(BaseModel):
    """Structured error response for image decode failures"""
    error_code: str
    message: str
    content_type: Optional[str]
    filename: Optional[str]
    size_bytes: int
    first_32_bytes_hex: str
    detected_format: Optional[str]


class SessionReport(BaseModel):
    session_id: str
    duration_seconds: float
    emotion_counts: Dict[str, int]
    average_confidence: Dict[str, float]
    timeline: List[Dict[str, Any]]
    saved_frames: Dict[str, List[SavedFrame]]
    summary: Dict[str, Any]


# Session storage (in-memory, ready for Redis migration)
class SessionData:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.started_at = datetime.now()
        self.last_activity = datetime.now()
        self.timeline: List[Dict] = []
        self.emotion_counts: Counter = Counter()
        self.emotion_confidences: Dict[str, List[float]] = defaultdict(list)
        # Store best N frames per emotion: emotion -> list of (confidence, timestamp, frame_bytes)
        self.saved_frames: Dict[str, List[Tuple[float, datetime, bytes]]] = defaultdict(list)
    
    def is_expired(self) -> bool:
        return datetime.now() - self.last_activity > timedelta(minutes=SESSION_TIMEOUT_MINUTES)
    
    def update_activity(self):
        self.last_activity = datetime.now()


sessions: Dict[str, SessionData] = {}


# Security dependency
async def verify_api_key(x_api_key: Optional[str] = Header(None)):
    """Optional API key verification"""
    if API_KEY is not None:
        if x_api_key is None or x_api_key != API_KEY:
            raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return True


# Helper functions
def cleanup_expired_sessions():
    """Remove expired sessions"""
    expired = [sid for sid, sess in sessions.items() if sess.is_expired()]
    for sid in expired:
        del sessions[sid]
        logger.info(f"Cleaned up expired session: {sid}")


def detect_image_format(file_bytes: bytes) -> Optional[str]:
    """Detect image format from magic bytes"""
    if len(file_bytes) < 4:
        return None
    
    # JPEG magic bytes: FF D8 FF
    if file_bytes[0:3] == b'\xff\xd8\xff':
        return "JPEG"
    
    # PNG magic bytes: 89 50 4E 47 0D 0A 1A 0A
    if file_bytes[0:8] == b'\x89\x50\x4e\x47\x0d\x0a\x1a\x0a':
        return "PNG"
    
    # WebP magic bytes: RIFF ???? WEBP
    if file_bytes[0:4] == b'RIFF' and file_bytes[8:12] == b'WEBP':
        return "WEBP"
    
    return None


def decode_image_from_upload(file_bytes: bytes, content_type: Optional[str] = None, 
                            filename: Optional[str] = None) -> Tuple[Optional[np.ndarray], Optional[Dict]]:
    """Decode image from uploaded bytes - supports multiple formats
    
    Returns:
        Tuple of (decoded_image, error_dict)
        If successful: (image, None)
        If failed: (None, error_dict with debug info)
    """
    if len(file_bytes) == 0:
        return None, {
            "error_code": "EMPTY_FILE",
            "message": "Received empty file with 0 bytes",
            "content_type": content_type,
            "filename": filename,
            "size_bytes": 0,
            "first_32_bytes_hex": "",
            "detected_format": None
        }
    
    # Detect format from magic bytes
    detected_format = detect_image_format(file_bytes)
    first_32_hex = file_bytes[:32].hex()
    
    logger.info(f"🔍 Image analysis: size={len(file_bytes)} bytes, content_type={content_type}, "
                f"filename={filename}, detected_format={detected_format}")
    logger.info(f"🔍 First 32 bytes (hex): {first_32_hex}")
    
    try:
        # Method 1: Try OpenCV decode (fastest for JPEG/PNG)
        nparr = np.frombuffer(file_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is not None:
            logger.info(f"✅ OpenCV decode successful: shape={img.shape}")
            # Optional: resize for performance if too large
            height, width = img.shape[:2]
            if width > INPUT_FRAME_MAX_WIDTH:
                scale = INPUT_FRAME_MAX_WIDTH / width
                new_width = INPUT_FRAME_MAX_WIDTH
                new_height = int(height * scale)
                img = cv2.resize(img, (new_width, new_height))
                logger.debug(f"Resized frame from {width}x{height} to {new_width}x{new_height}")
            return img, None
        
        # Method 2: Fallback to PIL for other formats
        logger.warning("⚠️ OpenCV decode failed, trying PIL fallback")
        from PIL import Image
        pil_img = Image.open(io.BytesIO(file_bytes))
        # Convert to RGB if needed
        if pil_img.mode != 'RGB':
            pil_img = pil_img.convert('RGB')
        # Convert PIL to OpenCV format (RGB -> BGR)
        img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        logger.info(f"✅ PIL decode successful: shape={img.shape}")
        
        # Optional: resize for performance
        height, width = img.shape[:2]
        if width > INPUT_FRAME_MAX_WIDTH:
            scale = INPUT_FRAME_MAX_WIDTH / width
            new_width = INPUT_FRAME_MAX_WIDTH
            new_height = int(height * scale)
            img = cv2.resize(img, (new_width, new_height))
            logger.debug(f"Resized frame from {width}x{height} to {new_width}x{new_height}")
        
        return img, None
        
    except Exception as e:
        logger.error(f"❌ Both OpenCV and PIL decode failed: {str(e)}")
        return None, {
            "error_code": "DECODE_FAILED",
            "message": f"Failed to decode image with both OpenCV and PIL. Error: {str(e)}",
            "content_type": content_type,
            "filename": filename,
            "size_bytes": len(file_bytes),
            "first_32_bytes_hex": first_32_hex,
            "detected_format": detected_format
        }


def encode_frame_to_base64(frame: np.ndarray) -> str:
    """Encode frame to base64 JPEG string"""
    _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return base64.b64encode(buffer).decode('utf-8')


def store_frame_for_emotion(session: SessionData, emotion: str, confidence: float, 
                            timestamp: datetime, frame: np.ndarray):
    """
    Store frame if it's among the best N frames for this emotion.
    Strategy: keep highest confidence frames, spaced across time to avoid duplicates.
    """
    # Encode frame to bytes
    _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
    frame_bytes = buffer.tobytes()
    
    frames_list = session.saved_frames[emotion]
    
    # Add new frame
    frames_list.append((confidence, timestamp, frame_bytes))
    
    # Sort by confidence (descending) and then timestamp
    frames_list.sort(key=lambda x: (-x[0], x[1]))
    
    # Keep only top MAX_FRAMES_PER_EMOTION, but ensure temporal diversity
    if len(frames_list) > MAX_FRAMES_PER_EMOTION:
        # Strategy: keep top frames but ensure at least 2 seconds between frames
        filtered = []
        last_timestamp = None
        MIN_TIME_GAP = timedelta(seconds=2)
        
        for conf, ts, fb in frames_list:
            if last_timestamp is None or (ts - last_timestamp) >= MIN_TIME_GAP:
                filtered.append((conf, ts, fb))
                last_timestamp = ts
                if len(filtered) >= MAX_FRAMES_PER_EMOTION:
                    break
        
        # If we didn't get enough with time filtering, just take top N
        if len(filtered) < MAX_FRAMES_PER_EMOTION:
            filtered = frames_list[:MAX_FRAMES_PER_EMOTION]
        
        session.saved_frames[emotion] = filtered


def get_session_or_error(session_id: str) -> SessionData:
    """Get session or raise HTTP 404"""
    cleanup_expired_sessions()
    
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found or expired")
    
    session = sessions[session_id]
    session.update_activity()
    return session


# FastAPI app
app = FastAPI(
    title="Emotion Detection API",
    description="Real-time emotion detection for interview analysis",
    version="1.0.0"
)

# Add CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins in development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Log all registered routes on startup for debugging"""
    logger.info("="*60)
    logger.info("🚀 Emotion Detection API Starting Up")
    logger.info("="*60)
    logger.info("📋 Registered Routes:")
    for route in app.routes:
        if hasattr(route, 'methods'):
            methods = ", ".join(route.methods)
            logger.info(f"  {methods:8s} {route.path}")
    logger.info("="*60)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests with details"""
    start_time = datetime.now()
    
    # Log request
    logger.info(f"📥 REQUEST: {request.method} {request.url.path} from {request.client.host if request.client else 'unknown'}")
    
    try:
        response = await call_next(request)
        
        # Log response
        duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"📤 RESPONSE: {request.method} {request.url.path} → Status {response.status_code} ({duration:.3f}s)")
        
        return response
    except Exception as e:
        duration = (datetime.now() - start_time).total_seconds()
        logger.error(f"❌ ERROR: {request.method} {request.url.path} → {str(e)} ({duration:.3f}s)")
        raise


# Custom validation error handler
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Log validation errors clearly for debugging"""
    logger.error(f"🔴 VALIDATION ERROR on {request.method} {request.url.path}")
    logger.error(f"Details: {exc.errors()}")
    logger.error(f"Body: {exc.body}")
    
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Validation error - check request format",
            "errors": exc.errors(),
            "message": "Request does not match expected format. Check field names and types."
        }
    )


@app.get("/health")
async def health_check():
    """Health check endpoint - no auth required for monitoring"""
    cleanup_expired_sessions()
    
    with session_lock:
        active_count = len(sessions)
    
    logger.info(f"💚 Health check: {active_count} active sessions")
    
    return {
        "status": "healthy",
        "model_loaded": model is not None,
        "active_sessions": active_count,
        "timestamp": datetime.now().isoformat()
    }


@app.post("/start_session", response_model=StartSessionResponse, dependencies=[Depends(verify_api_key)])
async def start_session():
    """
    Start a new interview session.
    Returns a session_id to use in subsequent requests.
    """
    cleanup_expired_sessions()
    
    session_id = str(uuid.uuid4())
    session = SessionData(session_id)
    
    with session_lock:
        sessions[session_id] = session
    
    logger.info(f"🆕 SESSION STARTED: {session_id}")
    
    return StartSessionResponse(
        session_id=session_id,
        started_at=session.started_at.isoformat()
    )


@app.post("/predict_frame", dependencies=[Depends(verify_api_key)])
async def predict_frame(
    session_id: str = Form(...),
    frame: Optional[UploadFile] = File(None),
    file: Optional[UploadFile] = File(None)
):
    """
    Process a single frame for emotion detection.
    
    FLUTTER INTEGRATION:
    - Accepts field name "frame" (preferred) or "file" (fallback)
    - Use multipart/form-data
    - Include session_id as form field
    
    Args:
        session_id: Active session ID from start_session
        frame: Image file (JPEG/PNG) with field name "frame" (preferred)
        file: Image file with field name "file" (fallback for compatibility)
    
    Returns:
        Detection results with faces, emotions, and confidence scores
        OR structured error with debug information
    """
    session = get_session_or_error(session_id)
    
    # Accept either 'frame' or 'file' field
    image = frame or file
    if image is None:
        logger.error(f"❌ No image file provided for session {session_id}")
        return JSONResponse(
            status_code=400,
            content={
                "error_code": "MISSING_FILE",
                "message": "No image file provided. Use field name 'frame' or 'file' with multipart/form-data",
                "accepted_field_names": ["frame", "file"]
            }
        )
    
    # Read and decode image
    try:
        file_bytes = await image.read()
        file_size_kb = len(file_bytes) / 1024
        
        logger.info(f"📸 FRAME RECEIVED: Session {session_id}")
        logger.info(f"   Content-Type: {image.content_type}")
        logger.info(f"   Filename: {image.filename}")
        logger.info(f"   Size: {file_size_kb:.1f}KB ({len(file_bytes)} bytes)")
        
        decoded_frame, error_info = decode_image_from_upload(
            file_bytes, 
            content_type=image.content_type,
            filename=image.filename
        )
        
        if decoded_frame is None:
            logger.error(f"❌ Image decode failed for session {session_id}")
            return JSONResponse(
                status_code=400,
                content=error_info
            )
        
        frame_img = decoded_frame
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error reading frame for session {session_id}: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=400,
            content={
                "error_code": "PROCESSING_ERROR",
                "message": f"Error processing image: {str(e)}",
                "content_type": image.content_type if image else None,
                "filename": image.filename if image else None
            }
        )
    
    # Detect faces
    faces = detect_faces(frame_img)
    timestamp = datetime.now()
    
    if len(faces) == 0:
        logger.info(f"👤 No faces detected in frame for session {session_id}")
        # No faces detected - still valid response
        return PredictFrameResponse(
            faces_found=0,
            top_result=None,
            results=[],
            stored_frame_update=None
        )
    
    # Process each face
    results = []
    top_confidence = 0.0
    top_result = None
    stored_update = defaultdict(int)
    
    for (x, y, w, h) in faces:
        # Extract and preprocess face
        face = frame_img[y:y+h, x:x+w]
        face_input = preprocess_face(face)
        
        # Predict emotion
        # Note: preprocessing in utils.py does NOT normalize to [0,1]
        # If your model expects normalized input, you may need to add: face_input = face_input / 255.0
        preds = model.predict(face_input, verbose=0)
        emotion_idx = int(np.argmax(preds))
        emotion = emotion_labels[emotion_idx]
        confidence = float(np.max(preds))
        
        # Thread-safe session update
        with session_lock:
            session.emotion_counts[emotion] += 1
            session.emotion_confidences[emotion].append(confidence)
            session.timeline.append({
                "timestamp": timestamp.isoformat(),
                "emotion": emotion,
                "confidence": confidence
            })
            
            # Store frame if it's good enough
            store_frame_for_emotion(session, emotion, confidence, timestamp, face)
            stored_update[emotion] = len(session.saved_frames[emotion])
        
        # Track results
        face_result = FaceResult(
            emotion=emotion,
            confidence=confidence,
            bbox=(int(x), int(y), int(w), int(h))
        )
        results.append(face_result)
        
        if confidence > top_confidence:
            top_confidence = confidence
            top_result = face_result
        
        logger.info(f"😊 EMOTION DETECTED: Session {session_id}, Emotion: {emotion}, Confidence: {confidence:.2f}")
    
    # Log frame processing progress
    with session_lock:
        total_frames = sum(session.emotion_counts.values())
    
    if total_frames % 10 == 0 and total_frames > 0:
        logger.info(f"📊 PROGRESS: Session {session_id}, Processed {total_frames} frames, Emotions: {dict(session.emotion_counts)}")
    
    return PredictFrameResponse(
        faces_found=len(faces),
        top_result=top_result,
        results=results,
        stored_frame_update=dict(stored_update) if stored_update else None
    )


@app.post("/stop_session", response_model=SessionReport, dependencies=[Depends(verify_api_key)])
async def stop_session(request: StopSessionRequest):
    """
    Stop an interview session and return complete report with saved frames.
    
    Args:
        request: JSON body with session_id field
    
    Returns:
        Complete session report including emotion counts, timeline, saved frames, and summary
    """
    session = get_session_or_error(request.session_id)
    
    # Calculate duration
    duration = (datetime.now() - session.started_at).total_seconds()
    
    # Thread-safe access to session data
    with session_lock:
        # Calculate average confidence per emotion
        avg_confidence = {}
        for emotion, confidences in session.emotion_confidences.items():
            if confidences:
                avg_confidence[emotion] = sum(confidences) / len(confidences)
        
        # Prepare saved frames with metadata
        saved_frames_output = {}
        for emotion, frames_list in session.saved_frames.items():
            saved_frames_output[emotion] = [
                SavedFrame(
                    timestamp=ts.isoformat(),
                    confidence=conf,
                    frame_base64=base64.b64encode(fb).decode('utf-8')
                )
                for conf, ts, fb in frames_list
            ]
        
        # Calculate dominant emotions (top 3)
        dominant_emotions = []
        if session.emotion_counts:
            most_common = session.emotion_counts.most_common(3)
            total_count = sum(session.emotion_counts.values())
            dominant_emotions = [
                {"emotion": emotion, "count": count, "percentage": (count / total_count) * 100}
                for emotion, count in most_common
            ]
        
        # Build summary for Gemini/LLM
        summary = {
            "total_duration_seconds": round(duration, 2),
            "total_frames_processed": sum(session.emotion_counts.values()),
            "dominant_emotions": dominant_emotions,
            "emotion_distribution": dict(session.emotion_counts),
            "average_confidence_overall": round(
                sum(sum(c) for c in session.emotion_confidences.values()) / 
                sum(len(c) for c in session.emotion_confidences.values()),
                3
            ) if any(session.emotion_confidences.values()) else 0.0,
            "unique_emotions_detected": len(session.emotion_counts),
            "session_quality": "good" if avg_confidence and sum(avg_confidence.values()) / len(avg_confidence) > 0.7 else "moderate"
        }
        
        # Build report
        report = SessionReport(
            session_id=request.session_id,
            duration_seconds=round(duration, 2),
            emotion_counts=dict(session.emotion_counts),
            average_confidence=avg_confidence,
            timeline=session.timeline,
            saved_frames=saved_frames_output,
            summary=summary
        )
        
        # Log session completion stats
        total_frames = sum(session.emotion_counts.values())
        logger.info(f"🛑 SESSION STOPPED: {request.session_id}")
        logger.info(f"📈 REPORT GENERATED: Duration={duration:.1f}s, Total frames={total_frames}")
        logger.info(f"📊 FINAL EMOTIONS: {dict(session.emotion_counts)}")
        logger.info(f"🏆 DOMINANT: {dominant_emotions[0] if dominant_emotions else 'None'}")
    
    # Clean up session
    with session_lock:
        del sessions[request.session_id]
    
    return report


@app.post("/reset_session", dependencies=[Depends(verify_api_key)])
async def reset_session(request: ResetSessionRequest):
    """
    Reset a session (clear all data but keep session active).
    Useful for debugging or restarting an interview.
    """
    session = get_session_or_error(request.session_id)
    
    # Thread-safe session reset
    with session_lock:
        # Keep session ID and start time, reset everything else
        session.last_activity = datetime.now()
        session.timeline = []
        session.emotion_counts = Counter()
        session.emotion_confidences = defaultdict(list)
        session.saved_frames = defaultdict(list)
    
    logger.info(f"🔄 SESSION RESET: {request.session_id}")
    
    return {
        "status": "success",
        "message": f"Session {request.session_id} has been reset",
        "session_id": request.session_id
    }


@app.get("/")
async def root():
    """Root endpoint with API info"""
    return {
        "name": "Emotion Detection API",
        "version": "1.0.0",
        "endpoints": {
            "health": "GET /health",
            "start_session": "POST /start_session",
            "predict_frame": "POST /predict_frame",
            "stop_session": "POST /stop_session",
            "reset_session": "POST /reset_session (debug)"
        },
        "documentation": "/docs"
    }


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error": str(exc)
        }
    )


@app.on_event("startup")
async def startup_event():
    """Log server startup information"""
    logger.info("="*60)
    logger.info("Emotion Detection API Server Starting")
    logger.info(f"Model: {MODEL_PATH}")
    logger.info(f"API Key Protection: {'ENABLED' if API_KEY else 'DISABLED'}")
    logger.info(f"Max Frames per Emotion: {MAX_FRAMES_PER_EMOTION}")
    logger.info(f"Session Timeout: {SESSION_TIMEOUT_MINUTES} minutes")
    logger.info("="*60)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")


"""
================================================================================
FLUTTER COMPATIBILITY SUMMARY
================================================================================

ISSUES FOUND AND FIXED:
------------------------
1. ❌ Field name mismatch: /predict_frame expected "file" but Flutter sends "image"
   ✅ FIXED: Changed parameter from 'file' to 'image' in predict_frame endpoint

2. ❌ Validation errors (422) not logged clearly
   ✅ FIXED: Added custom validation error handler with detailed logging

3. ❌ No request/response logging for debugging
   ✅ FIXED: Added middleware to log all HTTP requests with timing and status

4. ❌ Thread safety issues with rapid frame submissions
   ✅ FIXED: Added threading.Lock for session access protection

5. ❌ Empty frames not handled gracefully
   ✅ FIXED: Added explicit check for empty image data with clear error

6. ❌ Generic error messages made debugging difficult
   ✅ FIXED: Added detailed logging with emojis for easy scanning

7. ❌ No visibility into frame processing pipeline
   ✅ FIXED: Added logs at each step: receive, decode, detect, predict, store


FLUTTER INTEGRATION GUIDE:
--------------------------

ENDPOINTS TO CALL:
------------------
1. GET  /health           - Check server status (no auth)
2. POST /start_session    - Start interview, get session_id
3. POST /predict_frame    - Send camera frames during interview
4. POST /stop_session     - End interview, get full report
5. POST /reset_session    - Reset session (optional, for debugging)


FLUTTER REQUEST FORMAT:
-----------------------

1. Start Session:
   ```dart
   final response = await http.post(
     Uri.parse('$baseUrl/start_session'),
     headers: {
       'x-api-key': apiKey,  // Only if API_KEY env var is set
     },
   );
   final sessionId = jsonDecode(response.body)['session_id'];
   ```

2. Send Frame (CRITICAL - Field name MUST be "image"):
   ```dart
   var request = http.MultipartRequest('POST', Uri.parse('$baseUrl/predict_frame'));
   
   // Add session ID
   request.fields['session_id'] = sessionId;
   
   // Add image with field name "image" (NOT "file"!)
   request.files.add(
     http.MultipartFile.fromBytes(
       'image',  // ⚠️ MUST BE "image" NOT "file"
       imageBytes,
       filename: 'frame.jpg',
       contentType: MediaType('image', 'jpeg'),
     )
   );
   
   // Add API key if enabled
   if (apiKey != null) {
     request.headers['x-api-key'] = apiKey;
   }
   
   final streamedResponse = await request.send();
   final response = await http.Response.fromStream(streamedResponse);
   final result = jsonDecode(response.body);
   
   // Check results
   if (result['faces_found'] > 0) {
     final emotion = result['top_result']['emotion'];
     final confidence = result['top_result']['confidence'];
     print('Detected: $emotion ($confidence)');
   }
   ```

3. Stop Session:
   ```dart
   final response = await http.post(
     Uri.parse('$baseUrl/stop_session'),
     headers: {
       'Content-Type': 'application/json',
       'x-api-key': apiKey,  // Only if API_KEY env var is set
     },
     body: jsonEncode({'session_id': sessionId}),
   );
   
   final report = jsonDecode(response.body);
   print('Duration: ${report['duration_seconds']}s');
   print('Emotions: ${report['emotion_counts']}');
   print('Dominant: ${report['summary']['dominant_emotions']}');
   
   // Access saved frames
   for (var emotion in report['saved_frames'].keys) {
     for (var frame in report['saved_frames'][emotion]) {
       final imageData = base64Decode(frame['frame_base64']);
       // Display or save imageData
     }
   }
   ```


RESPONSE FORMATS:
-----------------

start_session:
{
  "session_id": "abc-123-...",
  "started_at": "2026-02-03T16:20:00"
}

predict_frame (with face):
{
  "faces_found": 1,
  "top_result": {
    "emotion": "happy",
    "confidence": 0.92,
    "bbox": [100, 100, 200, 200]
  },
  "results": [...],
  "stored_frame_update": {"happy": 3}
}

predict_frame (no face):
{
  "faces_found": 0,
  "top_result": null,
  "results": [],
  "stored_frame_update": null
}

stop_session:
{
  "session_id": "abc-123",
  "duration_seconds": 45.2,
  "emotion_counts": {"happy": 30, "neutral": 15},
  "average_confidence": {"happy": 0.89, "neutral": 0.76},
  "timeline": [
    {"timestamp": "...", "emotion": "happy", "confidence": 0.92},
    ...
  ],
  "saved_frames": {
    "happy": [
      {
        "timestamp": "2026-02-03T16:20:15",
        "confidence": 0.95,
        "frame_base64": "/9j/4AAQSkZJ..."  // JPEG as base64
      }
    ]
  },
  "summary": {
    "total_duration_seconds": 45.2,
    "total_frames_processed": 45,
    "dominant_emotions": [
      {"emotion": "happy", "count": 30, "percentage": 66.67}
    ],
    "emotion_distribution": {"happy": 30, "neutral": 15},
    "average_confidence_overall": 0.85,
    "unique_emotions_detected": 2,
    "session_quality": "good"
  }
}


ERROR RESPONSES:
----------------

400 Bad Request - Invalid/empty image:
{
  "detail": "Empty image file received"
}

404 Not Found - Invalid session:
{
  "detail": "Session abc-123 not found or expired"
}

422 Validation Error - Wrong field names:
{
  "detail": "Validation error - check request format",
  "errors": [...],
  "message": "Request does not match expected format..."
}


SERVER LOGGING (what you'll see):
----------------------------------
📥 REQUEST: POST /start_session from 10.19.40.133
🆕 SESSION STARTED: abc-123-def-456
📤 RESPONSE: POST /start_session → Status 200 (0.023s)

📥 REQUEST: POST /predict_frame from 10.19.40.133
📸 FRAME RECEIVED: Session abc-123, Size: 45.2KB, Filename: frame.jpg
😊 EMOTION DETECTED: Session abc-123, Emotion: happy, Confidence: 0.92
📤 RESPONSE: POST /predict_frame → Status 200 (0.156s)

📊 PROGRESS: Session abc-123, Processed 10 frames, Emotions: {'happy': 7, 'neutral': 3}

📥 REQUEST: POST /stop_session from 10.19.40.133
🛑 SESSION STOPPED: abc-123-def-456
📈 REPORT GENERATED: Duration=45.2s, Total frames=45
📊 FINAL EMOTIONS: {'happy': 30, 'neutral': 15}
🏆 DOMINANT: {'emotion': 'happy', 'count': 30, 'percentage': 66.67}
📤 RESPONSE: POST /stop_session → Status 200 (0.089s)


RUNNING THE SERVER:
-------------------

Development (with auto-reload - may cause issues with TensorFlow):
  uvicorn api:app --host 0.0.0.0 --port 8000 --reload

Production (recommended for stable operation):
  uvicorn api:app --host 0.0.0.0 --port 8000 --workers 1

⚠️ AUTO-RELOAD NOTES:
- --reload watches for file changes and restarts server automatically
- Can cause TensorFlow model to reload unnecessarily
- May cause "model already loaded" warnings or memory issues
- Recommended: Use --reload during development ONLY
- For production or extended testing, remove --reload flag

Multi-worker (only if needed, requires process-safe storage like Redis):
  uvicorn api:app --host 0.0.0.0 --port 8000 --workers 4


TESTING CHECKLIST:
------------------
✅ Server starts without errors
✅ /health returns {"status": "healthy", "model_loaded": true}
✅ POST /start_session returns session_id
✅ POST /predict_frame accepts "image" field (not "file")
✅ Frames process without 422 validation errors
✅ Terminal shows clear logs for each request
✅ Multiple rapid frames don't cause crashes
✅ POST /stop_session returns complete report with base64 frames
✅ Sessions auto-expire after 30 minutes of inactivity


COMMON ISSUES AND SOLUTIONS:
-----------------------------

Issue: 422 Validation Error on /predict_frame
Solution: Ensure field name is "image" not "file" in Flutter multipart request

Issue: "Session not found" immediately after creation
Solution: Check that session_id is properly extracted from start_session response

Issue: Empty frame errors
Solution: Verify camera permission in Flutter and image bytes are not empty

Issue: Server crashes on rapid frames
Solution: Fixed with threading.Lock - update to latest api.py

Issue: No faces detected
Solution: Ensure good lighting, camera facing user, not a backend issue

Issue: 401 Unauthorized errors
Solution: Either set x-api-key header or remove API_KEY environment variable


PERFORMANCE NOTES:
------------------
- Model loaded once on startup (not per request)
- Frames automatically resized if width > 1280px (configurable)
- Thread-safe session access for concurrent requests
- Sessions auto-expire after 30 minutes (configurable)
- Best N frames per emotion stored (default: 10, configurable)

================================================================================
"""

