Facial Expression Recognition Project

1. Train model on Google Colab
2. Download emotion_efficientnet.keras
3. Place model in model folder
4. Install requirements
5. Run webcam_app.py for live detection
6. Run image_test.py for unseen images

==========================================
FastAPI Backend for Interview Analysis
==========================================

The emotion detection model is now exposed as a REST API service that Flutter apps 
or any HTTP client can use for real-time emotion analysis during interviews.

QUICK START - RUN WITH ONE COMMAND
-----------------------------------
Simply run the provided PowerShell script:
   .\run_api.ps1

This script will:
- Activate your virtual environment (if present)
- Install/update all dependencies
- Show your network IP address
- Start the server on port 8000

==========================================
RUN FASTAPI FOR MOBILE TESTING
==========================================

STEP 1: Find Your Laptop's IP Address
--------------------------------------
Open PowerShell and run:
   ipconfig

Look for your active network adapter (usually "Wireless LAN adapter Wi-Fi"):
   IPv4 Address. . . . . . . . . . . : 192.168.1.XXX

Note this IP address (e.g., 10.19.40.133)

STEP 2: Allow Port 8000 in Windows Firewall
--------------------------------------------
Option A - Quick Test (Temporary):
   # Temporarily disable Windows Firewall for private networks
   # Not recommended for production!
   
Option B - Proper Rule (Recommended):
   1. Open Windows Defender Firewall with Advanced Security
   2. Click "Inbound Rules" → "New Rule"
   3. Select "Port" → Next
   4. TCP, Specific local ports: 8000 → Next
   5. "Allow the connection" → Next
   6. Check "Private" network (your home WiFi) → Next
   7. Name: "Emotion API Port 8000" → Finish

OR use PowerShell as Administrator:
   New-NetFirewallRule -DisplayName "Emotion API" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow -Profile Private

STEP 3: Start the FastAPI Server
---------------------------------
Run the server accessible to network devices:
   uvicorn api:app --host 0.0.0.0 --port 8000 --reload

You should see:
   INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
   INFO:     Loading model from [path]
   INFO:     Model loaded successfully

The server is now listening on ALL network interfaces (0.0.0.0 means all IPs)

STEP 4: Test from Your Phone Browser
-------------------------------------
Ensure your phone is on the SAME WiFi network as your laptop!

Open your phone's browser and navigate to:
   http://192.168.1.XXX:8000/health
   
Replace XXX with YOUR laptop's IP from Step 1.

You should see JSON response:
   {
     "status": "healthy",
     "model_loaded": true,
     "active_sessions": 0,
     "timestamp": "2026-02-03T..."
   }

If successful, your Flutter app can now connect using:
   http://192.168.1.XXX:8000

STEP 5: Configure Flutter App
------------------------------
In your Flutter app, update the base URL to:
   final String baseUrl = "http://192.168.1.XXX:8000";

Replace XXX with your laptop's IP address.

TROUBLESHOOTING MOBILE CONNECTION
----------------------------------
❌ "Connection refused" or "Cannot connect"
   → Check firewall rule is active (Step 2)
   → Verify both devices are on SAME WiFi network
   → Make sure server is running with --host 0.0.0.0
   → Try pinging laptop from phone: ping 192.168.1.XXX

❌ "Connection timeout"
   → Windows Firewall might be blocking
   → Some WiFi routers have "AP Isolation" enabled - disable it
   → Check antivirus software isn't blocking connections

❌ 404 errors
   → Verify the URL path: http://IP:8000/health (not /Health or missing /health)
   → Server might not be running - check PowerShell window

✅ Test sequence:
   1. Phone browser → http://192.168.1.XXX:8000/health works?
   2. Phone browser → http://192.168.1.XXX:8000/docs shows API docs?
   3. If both work, Flutter app should connect successfully!

INSTALLATION
------------
1. Ensure you're in the project root directory
2. Activate your virtual environment (if using one):
   .venv\Scripts\Activate.ps1

3. Install all dependencies including FastAPI:
   pip install -r requirements.txt

RUNNING THE API SERVER
----------------------
Development mode (with auto-reload):
   uvicorn api:app --host 0.0.0.0 --port 8000 --reload

Production mode:
   uvicorn api:app --host 0.0.0.0 --port 8000 --workers 4

The API will be available at: http://localhost:8000
Interactive API documentation: http://localhost:8000/docs
Alternative docs: http://localhost:8000/redoc

OPTIONAL CONFIGURATION
---------------------
Set environment variables to customize behavior:

