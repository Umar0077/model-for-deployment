"""
CLI Debug Tool #1: Test image upload from local file
Posts a local JPEG/PNG file to the emotion detection API

Usage:
    python debug_upload_file.py <image_path> <session_id> [--base-url http://localhost:8000]

Example:
    python debug_upload_file.py test.jpg abc-123-def --base-url http://10.19.40.133:8000
"""

import sys
import argparse
import requests
from pathlib import Path


def upload_file_to_api(image_path: str, session_id: str, base_url: str = "http://localhost:8000"):
    """Upload a local image file to the predict_frame endpoint"""
    
    image_file = Path(image_path)
    
    if not image_file.exists():
        print(f"❌ Error: File not found: {image_path}")
        return False
    
    print("=" * 60)
    print(f"📤 Uploading to Emotion Detection API")
    print("=" * 60)
    print(f"   File: {image_file.name}")
    print(f"   Size: {image_file.stat().st_size} bytes ({image_file.stat().st_size / 1024:.1f} KB)")
    print(f"   Session ID: {session_id}")
    print(f"   Base URL: {base_url}")
    print()
    
    # Read file
    with open(image_file, 'rb') as f:
        file_bytes = f.read()
    
    # Show first 32 bytes as hex (same as server logs)
    first_32_hex = file_bytes[:32].hex()
    print(f"🔍 First 32 bytes (hex): {first_32_hex}")
    
    # Detect format from magic bytes
    if file_bytes[:3] == b'\xff\xd8\xff':
        detected_format = "JPEG"
    elif file_bytes[:8] == b'\x89\x50\x4e\x47\x0d\x0a\x1a\x0a':
        detected_format = "PNG"
    else:
        detected_format = "Unknown"
    
    print(f"🔍 Detected format: {detected_format}")
    print()
    
    # Prepare multipart form data
    files = {
        'frame': (image_file.name, file_bytes, 'image/jpeg' if detected_format == "JPEG" else 'image/png')
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
                    print(f"      Face {i}: {res['emotion']} ({res['confidence']:.2%})")
            
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
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Upload a local image file to the emotion detection API for debugging"
    )
    parser.add_argument("image_path", help="Path to JPEG or PNG image file")
    parser.add_argument("session_id", help="Session ID from /start_session")
    parser.add_argument("--base-url", default="http://localhost:8000", 
                       help="API base URL (default: http://localhost:8000)")
    
    args = parser.parse_args()
    
    success = upload_file_to_api(args.image_path, args.session_id, args.base_url)
    
    print()
    print("=" * 60)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

