# 🔧 Debugging Guide for Emotion Detection API

## What Was Fixed

### 1. ✅ Route Registration & Logging
- Added startup event that logs all registered routes
- `/predict_frame` route is now verified at startup
- Easy to see if endpoint exists and what methods it accepts

### 2. ✅ Flexible Field Names
- Accepts **both** `frame` and `file` as field names
- Flutter can use either - no more 422 validation errors
- Fallback logic ensures compatibility

### 3. ✅ Detailed Debug Logging
- Logs content-type, filename, and size for every request
- Shows **first 32 bytes in hex** (same format as magic bytes)
- Detects JPEG/PNG/WEBP from magic bytes on server side
- Easy to compare what client sent vs what server received

### 4. ✅ Improved Image Decoding
- Tries OpenCV first (fast)
- Falls back to PIL if OpenCV fails
- Returns structured error with full debug info on failure
- No more generic "invalid format" errors

### 5. ✅ Structured Error Responses
When decode fails, returns JSON with:
- `error_code`: Machine-readable error type
- `message`: Human-readable description
- `content_type`: MIME type from request
- `filename`: Original filename
- `size_bytes`: File size
- `first_32_bytes_hex`: Hex dump of first 32 bytes
- `detected_format`: Format detected from magic bytes (JPEG/PNG/etc)

### 6. ✅ CORS Support
- Added CORS middleware for development
- Phone can now call API on local network
- No more CORS errors in Flutter

### 7. ✅ Unit Tests
- Tests for JPEG and PNG decoding
- Tests magic byte detection
- Tests error cases (empty, invalid, truncated)
- Verifies `first_32_bytes_hex` is included in errors

### 8. ✅ CLI Debug Tools
Two scripts to test independently from Flutter:
1. **debug_upload_file.py** - Upload local image file
2. **debug_webcam_upload.py** - Capture webcam and upload

---

## 📋 Testing Instructions

### Step 1: Run Unit Tests

Test the image decoding logic:

```bash
cd "C:\Users\aliah\OneDrive\Desktop\Models\Umar workplace\emotion_detection"
.\.venv\Scripts\python.exe tests\test_image_decode.py
```

**Expected Output:**
```
============================================================
🧪 Running Image Decode Tests
============================================================
✅ JPEG magic bytes detected correctly
✅ PNG magic bytes detected correctly
✅ Valid JPEG decoded successfully: shape=(10, 10, 3)
✅ Valid PNG decoded successfully: shape=(10, 10, 3)
✅ PIL PNG decoded successfully: shape=(10, 10, 3)
✅ Empty file error handled correctly
✅ Invalid data error handled correctly
✅ Truncated JPEG error handled correctly
============================================================
📊 Test Results: 8 passed, 0 failed
============================================================
```

### Step 2: Start the Backend

Start the emotion detection API:

```bash
cd "C:\Users\aliah\OneDrive\Desktop\Models\Umar workplace\emotion_detection"
.\.venv\Scripts\python.exe -m uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

**Check startup logs for route listing:**
```
============================================================
🚀 Emotion Detection API Starting Up
============================================================
📋 Registered Routes:
  GET      /health
  POST     /start_session
  POST     /predict_frame
  POST     /stop_session
  POST     /reset_session
============================================================
```

✅ Verify `/predict_frame` is listed!

### Step 3: Start a Session

Use curl or Python to start a session:

```bash
curl -X POST http://localhost:8000/start_session
```

**Copy the `session_id` from response** (you'll need it for next steps)

Example response:
```json
{
  "session_id": "abc-123-def-456",
  "started_at": "2026-02-03T19:00:00"
}
```

### Step 4: Test with Local Image File

Use the debug tool to upload a local image:

```bash
# Upload a test image (create one or use any JPEG/PNG)
.\.venv\Scripts\python.exe debug_upload_file.py test.jpg abc-123-def-456
```

**With your laptop IP for phone testing:**
```bash
.\.venv\Scripts\python.exe debug_upload_file.py test.jpg abc-123-def-456 --base-url http://10.19.40.133:8000
```

**Expected Output:**
```
============================================================
📤 Uploading to Emotion Detection API
============================================================
   File: test.jpg
   Size: 15234 bytes (14.9 KB)
   Session ID: abc-123-def-456
   Base URL: http://localhost:8000