API Security (optional API key protection):
   # In PowerShell, set the API key BEFORE running the server:
   $env:API_KEY = "your-secret-key-here"
   
   # Then run the server:
   uvicorn api:app --host 0.0.0.0 --port 8000 --reload
   
   # All requests must now include the header:
   # x-api-key: your-secret-key-here
   
   # To disable API key (for testing):
   Remove-Item Env:\API_KEY
   
   # For Flutter, add to HTTP headers:
   headers: {'x-api-key': 'your-secret-key-here'}

Other Configuration Options:
   # Max frames stored per emotion (default: 10)
   $env:MAX_FRAMES_PER_EMOTION = "15"

   # Session timeout in minutes (default: 30)
   $env:SESSION_TIMEOUT_MINUTES = "60"

   # Max input frame width for performance (default: 1280)
   $env:INPUT_FRAME_MAX_WIDTH = "1920"

TESTING API KEY PROTECTION
---------------------------
# Start server with API key:
$env:API_KEY = "test123"
uvicorn api:app --host 0.0.0.0 --port 8000 --reload

# Test without key (should fail with 401):
curl http://localhost:8000/start_session

# Test with correct key (should succeed):
curl -H "x-api-key: test123" http://localhost:8000/start_session

# Note: /health endpoint works without API key for monitoring

# Max input frame width for performance (default: 1280)
$env:INPUT_FRAME_MAX_WIDTH = "1920"

API ENDPOINTS
-------------
1. GET /health - Check API health and status
2. POST /start_session - Start a new interview session
3. POST /predict_frame - Send a frame for emotion detection
4. POST /stop_session - End session and get complete report
5. POST /reset_session - Reset session data (debugging)

EXAMPLE USAGE WITH CURL (PowerShell)
------------------------------------

# 1. Health Check
curl http://localhost:8000/health

# 2. Start a session
$response = curl -Method POST http://localhost:8000/start_session | ConvertFrom-Json
$sessionId = $response.session_id
echo "Session ID: $sessionId"

# 3. Send a frame for prediction (replace with your image path)
curl -Method POST `
  -Form "session_id=$sessionId" `
  -Form "file=@test_image.jpg" `
  http://localhost:8000/predict_frame

# 4. Send multiple frames in a loop (example)
Get-ChildItem .\frames\*.jpg | ForEach-Object {
  curl -Method POST `
    -Form "session_id=$sessionId" `
    -Form "file=@$($_.FullName)" `
    http://localhost:8000/predict_frame
  Start-Sleep -Milliseconds 100
}

# 5. Stop session and get complete report
curl -Method POST `
  -ContentType "application/json" `
  -Body "{`"session_id`": `"$sessionId`"}" `
  http://localhost:8000/stop_session

EXAMPLE USAGE WITH Python Requests
----------------------------------
import requests
import time

BASE_URL = "http://localhost:8000"

# Start session
response = requests.post(f"{BASE_URL}/start_session")
session_id = response.json()["session_id"]
print(f"Session started: {session_id}")

# Send frames
with open("test_image.jpg", "rb") as f:
    files = {"file": f}
    data = {"session_id": session_id}
    response = requests.post(f"{BASE_URL}/predict_frame", files=files, data=data)
    print(response.json())

# Stop session
response = requests.post(f"{BASE_URL}/stop_session", json={"session_id": session_id})
report = response.json()
print(f"Emotion counts: {report['emotion_counts']}")
print(f"Dominant emotion: {report['summary']['dominant_emotions'][0]}")

FLUTTER INTEGRATION EXAMPLE
---------------------------
import 'package:http/http.dart' as http;
import 'dart:convert';

final baseUrl = 'http://your-server:8000';

// Start session
Future<String> startSession() async {
  final response = await http.post(Uri.parse('$baseUrl/start_session'));
  return json.decode(response.body)['session_id'];
}

// Send frame
Future<Map> sendFrame(String sessionId, List<int> imageBytes) async {
  var request = http.MultipartRequest('POST', Uri.parse('$baseUrl/predict_frame'));
  request.fields['session_id'] = sessionId;
  request.files.add(http.MultipartFile.fromBytes('file', imageBytes, filename: 'frame.jpg'));
  
  var response = await request.send();
  var responseBody = await response.stream.bytesToString();
  return json.decode(responseBody);
}

// Stop session
Future<Map> stopSession(String sessionId) async {
  final response = await http.post(
    Uri.parse('$baseUrl/stop_session'),
    headers: {'Content-Type': 'application/json'},
    body: json.encode({'session_id': sessionId}),
  );
  return json.decode(response.body);
}

RESPONSE FORMATS
----------------
predict_frame response includes:
- faces_found: number of faces detected
- top_result: highest confidence detection with emotion, confidence, bbox
- results: all face detections in frame
- stored_frame_update: current count of stored frames per emotion

