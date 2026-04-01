# Full Project Documentation

## 1) Project Purpose

This repository contains two related backend systems:

1. Emotion Detection API (root project)
- Runs a local TensorFlow model to detect facial emotions from uploaded camera frames.
- Designed for interview-session tracking (start session, process frames, stop session, generate report).
- Exposes REST endpoints through FastAPI.

2. Gemini AI API (gemini-api subproject)
- Wraps Google Gemini capabilities (text generation, summarization, JSON extraction, emotion-report analysis).
- Includes production-style middleware: request ID, rate limiting, structured logging, retry with backoff, and model fallback.

Together, the intended workflow is:
- Flutter app streams interview frames to Emotion Detection API.
- Emotion API builds a session report with emotion distribution and confidence.
- Report can be sent to Gemini API for natural-language analysis and recommendations.

---

## 2) Repository Structure and Responsibilities

### Root-level (Emotion Detection API)

- api.py
  Main FastAPI server for emotion detection and session management.

- src/face_detector.py
  Face detection using OpenCV Haar cascade.

- src/utils.py
  Face preprocessing and emotion label mapping.

- src/webcam_app.py
  Standalone desktop webcam emotion detection demo (non-API mode).

- src/image_test.py
  Standalone single-image test script (non-API mode).

- model/emotion_efficientnet.keras
  Trained TensorFlow/Keras model used for inference.

- run_api.ps1
  Convenience script to activate venv, install dependencies, print network URL, and run Uvicorn.

- debug_upload_file.py
  CLI tool that uploads a local image to /predict_frame for debugging payload issues.

- debug_webcam_upload.py
  CLI tool that captures one webcam frame and uploads it to /predict_frame.

- tests/test_image_decode.py
  Unit tests for image format detection and decoding behavior.

- requirements.txt
  Dependencies for the root Emotion Detection API.

- README.txt, DEBUGGING_GUIDE.md, MOBILE_TESTING_GUIDE.md, IMPLEMENTATION_SUMMARY.md
  Existing operational docs and debugging notes.

### Subproject (Gemini API)

- gemini-api/app/main.py
  FastAPI app bootstrap: middleware, routers, exception handlers, startup/shutdown logging.

- gemini-api/app/config.py
  Environment-based configuration using Pydantic Settings.

- gemini-api/app/api/routes/health.py
  Health and root information endpoints.

- gemini-api/app/api/routes/gemini.py
  AI endpoints for generate, summarize, extract, and analyze emotions.

- gemini-api/app/services/gemini_service.py
  Core Gemini integration with primary/fallback model logic and retry support.

- gemini-api/app/models/requests.py
  Pydantic request schemas and constraints.

- gemini-api/app/models/responses.py
  Pydantic response schemas.

- gemini-api/app/middleware/request_id.py
  Injects request_id into request state and response headers.

- gemini-api/app/middleware/rate_limiter.py
  SlowAPI limiter initialization and default policy.

- gemini-api/app/utils/logger.py
  Structured logging setup (JSON or console).

- gemini-api/app/utils/retry.py
  Async retry decorator with exponential backoff.

- gemini-api/tests/test_endpoints.py
  Integration-style endpoint tests (contains drift; see Known Issues).

- gemini-api/tests/test_gemini_service.py
  Unit tests for service behavior and fallback logic.

- gemini-api/.env.example
  Environment variable template.

- gemini-api/requirements.txt
  Dependencies for Gemini API.

---

## 3) High-Level Architecture

### Emotion Detection API runtime flow

1. Server startup
- Reads env config (API_KEY, frame limits, timeout, max width).
- Loads TensorFlow model from model/emotion_efficientnet.keras once.
- Registers middleware, exception handlers, and endpoints.

2. Session lifecycle
- Client calls POST /start_session and receives session_id.
- Client repeatedly calls POST /predict_frame with session_id + image file.
- Server decodes image, detects faces, predicts emotion for each face, updates in-memory session stats.
- Client calls POST /stop_session to obtain final report; session is deleted.

3. Report output
- Returns counts, average confidence by emotion, event timeline, selected best frames (base64), and summary metrics.

### Gemini API runtime flow

1. Server startup
- Loads settings from .env.
- Configures structured logging.
- Configures CORS, rate limiter, request ID middleware.

2. Request processing
- Each request receives request_id.
- Optional API key verification on Gemini endpoints.
- Rate limit enforced by SlowAPI.
- Service methods call Gemini model with fallback and retry behavior.

3. Response and observability
- Response includes request_id and modeled payload.
- Structured logs capture request lifecycle and model path used.

---

## 4) Emotion Detection API: Detailed Functional Behavior