🔍 First 32 bytes (hex): ffd8ffe000104a46494600010101006000600000...
🔍 Detected format: JPEG

📡 Sending POST request to: http://localhost:8000/predict_frame

📥 Response Status: 200

✅ SUCCESS!

   Faces Found: 1
   Top Emotion: happy
   Confidence: 87.45%
   Bounding Box: (100, 120, 150, 180)
```

### Step 5: Test with Webcam Capture

Capture a frame from your webcam and upload:

```bash
.\.venv\Scripts\python.exe debug_webcam_upload.py abc-123-def-456
```

**With your laptop IP:**
```bash
.\.venv\Scripts\python.exe debug_webcam_upload.py abc-123-def-456 --base-url http://10.19.40.133:8000
```

**Expected Output:**
```
============================================================
📷 Capturing from webcam and uploading
============================================================
   Camera Index: 0
   Session ID: abc-123-def-456
   Base URL: http://localhost:8000

📸 Opening camera...
✅ Camera opened successfully
📸 Capturing frame...
✅ Frame captured: 640x480 pixels

🔄 Encoding to JPEG...
✅ Encoded successfully: 45.2 KB (46234 bytes)
🔍 First 32 bytes (hex): ffd8ffe000104a46494600010101006000600000...
🔍 JPEG magic bytes verified: FF D8 FF

📡 Sending POST request to: http://localhost:8000/predict_frame

📥 Response Status: 200

✅ SUCCESS!

   Faces Found: 1
   Top Emotion: neutral
   Confidence: 82.31%
```

### Step 6: Test from Flutter App

Now test from your phone:

1. **Set the base URL in Flutter** to your laptop IP:
   ```dart
   final baseUrl = "http://10.19.40.133:8000";
   ```

2. **Start interview** and watch the server logs

3. **Look for these log entries:**
   ```
   📥 REQUEST: POST /predict_frame from 10.19.40.133
   📸 FRAME RECEIVED: Session abc-123-def-456
      Content-Type: image/jpeg
      Filename: frame.jpg
      Size: 45.2KB (46234 bytes)
   🔍 Image analysis: size=46234 bytes, content_type=image/jpeg, filename=frame.jpg, detected_format=JPEG
   🔍 First 32 bytes (hex): ffd8ffe000104a46494600010101006000600000...
   ✅ OpenCV decode successful: shape=(480, 640, 3)
   😊 EMOTION DETECTED: Session abc-123-def-456, Emotion: happy, Confidence: 0.87
   ```

---

## 🐛 Debugging Failures

### If you see "404 Not Found"

**Check:**
1. Is `/predict_frame` listed in startup logs?
2. Are you POSTing to the correct URL?
3. Is the server running?

**Fix:**
- Restart server and check startup logs
- Verify URL: `http://<IP>:8000/predict_frame`

### If you see "Invalid image format"

**Server logs will show:**
```
❌ Image decode failed for session abc-123
```

**And return:**
```json
{
  "error_code": "DECODE_FAILED",
  "message": "Failed to decode image with both OpenCV and PIL",
  "content_type": "image/jpeg",
  "filename": "frame.jpg",
  "size_bytes": 46234,
  "first_32_bytes_hex": "ffd8ffe000104a46494600010101006000600000...",
  "detected_format": "JPEG"
}
```

**Debug steps:**
1. **Check magic bytes** - Does `first_32_bytes_hex` start with:
   - JPEG: `ffd8ff...`
   - PNG: `89504e47...`