stop_session response includes:
- emotion_counts: total detections per emotion
- average_confidence: average confidence per emotion
- timeline: chronological list of all detections
- saved_frames: best frames per emotion (base64 encoded JPEG)
- summary: compact object for LLM analysis including:
  * total_duration_seconds
  * dominant_emotions (top 3 with percentages)
  * emotion_distribution
  * session_quality rating

SECURITY NOTES
--------------
- For production, always set an API_KEY environment variable
- The API will require x-api-key header when API_KEY is set
- Use HTTPS in production (configure with reverse proxy like nginx)
- Consider rate limiting for public deployments

TROUBLESHOOTING
---------------
- If port 8000 is busy, use --port 8001 or another port
- Ensure model file exists at model/emotion_efficientnet.keras
- Check that src/ folder is in the same directory as api.py
- For CORS issues with web clients, add CORS middleware to api.py

ARCHITECTURE NOTES
------------------
- Sessions are stored in-memory (ideal for single-server deployments)
- For multi-server deployments, migrate session storage to Redis:
  * Replace sessions dict with Redis client
  * Store SessionData as JSON in Redis
  * Use Redis TTL for automatic cleanup
- Model is loaded once on startup for efficiency
- Frame selection uses confidence + temporal diversity to avoid duplicates
- Preprocessing matches training pipeline (no normalization by default)

==========================================
MOBILE TESTING CHECKLIST
==========================================

Before testing your Flutter app with the API:

□ LAPTOP SETUP
  □ Virtual environment activated (.venv\Scripts\Activate.ps1)
  □ Requirements installed (pip install -r requirements.txt)
  □ Model file exists at model/emotion_efficientnet.keras
  □ API server running: uvicorn api:app --host 0.0.0.0 --port 8000 --reload
  □ Server logs show "Model loaded successfully"
  
□ NETWORK CONFIGURATION
  □ Laptop IPv4 address noted (run: ipconfig)
     Example: 10.19.40.133
  □ Windows Firewall rule created for port 8000 (private network)
  □ Laptop and phone on SAME WiFi network
  □ No VPN active on laptop (can interfere with local network)

□ PHONE VERIFICATION
  □ Phone browser can access http://YOUR_IP:8000/health
  □ Health check returns {"status": "healthy", "model_loaded": true}
  □ API docs accessible at http://YOUR_IP:8000/docs
  
□ FLUTTER APP CONFIGURATION
  □ baseUrl set to "http://YOUR_IP:8000" (not localhost!)
  □ If using API key: headers include 'x-api-key' header
  □ Test start_session endpoint first
  □ Verify session_id is returned and stored
  □ Test predict_frame with sample image
  □ Test stop_session returns full report

□ TROUBLESHOOTING CHECKLIST
  □ Can you ping laptop from phone? (use network tools app)
  □ Is server running on 0.0.0.0 (not 127.0.0.1)?
  □ Check server logs in PowerShell for errors
  □ Try accessing from laptop browser first: http://localhost:8000/health
  □ Try accessing from phone on different port to rule out firewall
  □ Disable Windows Firewall temporarily to test (re-enable after!)

QUICK TEST COMMANDS (PowerShell)
---------------------------------
# 1. Find your IP
ipconfig | Select-String "IPv4"

# 2. Test locally first
curl http://localhost:8000/health

# 3. Test firewall rule
Test-NetConnection -ComputerName localhost -Port 8000

# 4. Check if server is listening on all interfaces
netstat -an | Select-String "8000"
# Should show: 0.0.0.0:8000 (not 127.0.0.1:8000)

LIVE TESTING WORKFLOW
---------------------
1. Run: .\run_api.ps1
2. Note the "Network URL" shown in console
3. Open phone browser → http://NETWORK_URL/health
4. If successful, open Flutter app
5. Start interview session in app
6. Hold phone camera to face
7. App sends frames periodically
8. Monitor PowerShell for logs: "Processed X frames"
9. Stop session in app
10. App receives emotion report with saved frames
11. Review dominant emotions and timeline

EXPECTED SERVER LOGS
--------------------
When everything works correctly, you'll see:

INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     ============================================================
INFO:     Emotion Detection API Server Starting
INFO:     Model: c:\...\model\emotion_efficientnet.keras
INFO:     API Key Protection: DISABLED
INFO:     Max Frames per Emotion: 10
INFO:     Session Timeout: 30 minutes
INFO:     ============================================================
INFO:     Started session: abc123-def456-...
INFO:     Session abc123: Processed 10 frames, Current emotions: {'happy': 7, 'neutral': 3}
INFO:     Session abc123: Processed 20 frames, Current emotions: {'happy': 15, 'neutral': 5}
INFO:     Session abc123 stopped: Duration=45.2s, Total frames=45, Emotions={'happy': 30, 'neutral': 15}