## 4.1 Core data models in api.py

- StartSessionResponse
  session_id and started_at.

- StopSessionRequest
  JSON input with session_id.

- ResetSessionRequest
  JSON input with session_id.

- FaceResult
  emotion, confidence, bbox tuple (x, y, w, h).

- PredictFrameResponse
  faces_found, top_result, all results, and stored_frame_update.

- SavedFrame
  timestamp, confidence, frame_base64.

- SessionReport
  Full session analytics output.

- ImageDecodeError
  Structured decode failure details.

## 4.2 Session state model

SessionData stores in-memory:
- session_id
- started_at, last_activity
- timeline (emotion events with timestamps)
- emotion_counts (Counter)
- emotion_confidences (list per emotion)
- saved_frames (top frames per emotion)

Notes:
- Session expiration uses SESSION_TIMEOUT_MINUTES.
- Global sessions dictionary is protected by a threading lock for writes/updates.
- This design is single-process memory. No persistence or cross-process sharing.

## 4.3 Security model

- Optional API key via x-api-key header.
- If environment variable API_KEY is set, all protected endpoints require exact match.
- Health endpoint is intentionally open for monitoring.

## 4.4 Image decode pipeline

decode_image_from_upload:
- Validates non-empty file.
- Detects image format by magic bytes (JPEG, PNG, WEBP).
- Logs first 32 bytes hex for diagnostics.
- Attempts OpenCV decode first.
- Falls back to PIL decode if OpenCV fails.
- Resizes image if width exceeds INPUT_FRAME_MAX_WIDTH.
- Returns structured error object on failure.

## 4.5 Face and emotion inference pipeline

For each detected face:
- Crop from frame using bbox.
- preprocess_face from src/utils.py:
  - Resize to 224x224
  - Convert BGR to RGB
  - Cast float32
  - Expand batch dimension
- model.predict
- Argmax maps to emotion_labels:
  angry, disgust, fear, happy, neutral, sad, surprise
- Confidence = max probability.

Important detail:
- Preprocessing currently does not normalize pixel values to [0,1].
- A code comment in api.py warns this may need adjustment depending on training pipeline.

## 4.6 Frame retention strategy

store_frame_for_emotion:
- Keeps top confidence frames per emotion.
- Applies temporal diversity target (about 2 seconds gap) before fallback to pure top-N.
- N is controlled by MAX_FRAMES_PER_EMOTION.

## 4.7 Session summary logic on stop

When POST /stop_session is called:
- Computes duration.
- Computes average confidence per emotion.
- Builds saved_frames output with base64 encoded JPEG bytes.
- Computes dominant emotions (top 3 with percentages).
- Computes summary fields:
  - total_duration_seconds
  - total_frames_processed
  - dominant_emotions
  - emotion_distribution
  - average_confidence_overall
  - unique_emotions_detected
  - session_quality (good/moderate threshold logic)
- Deletes session from memory.

---

## 5) Emotion Detection API: Endpoint Reference

Base URL default: http://localhost:8000

## 5.1 GET /health
Purpose:
- Service health probe and activity count.

Auth:
- Not required.

Response includes:
- status
- model_loaded
- active_sessions
- timestamp

## 5.2 POST /start_session
Purpose:
- Create a new interview session.

Auth:
- Required only if API_KEY configured.

Response:
- session_id
- started_at

## 5.3 POST /predict_frame
Purpose:
- Process one uploaded image frame and detect emotions.

Request type:
- multipart/form-data

Form fields:
- session_id (required)
- frame (preferred) OR file (fallback), each as UploadFile

Behavior:
- Accepts either frame or file.
- Returns faces_found and per-face results.
- If no faces found, returns valid response with faces_found=0.
- On decode failures returns structured 400 payload.

Potential error payloads:
- MISSING_FILE
- EMPTY_FILE
- DECODE_FAILED
- PROCESSING_ERROR

## 5.4 POST /stop_session
Purpose:
- Close session and return comprehensive report.

Request body:
- JSON with session_id

Response:
- SessionReport object with analytics and saved frames.

## 5.5 POST /reset_session
Purpose:
- Clear accumulated session data while keeping session active.

Request body:
- JSON with session_id

Response:
- success status and message.

## 5.6 GET /
Purpose:
- API metadata and endpoint listing.

---

## 6) Gemini API: Detailed Functional Behavior

## 6.1 Configuration and environment

Configuration class in app/config.py loads:
- App metadata
- Server host/port/workers
- Gemini credentials and model IDs
- Rate limits
- Optional API key
- CORS origins
- Logging format/level

Required key variable:
- GEMINI_API_KEY

