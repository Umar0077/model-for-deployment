"""
CLI Debug Tool #2: Capture webcam frame and upload
Captures one frame from webcam, encodes to JPEG, and posts to API

Usage:
    python debug_webcam_upload.py <session_id> [--base-url http://localhost:8000] [--camera 0]

Example:
    python debug_webcam_upload.py abc-123-def --base-url http://10.19.40.133:8000
    python debug_webcam_upload.py abc-123-def --camera 1  # Use second camera
"""

import sys
import argparse
import requests
import cv2
import numpy as np
from io import BytesIO


def capture_and_upload(session_id: str, base_url: str = "http://localhost:8000", camera_index: int = 0):
    """Capture one frame from webcam and upload to API"""
    
    print("=" * 60)
    print(f"📷 Capturing from webcam and uploading")
    print("=" * 60)
    print(f"   Camera Index: {camera_index}")
    print(f"   Session ID: {session_id}")
    print(f"   Base URL: {base_url}")
    print()
    
    # Open webcam
    print("📸 Opening camera...")
    cap = cv2.VideoCapture(camera_index)
    
    if not cap.isOpened():
        print(f"❌ Error: Cannot open camera {camera_index}")
        print("   Try a different camera index (0, 1, 2...)")
        return False
    
    # Set camera properties for better quality
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    print("✅ Camera opened successfully")
    print("📸 Capturing frame...")
    
    # Capture frame
    ret, frame = cap.read()
    cap.release()
    
    if not ret or frame is None:
        print("❌ Error: Failed to capture frame")
        return False
    
    print(f"✅ Frame captured: {frame.shape[1]}x{frame.shape[0]} pixels")
    print()
    
    # Encode to JPEG
    print("🔄 Encoding to JPEG...")
    success, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
    
    if not success:
        print("❌ Error: Failed to encode frame to JPEG")
        return False
    
    file_bytes = buffer.tobytes()
    file_size_kb = len(file_bytes) / 1024
    
    print(f"✅ Encoded successfully: {file_size_kb:.1f} KB ({len(file_bytes)} bytes)")
    
    # Show first 32 bytes as hex (same as server logs)
    first_32_hex = file_bytes[:32].hex()
    print(f"🔍 First 32 bytes (hex): {first_32_hex}")
    
    # Verify JPEG magic bytes
    if file_bytes[:3] == b'\xff\xd8\xff':
        print(f"🔍 JPEG magic bytes verified: FF D8 FF")
    else:
        print(f"⚠️ Warning: JPEG magic bytes not found!")
    
    print()
    
    # Prepare multipart form data
    files = {
        'frame': ('webcam_frame.jpg', file_bytes, 'image/jpeg')
    }
    data = {
        'session_id': session_id
    }
    
    # Make request
    url = f"{base_url}/predict_frame"
    print(f"📡 Sending POST request to: {url}")
    
    try:
        response = requests.post(url, files=files, data=data, timeout=30)
        
        print()
        print(f"📥 Response Status: {response.status_code}")
        print()
        
        if response.status_code == 200:
            result = response.json()
            print("✅ SUCCESS!")
            print()
            print(f"   Faces Found: {result.get('faces_found', 0)}")
            
            if result.get('top_result'):
                top = result['top_result']
                print(f"   Top Emotion: {top['emotion']}")
                print(f"   Confidence: {top['confidence']:.2%}")
                print(f"   Bounding Box: {top['bbox']}")
            
            if result.get('results'):
                print()
                print(f"   All Results ({len(result['results'])} faces):")
                for i, res in enumerate(result['results'], 1):
                    print(f"      Face {i}: {res['emotion']} ({res['confidence']:.2%}) at {res['bbox']}")
            else:
                print()
                print("   ℹ️ No faces detected in frame")
                print("   Try adjusting camera angle or lighting")
            
            return True
        else:
            print("❌ ERROR!")
            print()
            try:
                error = response.json()
                print(f"   Error Code: {error.get('error_code', 'N/A')}")
                print(f"   Message: {error.get('message', response.text)}")
                
                if 'first_32_bytes_hex' in error:
                    print(f"   Server received (hex): {error['first_32_bytes_hex']}")
                    print(f"   Client sent (hex):     {first_32_hex}")
                    if error['first_32_bytes_hex'] != first_32_hex:
                        print(f"   ⚠️ MISMATCH! Bytes changed during transfer!")
                
                if 'detected_format' in error:
                    print(f"   Server detected format: {error['detected_format']}")
            except:
                print(f"   Response: {response.text}")
            
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"❌ Connection Error: Cannot connect to {base_url}")
        print(f"   Make sure the server is running!")
        return False
    except requests.exceptions.Timeout:
        print(f"❌ Timeout: Server did not respond within 30 seconds")
        return False
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Capture webcam frame and upload to emotion detection API"
    )
    parser.add_argument("session_id", help="Session ID from /start_session")
    parser.add_argument("--base-url", default="http://localhost:8000", 
                       help="API base URL (default: http://localhost:8000)")
    parser.add_argument("--camera", type=int, default=0,
                       help="Camera index (default: 0)")
    
    args = parser.parse_args()
    
    success = capture_and_upload(args.session_id, args.base_url, args.camera)
    
    print()
    print("=" * 60)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

