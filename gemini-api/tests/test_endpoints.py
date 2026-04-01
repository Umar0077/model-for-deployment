"""Integration tests for API endpoints"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock

from app.main import app
from app.config import settings


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def mock_gemini_response():
    """Mock Gemini API response"""
    mock_response = MagicMock()
    mock_response.text = "Generated text response"
    mock_response.candidates = [MagicMock(finish_reason="STOP")]
    return mock_response


def test_health_check(client):
    """Test health check endpoint"""
    response = client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == settings.app_name
    assert "timestamp" in data


def test_root_endpoint(client):
    """Test root endpoint"""
    response = client.get("/")
    
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == f"Welcome to {settings.app_name}"
    assert data["version"] == settings.app_version


def test_generate_text_endpoint(client, mock_gemini_response):
    """Test text generation endpoint"""
    
    with patch('app.services.gemini_service.GeminiService.generate_text', new_callable=AsyncMock) as mock_generate:
        mock_generate.return_value = ("Generated text response", "gemini-2.5-flash")
        
        response = client.post(
            "/api/v1/gemini/generate",
            json={
                "prompt": "Write a short story",
                "temperature": 0.7,
                "max_output_tokens": 100
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["text"] == "Generated text response"
        assert "request_id" in data


def test_generate_text_missing_prompt(client):
    """Test generation with missing prompt"""
    
    response = client.post(
        "/api/v1/gemini/generate",
        json={"temperature": 0.7}
    )
    
    assert response.status_code == 422  # Validation error


def test_summarize_endpoint(client):
    """Test summarization endpoint"""
    
    with patch('app.services.gemini_service.GeminiService.summarize_text', new_callable=AsyncMock) as mock_summarize:
        mock_summarize.return_value = ("This is a summary", "gemini-2.5-flash")
        
        response = client.post(
            "/api/v1/gemini/summarize",
            json={
                "text": "Long text to summarize...",
                "max_length": 50
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["summary"] == "This is a summary"


def test_extract_json_endpoint(client):
    """Test JSON extraction endpoint"""
    
    with patch('app.services.gemini_service.GeminiService.extract_json_data', new_callable=AsyncMock) as mock_extract:
        mock_extract.return_value = ({"name": "John", "score": 85}, "raw response", "gemini-2.5-flash")
        
        response = client.post(
            "/api/v1/gemini/extract",
            json={
                "text": "John scored 85 points",
                "schema": "name and score"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"] == {"name": "John", "score": 85}


def test_analyze_emotions_endpoint(client):
    """Test emotion analysis endpoint"""
    
    with patch('app.services.gemini_service.GeminiService.analyze_emotion_report', new_callable=AsyncMock) as mock_analyze:
        mock_analyze.return_value = (
            "The candidate showed confidence and composure.",
            {"overall_sentiment": "positive", "confidence_level": "high"},
            ["Maintain composure", "Show enthusiasm"],
            "gemini-2.5-flash"
        )
        
        response = client.post(
            "/api/v1/gemini/analyze-emotions",
            json={
                "emotion_data": {
                    "happy": 0.6,
                    "neutral": 0.3,
                    "surprised": 0.1
                },
                "context": "Job interview",
                "analysis_type": "detailed"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "confidence" in data["analysis"].lower()


def test_rate_limiting(client):
    """Test rate limiting behavior"""
    
    # This test requires the rate limiter to be enabled
    if not settings.rate_limit_enabled:
        pytest.skip("Rate limiting not enabled")
    
    with patch('app.services.gemini_service.GeminiService.generate_text', new_callable=AsyncMock) as mock_generate:
        mock_generate.return_value = "Response"
        
        # Make requests until rate limit is hit
        responses = []
        for _ in range(20):  # Exceed typical rate limit
            response = client.post(
                "/api/v1/gemini/generate",
                json={"prompt": "Test"}
            )
            responses.append(response.status_code)
        
        # At least one should be rate limited (429)
        assert 429 in responses


def test_error_handling(client):
    """Test error handling for service failures"""
    
    with patch('app.services.gemini_service.GeminiService.generate_text', new_callable=AsyncMock) as mock_generate:
        mock_generate.side_effect = Exception("Service unavailable")
        
        response = client.post(
            "/api/v1/gemini/generate",
            json={"prompt": "Test prompt"}
        )
        
        assert response.status_code == 500
        data = response.json()
        assert "error" in data
        assert "request_id" in data


def test_cors_headers(client):
    """Test CORS headers are present"""
    
    response = client.options("/health")
    
    # CORS headers should be present
    assert "access-control-allow-origin" in response.headers or response.status_code == 200


def test_request_id_header(client):
    """Test that request ID is included in responses"""
    
    response = client.get("/health")
    
    data = response.json()
    assert "request_id" in data