## 6.2 Middleware and handlers

From app/main.py:
- RequestIDMiddleware: adds UUID request_id to request.state and X-Request-ID response header.
- CORSMiddleware: origins from config.
- RateLimitExceeded handler: returns 429 JSON.
- Global exception handler: returns 500 JSON with request_id.
- HTTP logging middleware: logs request and completion status.

## 6.3 Gemini model fallback and retry

In gemini_service.py:
- Primary model from GEMINI_MODEL_ID.
- If model-not-found style error occurs, fallback to GEMINI_FALLBACK_MODEL_ID.
- generate_text method wrapped with async_retry decorator.
- Retry uses exponential backoff with configurable attempts.

## 6.4 Prompt-building and parsing strategies

generate_text:
- Builds combined prompt from optional system_prompt, optional context, and user message.

summarize:
- Supports style: concise, detailed, bullet-points.

extract_json:
- Injects schema and instructions.
- Attempts JSON extraction from model text including markdown-code-block cleanup.

analyze_emotion_report:
- Builds structured prompt from emotion metrics and context.
- Expects JSON response with analysis, insights, recommendations.
- Parses and returns structured components.

---

## 7) Gemini API: Endpoint Reference

Base URL default: http://localhost:8001
Router prefix: /api/v1

## 7.1 GET /health
Purpose:
- Service health and metadata.

## 7.2 GET /
Purpose:
- Root metadata and endpoint listing.

## 7.3 POST /api/v1/generate
Purpose:
- Freeform text generation.

Body model:
- GenerateTextRequest
  - message (required)
  - system_prompt (optional)
  - context (optional)
  - temperature
  - max_tokens

Response model:
- GenerateTextResponse

## 7.4 POST /api/v1/summarize
Purpose:
- Summarize long text.

Body model:
- SummarizeRequest

Response model:
- SummarizeResponse

## 7.5 POST /api/v1/extract
Purpose:
- Structured JSON extraction from text.

Body model:
- ExtractJSONRequest

Response model:
- ExtractJSONResponse

## 7.6 POST /api/v1/analyze-emotions
Purpose:
- Analyze emotion-session report into insights and recommendations.

Body model:
- AnalyzeEmotionReportRequest

Response model:
- AnalyzeEmotionReportResponse

Security:
- Optional x-api-key verification if API_KEY configured.
Rate limiting:
- Applied to all Gemini route handlers via limiter decorator.

---

## 8) Scripts and Operational Tooling

## 8.1 run_api.ps1

Purpose:
- Root API startup helper.

Steps:
1. Activate .venv if present.
2. pip install -r requirements.txt (quiet).
3. Discover likely LAN IPv4 address.
4. Print local/network URLs.
5. Launch uvicorn api:app --host 0.0.0.0 --port 8000 --reload.

## 8.2 debug_upload_file.py

Purpose:
- Validate server upload pipeline from local image.

What it verifies:
- Local file exists and bytes are readable.
- Displays first 32 bytes and guessed format.
- Sends multipart with frame field.
- Prints rich success/error details.

## 8.3 debug_webcam_upload.py

Purpose:
- Validate capture and upload pipeline end to end.

What it verifies:
- Camera opens and captures frame.
- JPEG encoding works.
- Magic bytes match expected JPEG signature.
- Upload response and face/emotion results.

## 8.4 src/webcam_app.py and src/image_test.py

Purpose:
- Non-API local scripts useful during model/manual debugging.

---

## 9) Testing Coverage and Status

## 9.1 Root project tests

tests/test_image_decode.py covers:
- Magic byte identification (JPEG/PNG).
- Valid JPEG/PNG decoding.
- PIL fallback path.
- Empty file handling.
- Invalid bytes handling.
- Truncated JPEG handling.

## 9.2 Gemini API tests

gemini-api/tests/test_gemini_service.py covers:
- Primary path success.
- Fallback model behavior.
- Summarize, extract, analyze methods.
- Failure behavior when both models fail.

gemini-api/tests/test_endpoints.py attempts endpoint integration tests but currently shows schema/path drift from implementation (see Known Issues).

---

## 10) Environment Variables

## 10.1 Root Emotion API variables

- API_KEY
  Enables API key protection when set.

- MAX_FRAMES_PER_EMOTION (default 10)
  Number of retained best frames per emotion.

- SESSION_TIMEOUT_MINUTES (default 30)
  Session expiration interval.

- INPUT_FRAME_MAX_WIDTH (default 1280)
  Max width before downscaling incoming images.

## 10.2 Gemini API variables (.env example)

