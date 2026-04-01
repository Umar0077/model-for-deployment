# Mobile Testing Quick Reference
# Emotion Detection API - FastAPI Backend

## ✅ Verification Checklist

### 1. Installation Check
```powershell
# Activate virtual environment
.venv\Scripts\Activate.ps1

# Install/update all requirements
pip install -r requirements.txt

# Verify key packages
pip list | Select-String "fastapi|uvicorn|tensorflow|opencv"
```

Expected output:
- fastapi (latest)
- uvicorn (latest)  
- opencv-python 4.x
- tensorflow 2.x

### 2. Project Structure Verification
```
emotion_detection/
├── api.py                          ✓ FastAPI backend (repo root)
├── run_api.ps1                     ✓ One-command run script
├── requirements.txt                ✓ All dependencies
├── model/
│   └── emotion_efficientnet.keras  ✓ Trained model
└── src/
    ├── face_detector.py            ✓ Face detection
    ├── utils.py                    ✓ Preprocessing & labels
    └── ...
```

### 3. Network Setup for Mobile

**Find Your IP Address:**
```powershell
ipconfig | Select-String "IPv4"
```
Look for: `192.168.x.x` (your laptop's local IP)

**Add Windows Firewall Rule:**
```powershell
# Run as Administrator
New-NetFirewallRule -DisplayName "Emotion API Port 8000" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow -Profile Private
```

### 4. Start Server

**Option A - Use run script (Recommended):**
```powershell
.\run_api.ps1
```

**Option B - Manual start:**
```powershell
.venv\Scripts\Activate.ps1
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

**Expected console output:**
```
============================================================
Emotion Detection API Server Starting
Model: C:\...\model\emotion_efficientnet.keras
API Key Protection: DISABLED
Max Frames per Emotion: 10
Session Timeout: 30 minutes
============================================================
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

### 5. Test from Laptop Browser

```
http://localhost:8000/health
http://localhost:8000/docs
http://localhost:8000
```

### 6. Test from Phone

**Requirements:**
- Phone on SAME WiFi as laptop
- Use laptop's IP address (not localhost!)

**Phone browser test:**
```
http://192.168.x.x:8000/health
```

Expected JSON:
```json
{
  "status": "healthy",
  "model_loaded": true,
  "active_sessions": 0,
  "timestamp": "2026-02-03T..."
}
```

### 7. Flutter App Configuration

```dart
// In your Flutter app
final String baseUrl = "http://192.168.x.x:8000";  // Use YOUR laptop IP!

// Headers (if API key is enabled)
final headers = {
  'x-api-key': 'your-secret-key',  // Only if $env:API_KEY is set
};
```

## 📝 API Endpoints Summary

| Endpoint | Method | Purpose | Auth Required |
|----------|--------|---------|---------------|
| `/health` | GET | Health check | No |
| `/` | GET | API info | No |
| `/start_session` | POST | Start interview | Yes* |
| `/predict_frame` | POST | Send frame | Yes* |
| `/stop_session` | POST | Get report | Yes* |
| `/reset_session` | POST | Reset (debug) | Yes* |

*Only if API_KEY environment variable is set

## 🔧 Quick Test Commands

### Test Complete Flow (PowerShell)
```powershell
# 1. Start session
$response = Invoke-RestMethod -Method POST -Uri "http://localhost:8000/start_session"
$sessionId = $response.session_id
Write-Host "Session ID: $sessionId"

# 2. Send test frame (replace with actual image)
$form = @{
    session_id = $sessionId
    file = Get-Item "test_image.jpg"
}
$result = Invoke-WebRequest -Method POST -Uri "http://localhost:8000/predict_frame" -Form $form
$result.Content | ConvertFrom-Json

# 3. Stop session
$report = Invoke-RestMethod -Method POST -Uri "http://localhost:8000/stop_session" -ContentType "application/json" -Body (@{session_id=$sessionId} | ConvertTo-Json)
Write-Host "Emotion counts:" $report.emotion_counts
```

## 🐛 Common Issues & Solutions

### Issue: "Connection refused" from phone
**Solution:**
1. Verify firewall rule: `Get-NetFirewallRule -DisplayName "*Emotion*"`
2. Check server is on 0.0.0.0: Look for "http://0.0.0.0:8000" in logs
3. Verify same WiFi network on both devices
4. Try temporarily disabling firewall to test

### Issue: "Module not found" errors
**Solution:**
```powershell
pip install -r requirements.txt
# Verify api.py is in repo root (same level as src/ folder)
```

### Issue: Port 8000 already in use
**Solution:**
```powershell
# Find process using port
Get-NetTCPConnection -LocalPort 8000 -State Listen
# Kill process or use different port
uvicorn api:app --host 0.0.0.0 --port 8001 --reload
```

### Issue: Model not found
**Solution:**
```powershell
# Verify model file exists
Test-Path "model\emotion_efficientnet.keras"
# Should return: True
```

### Issue: "No face detected" in all frames
**Solution:**
- Ensure adequate lighting
- Camera facing user directly
- Image quality is good (not too blurry)
- Check that face detection cascade loads properly

## 🔒 Optional: Enable API Key Protection

```powershell
# Set API key before starting server
$env:API_KEY = "my-secure-key-123"

# Start server
uvicorn api:app --host 0.0.0.0 --port 8000 --reload

# All requests now need x-api-key header
curl -H "x-api-key: my-secure-key-123" http://localhost:8000/start_session
```

**In Flutter:**
```dart
final headers = {
  'x-api-key': 'my-secure-key-123',
};

await http.post(
  Uri.parse('$baseUrl/start_session'),
  headers: headers,
);
```

## 📊 Monitoring Server Activity

Watch the PowerShell console for logs:
```
INFO:     Started session: abc-123-def-456
INFO:     Session abc-123: Processed 10 frames, Current emotions: {'happy': 7, 'neutral': 3}
INFO:     Session abc-123: Processed 20 frames, Current emotions: {'happy': 15, 'neutral': 5}
INFO:     Session abc-123 stopped: Duration=45.2s, Total frames=45, Emotions={'happy': 30, 'neutral': 15}
```

## 🎯 Expected Response Formats

### start_session response:
```json
{
  "session_id": "abc-123-def-456",
  "started_at": "2026-02-03T10:30:00"
}
```

### predict_frame response:
```json
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
```

### stop_session response:
```json
{
  "session_id": "abc-123",
  "duration_seconds": 45.2,
  "emotion_counts": {"happy": 30, "neutral": 15},
  "average_confidence": {"happy": 0.89, "neutral": 0.76},
  "timeline": [...],
  "saved_frames": {
    "happy": [
      {
        "timestamp": "2026-02-03T10:30:15",
        "confidence": 0.95,
        "frame_base64": "/9j/4AAQSkZJRg..."
      }
    ]
  },
  "summary": {
    "total_duration_seconds": 45.2,
    "total_frames_processed": 45,
    "dominant_emotions": [
      {"emotion": "happy", "count": 30, "percentage": 66.67}
    ],
    "session_quality": "good"
  }
}
```

## ✅ Final Pre-Flight Checklist

Before testing with Flutter app:

- [ ] Virtual environment activated
- [ ] `pip install -r requirements.txt` completed successfully
- [ ] Model file exists: `model/emotion_efficientnet.keras`
- [ ] Firewall rule created for port 8000
- [ ] Server running: `uvicorn api:app --host 0.0.0.0 --port 8000 --reload`
- [ ] Laptop IP address noted (from `ipconfig`)
- [ ] Phone browser can access `http://LAPTOP_IP:8000/health`
- [ ] Health check returns `{"status": "healthy", "model_loaded": true}`
- [ ] Flutter app baseUrl updated to `http://LAPTOP_IP:8000`

If all items checked ✓, you're ready to test your Flutter app!

## 🚀 Go Live!

1. Run `.\run_api.ps1`
2. Note the Network URL shown
3. Test health endpoint from phone browser
4. Launch Flutter app
5. Start interview session
6. Watch the magic happen! 🎉
