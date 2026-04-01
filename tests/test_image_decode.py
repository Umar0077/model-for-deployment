"""
Unit tests for image decoding functionality
Tests decode_image_from_upload with real JPEG and PNG fixtures
"""

import os
import sys
import io
import cv2
import numpy as np
from PIL import Image

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api import decode_image_from_upload, detect_image_format


def create_test_jpeg() -> bytes:
    """Create a tiny valid JPEG image for testing"""
    # Create a 10x10 red image
    img = np.zeros((10, 10, 3), dtype=np.uint8)
    img[:, :] = [0, 0, 255]  # BGR: Red
    
    # Encode to JPEG
    success, buffer = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 90])
    assert success, "Failed to create test JPEG"
    
    return buffer.tobytes()


def create_test_png() -> bytes:
    """Create a tiny valid PNG image for testing"""
    # Create a 10x10 blue image
    img = np.zeros((10, 10, 3), dtype=np.uint8)
    img[:, :] = [255, 0, 0]  # BGR: Blue
    
    # Encode to PNG
    success, buffer = cv2.imencode('.png', img)
    assert success, "Failed to create test PNG"
    
    return buffer.tobytes()


def create_test_png_with_pil() -> bytes:
    """Create a PNG using PIL (alternative format)"""
    # Create a 10x10 green image
    img = Image.new('RGB', (10, 10), color=(0, 255, 0))
    
    # Save to bytes
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    return buffer.getvalue()


def test_detect_jpeg_magic_bytes():
    """Test JPEG format detection from magic bytes"""
    jpeg_bytes = create_test_jpeg()
    detected = detect_image_format(jpeg_bytes)
    assert detected == "JPEG", f"Expected JPEG, got {detected}"
    print("✅ JPEG magic bytes detected correctly")


def test_detect_png_magic_bytes():
    """Test PNG format detection from magic bytes"""
    png_bytes = create_test_png()
    detected = detect_image_format(png_bytes)
    assert detected == "PNG", f"Expected PNG, got {detected}"
    print("✅ PNG magic bytes detected correctly")


def test_decode_valid_jpeg():
    """Test decoding a valid JPEG image"""
    jpeg_bytes = create_test_jpeg()
    img, error = decode_image_from_upload(jpeg_bytes, "image/jpeg", "test.jpg")
    
    assert img is not None, "Failed to decode valid JPEG"
    assert error is None, "Error should be None for valid JPEG"
    assert img.shape == (10, 10, 3), f"Wrong shape: {img.shape}"
    print(f"✅ Valid JPEG decoded successfully: shape={img.shape}")


def test_decode_valid_png():
    """Test decoding a valid PNG image"""
    png_bytes = create_test_png()
    img, error = decode_image_from_upload(png_bytes, "image/png", "test.png")
    
    assert img is not None, "Failed to decode valid PNG"
    assert error is None, "Error should be None for valid PNG"
    assert img.shape == (10, 10, 3), f"Wrong shape: {img.shape}"
    print(f"✅ Valid PNG decoded successfully: shape={img.shape}")


def test_decode_pil_png():
    """Test decoding a PIL-created PNG (tests PIL fallback)"""
    png_bytes = create_test_png_with_pil()
    img, error = decode_image_from_upload(png_bytes, "image/png", "test_pil.png")
    
    assert img is not None, "Failed to decode PIL PNG"
    assert error is None, "Error should be None for PIL PNG"
    assert img.shape == (10, 10, 3), f"Wrong shape: {img.shape}"
    print(f"✅ PIL PNG decoded successfully: shape={img.shape}")


def test_decode_empty_file():
    """Test that empty file returns proper error"""
    empty_bytes = b""
    img, error = decode_image_from_upload(empty_bytes, "image/jpeg", "empty.jpg")
    
    assert img is None, "Should return None for empty file"
    assert error is not None, "Should return error dict for empty file"
    assert error["error_code"] == "EMPTY_FILE", f"Wrong error code: {error['error_code']}"
    assert error["size_bytes"] == 0, "Size should be 0"
    print(f"✅ Empty file error handled correctly: {error['message']}")


def test_decode_invalid_data():
    """Test that invalid data returns proper error with hex bytes"""
    invalid_bytes = b"This is not an image file, just random text data"
    img, error = decode_image_from_upload(invalid_bytes, "application/octet-stream", "invalid.dat")
    
    assert img is None, "Should return None for invalid data"
    assert error is not None, "Should return error dict for invalid data"
    assert error["error_code"] == "DECODE_FAILED", f"Wrong error code: {error['error_code']}"
    assert "first_32_bytes_hex" in error, "Should include hex bytes"
    assert len(error["first_32_bytes_hex"]) > 0, "Hex bytes should not be empty"
    
    print(f"✅ Invalid data error handled correctly")
    print(f"   Error: {error['message']}")
    print(f"   First 32 bytes (hex): {error['first_32_bytes_hex']}")
    print(f"   Detected format: {error['detected_format']}")


def test_decode_truncated_jpeg():
    """Test that truncated JPEG returns proper error"""
    jpeg_bytes = create_test_jpeg()
    # Truncate to first 50 bytes
    truncated = jpeg_bytes[:50]
    
    img, error = decode_image_from_upload(truncated, "image/jpeg", "truncated.jpg")
    
    assert img is None, "Should return None for truncated JPEG"
    assert error is not None, "Should return error dict for truncated JPEG"
    assert "first_32_bytes_hex" in error, "Should include hex bytes"
    
    # Should still detect as JPEG from magic bytes
    detected_format = detect_image_format(truncated)
    assert detected_format == "JPEG", "Should still detect JPEG magic bytes"
    
    print(f"✅ Truncated JPEG error handled correctly")
    print(f"   Detected format: {detected_format}")
    print(f"   First 32 bytes (hex): {error['first_32_bytes_hex']}")


def run_all_tests():
    """Run all tests"""
    print("=" * 60)
    print("🧪 Running Image Decode Tests")
    print("=" * 60)
    
    tests = [
        test_detect_jpeg_magic_bytes,
        test_detect_png_magic_bytes,
        test_decode_valid_jpeg,
        test_decode_valid_png,
        test_decode_pil_png,
        test_decode_empty_file,
        test_decode_invalid_data,
        test_decode_truncated_jpeg,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"❌ {test.__name__} FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"❌ {test.__name__} ERROR: {e}")
            failed += 1
    
    print("=" * 60)
    print(f"📊 Test Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