- APP_NAME, APP_VERSION, ENVIRONMENT, DEBUG
- HOST, PORT, WORKERS
- GEMINI_API_KEY (required)
- GEMINI_MODEL_ID, GEMINI_FALLBACK_MODEL_ID
- GEMINI_TIMEOUT, GEMINI_MAX_RETRIES
- RATE_LIMIT_ENABLED, RATE_LIMIT_REQUESTS, RATE_LIMIT_PERIOD
- API_KEY (optional)
- CORS_ORIGINS
- LOG_LEVEL, LOG_FORMAT

---

## 11) Known Issues, Drift, and Technical Debt

These are important observations discovered from actual source files:

1. Duplicate startup handlers in root api.py
- There are two @app.on_event("startup") functions defined with same name startup_event.
- FastAPI may register both decorators at definition time, but this is confusing and error-prone.
- Recommendation: keep a single startup hook and merge responsibilities.

2. Stale comments about field name in root api.py and docs
- Top docstring says changed to image field.
- Current implementation accepts frame and file, not image.
- Some Flutter example comments still mention image as required.
- Recommendation: align all docs/examples to accepted field names or add image alias if desired.

3. Unused imports in root api.py
- asyncio, Field, ValidationError, and others appear unused.
- Recommendation: remove to keep code clean and reduce confusion.

4. Session cleanup not lock-protected consistently
- cleanup_expired_sessions manipulates global sessions without lock.
- Other sections use lock for mutation.
- Recommendation: standardize lock usage for all writes/deletes.

5. Root API in-memory state is not horizontally scalable
- Session data exists only in process memory.
- Multiple workers/processes will not share session state.
- Recommendation: migrate sessions to Redis or database for multi-instance deployment.

6. gemini-api endpoint tests mismatch current API contract
- Tests reference older paths or field names (for example /api/v1/gemini/generate, prompt, max_output_tokens).
- Current implementation uses /api/v1/generate with message/max_tokens models.
- Recommendation: update tests to current request/route schemas.

7. health/root response expectations mismatch in gemini tests
- Some tests expect fields not present in current route implementation.
- Recommendation: adjust tests or route payload schema to desired contract.

---

## 12) How Components Work Together in a Real Interview Flow

1. Mobile app checks Emotion API health.
2. App starts session via /start_session.
3. App captures frames every interval and sends to /predict_frame.
4. API accumulates emotion events and confidence values over time.
5. App stops session via /stop_session and receives detailed report.
6. Optional: App posts report-derived metrics to Gemini API /api/v1/analyze-emotions.
7. Gemini API returns human-readable interpretation and recommendations.

This produces both:
- Quantitative signal from model inference (counts/confidence/timeline).
- Qualitative narrative from LLM analysis.

---

## 13) Deployment and Runtime Notes

## 13.1 Local development

Emotion API:
- uvicorn api:app --host 0.0.0.0 --port 8000 --reload

Gemini API:
- cd gemini-api
- uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

## 13.2 Mobile testing

- Use LAN IP (not localhost) from phone.
- Keep laptop and phone on same Wi-Fi.
- Open firewall rule for chosen port.

## 13.3 Production considerations

- Do not run with reload in production.
- Use persistent session storage for Emotion API.
- Restrict CORS origins.
- Enforce API key or stronger auth.
- Add HTTPS termination and reverse proxy.
- Monitor inference latency and model memory usage.

---

## 14) Quick API Contract Summary

## Emotion API contract summary

- start_session
  Request: empty POST
  Response: session_id

- predict_frame
  Request: multipart/form-data with session_id + frame/file upload
  Response: per-face predictions + top result

- stop_session
  Request: JSON session_id
  Response: full session analytics report

## Gemini API contract summary

- generate
  Request: message + options
  Response: generated text + model used

- summarize
  Request: text + style/length
  Response: summary + compression metrics

- extract
  Request: text + schema + instructions
  Response: extracted JSON + raw model output

- analyze-emotions
  Request: emotion counts/distribution context
  Response: analysis + insights + recommendations

---

## 15) Suggested Next Improvements (Prioritized)

1. Remove route/docs drift and unify request-field naming policy.
2. Merge duplicate startup handlers and clean unused imports in root api.py.
3. Update gemini-api tests to current endpoints and schemas.
4. Add integration test for full Emotion API session lifecycle.
5. Add Redis-backed session store for production scaling.
6. Add model-input normalization toggle based on training pre-processing.

---

## 16) Documentation Source of Truth

This document was generated from direct source inspection of:
- root API code and scripts
- Gemini subproject code
- test files
- existing markdown/txt guides in repository

If code and documentation disagree, treat source code as final runtime truth and update docs accordingly.