2. **Compare client vs server hex** - Use debug tools to see what client sent vs what server received

3. **Test with debug tools** - If debug tools work but Flutter fails, issue is in Flutter image encoding

### If debug tools work but Flutter fails

**Common causes:**
1. **Wrong field name** - Server accepts `frame` or `file`, check Flutter code
2. **Wrong content-type** - Should be `image/jpeg` or `image/png`
3. **Corrupted during transfer** - Compare hex bytes from client vs server logs
4. **Not actually image data** - Flutter might be sending base64 or wrong bytes

**Flutter checklist:**
```dart
// ✅ Correct way
final request = http.MultipartRequest('POST', uri);
request.fields['session_id'] = sessionId;
request.files.add(await http.MultipartFile.fromPath(
  'frame',  // or 'file'
  imagePath,
  contentType: MediaType('image', 'jpeg'),
));
```

---

## 📊 Understanding the Logs

### Successful Request
```
📥 REQUEST: POST /predict_frame from 10.19.40.133
📸 FRAME RECEIVED: Session abc-123
   Content-Type: image/jpeg
   Filename: frame.jpg
   Size: 45.2KB (46234 bytes)
🔍 Image analysis: detected_format=JPEG
🔍 First 32 bytes (hex): ffd8ffe000104a464946...
✅ OpenCV decode successful: shape=(480, 640, 3)
😊 EMOTION DETECTED: happy (87.45%)
📤 RESPONSE: POST /predict_frame → Status 200 (0.234s)
```

### Failed Request (decode error)
```
📥 REQUEST: POST /predict_frame from 10.19.40.133
📸 FRAME RECEIVED: Session abc-123
   Content-Type: application/octet-stream
   Filename: frame.dat
   Size: 1.2KB (1234 bytes)
🔍 Image analysis: detected_format=None
🔍 First 32 bytes (hex): 54686973206973206e6f742061...
⚠️ OpenCV decode failed, trying PIL fallback
❌ Both OpenCV and PIL decode failed
❌ Image decode failed for session abc-123
📤 RESPONSE: POST /predict_frame → Status 400 (0.156s)
```

---

## 🎯 Quick Reference

### Magic Bytes Cheat Sheet
- **JPEG**: `FF D8 FF` (hex: `ffd8ff`)
- **PNG**: `89 50 4E 47 0D 0A 1A 0A` (hex: `89504e470d0a1a0a`)
- **WebP**: `RIFF ???? WEBP`

### Accepted Field Names
- `frame` (preferred)
- `file` (fallback)

### Common Status Codes
- `200` - Success
- `400` - Bad request (invalid image, missing file, etc)
- `404` - Session not found or endpoint doesn't exist
- `422` - Validation error (wrong field names/types)

### Debug Tool Commands
```bash
# Start session
curl -X POST http://localhost:8000/start_session

# Upload file
.\.venv\Scripts\python.exe debug_upload_file.py image.jpg SESSION_ID

# Capture webcam
.\.venv\Scripts\python.exe debug_webcam_upload.py SESSION_ID

# With custom URL
.\.venv\Scripts\python.exe debug_upload_file.py image.jpg SESSION_ID --base-url http://10.19.40.133:8000
```

---

## 📝 Files Modified/Created

### Modified:
- `api.py` - Added all the improvements above

### Created:
- `tests/test_image_decode.py` - Unit tests for image decoding
- `debug_upload_file.py` - CLI tool to upload local images
- `debug_webcam_upload.py` - CLI tool to capture and upload webcam
- `DEBUGGING_GUIDE.md` - This file

---

## 🚀 Next Steps

1. ✅ Run unit tests - verify decoding works
2. ✅ Start backend - check `/predict_frame` is listed
3. ✅ Test with debug tools - verify server accepts images
4. ✅ Test from Flutter - compare logs
5. ✅ Fix Flutter if needed - check field names and encoding

**Good luck! 🎉**

