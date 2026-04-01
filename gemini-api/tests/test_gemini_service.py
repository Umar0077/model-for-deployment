"""Unit tests for Gemini service"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.gemini_service import GeminiService
from app.config import settings


@pytest.fixture
def gemini_service():
    """Create GeminiService instance for testing"""
    return GeminiService()


@pytest.fixture
def mock_gemini_response():
    """Mock Gemini API response"""
    mock_response = MagicMock()
    mock_response.text = "Generated text response"
    return mock_response


@pytest.mark.asyncio
async def test_generate_text_success(gemini_service, mock_gemini_response):
    """Test successful text generation with primary model"""
    
    with patch.object(gemini_service, '_generate_with_fallback', new_callable=AsyncMock) as mock_generate:
        mock_generate.return_value = ("This is a generated response", "gemini-2.5-flash")
        
        result, model_used = await gemini_service.generate_text(
            message="Test prompt",
            temperature=0.7,
            max_tokens=100
        )
        
        assert result == "This is a generated response"
        assert model_used == "gemini-2.5-flash"
        mock_generate.assert_called_once()


@pytest.mark.asyncio
async def test_generate_text_with_fallback(gemini_service):
    """Test text generation falls back to secondary model"""
    
    with patch('asyncio.to_thread', new_callable=AsyncMock) as mock_thread:
        # First call fails with model not found, second succeeds with fallback
        primary_error = Exception("Model not found: gemini-2.5-flash")
        fallback_response = MagicMock()
        fallback_response.text = "Fallback response"
        
        mock_thread.side_effect = [primary_error, fallback_response]
        
        result, model_used = await gemini_service.generate_text(
            message="Test prompt",
            temperature=0.7,
            max_tokens=100
        )
        
        assert result == "Fallback response"
        assert model_used == "gemini-2.5-flash-lite"


@pytest.mark.asyncio
async def test_summarize_text(gemini_service):
    """Test text summarization"""
    
    with patch.object(gemini_service, '_generate_with_fallback', new_callable=AsyncMock) as mock_generate:
        mock_generate.return_value = ("This is a summary", "gemini-2.5-flash")
        
        result, model_used = await gemini_service.summarize(
            text="Long text to summarize",
            max_length=50
        )
        
        assert result == "This is a summary"
        assert model_used == "gemini-2.5-flash"


@pytest.mark.asyncio
async def test_extract_json_data(gemini_service):
    """Test JSON extraction"""
    
    with patch.object(gemini_service, '_generate_with_fallback', new_callable=AsyncMock) as mock_generate:
        mock_generate.return_value = ('{"name": "John", "age": 30}', "gemini-2.5-flash")
        
        result, raw_text, model_used = await gemini_service.extract_json(
            text="Extract data from this text",
            schema={"name": "string", "age": "integer"}
        )
        
        assert result == {"name": "John", "age": 30}
        assert model_used == "gemini-2.5-flash"


@pytest.mark.asyncio
async def test_analyze_emotion_report(gemini_service):
    """Test emotion report analysis"""
    
    response_json = """{
        "analysis": "The candidate showed confidence and composure.",
        "insights": {
            "overall_sentiment": "positive",
            "confidence_level": "high"
        },
        "recommendations": ["Maintain composure", "Show enthusiasm"]
    }"""
    
    with patch.object(gemini_service, '_generate_with_fallback', new_callable=AsyncMock) as mock_generate:
        mock_generate.return_value = (response_json, "gemini-2.5-flash")
        
        analysis, insights, recommendations, model_used = await gemini_service.analyze_emotion_report(
            emotion_counts={"happy": 80, "neutral": 20},
            duration_seconds=45.0,
            dominant_emotions=[{"emotion": "happy", "percentage": 80.0}]
        )
        
        assert "confidence" in analysis.lower()
        assert insights["overall_sentiment"] == "positive"
        assert len(recommendations) == 2
        assert model_used == "gemini-2.5-flash"


@pytest.mark.asyncio
async def test_fallback_on_model_not_found(gemini_service):
    """Test fallback mechanism when primary model is not found"""
    
    with patch('asyncio.to_thread', new_callable=AsyncMock) as mock_thread:
        # Primary model fails with "model not found"
        primary_error = Exception("Model not found")
        
        # Fallback model succeeds
        fallback_response = MagicMock()
        fallback_response.text = "Fallback success"
        
        mock_thread.side_effect = [primary_error, fallback_response]
        
        result, model_used = await gemini_service._generate_with_fallback(
            prompt="Test",
            temperature=0.7,
            max_output_tokens=100
        )
        
        assert result == "Fallback success"
        assert model_used == settings.gemini_fallback_model_id


@pytest.mark.asyncio
async def test_no_fallback_on_other_errors(gemini_service):
    """Test that fallback is NOT used for non-model-not-found errors"""
    
    with patch('asyncio.to_thread', new_callable=AsyncMock) as mock_thread:
        # Primary model fails with different error (e.g., quota exceeded)
        primary_error = Exception("Quota exceeded")
        mock_thread.side_effect = primary_error
        
        with pytest.raises(Exception, match="Quota exceeded"):
            await gemini_service._generate_with_fallback(
                prompt="Test",
                temperature=0.7,
                max_output_tokens=100
            )


@pytest.mark.asyncio
async def test_both_models_fail(gemini_service):
    """Test behavior when both primary and fallback models fail"""
    
    with patch('asyncio.to_thread', new_callable=AsyncMock) as mock_thread:
        # Both models fail
        primary_error = Exception("Model not found: primary")
        fallback_error = Exception("Model not found: fallback")
        
        mock_thread.side_effect = [primary_error, fallback_error]
        
        with pytest.raises(Exception) as exc_info:
            await gemini_service._generate_with_fallback(
                prompt="Test",
                temperature=0.7,
                max_output_tokens=100
            )
        
        error_msg = str(exc_info.value)
        assert "Both primary model" in error_msg
        assert "fallback model" in error_msg
