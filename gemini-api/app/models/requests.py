"""Request models for API endpoints"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List


class GenerateTextRequest(BaseModel):
    """Request model for generating text from user message"""
    
    message: str = Field(..., min_length=1, max_length=10000, description="User message")
    system_prompt: Optional[str] = Field(None, max_length=5000, description="System prompt to set context")
    context: Optional[str] = Field(None, max_length=10000, description="Additional context for the generation")
    temperature: Optional[float] = Field(0.7, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: Optional[int] = Field(1024, ge=1, le=8192, description="Maximum tokens to generate")
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "message": "Explain quantum computing in simple terms",
                    "system_prompt": "You are a helpful teacher explaining complex topics simply",
                    "temperature": 0.7,
                    "max_tokens": 500
                }
            ]
        }
    }


class SummarizeRequest(BaseModel):
    """Request model for text summarization"""
    
    text: str = Field(..., min_length=1, max_length=50000, description="Text to summarize")
    max_length: Optional[int] = Field(200, ge=50, le=2000, description="Maximum length of summary")
    style: Optional[str] = Field("concise", description="Summary style: concise, detailed, bullet-points")
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "text": "Long article text here...",
                    "max_length": 200,
                    "style": "concise"
                }
            ]
        }
    }


class ExtractJSONRequest(BaseModel):
    """Request model for extracting structured JSON from text"""
    
    text: str = Field(..., min_length=1, max_length=50000, description="Text to extract information from")
    schema: Dict[str, Any] = Field(..., description="JSON schema describing the expected structure")
    instructions: Optional[str] = Field(None, description="Additional extraction instructions")
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "text": "John Doe, age 30, lives in New York and works as a software engineer.",
                    "schema": {
                        "name": "string",
                        "age": "integer",
                        "city": "string",
                        "occupation": "string"
                    },
                    "instructions": "Extract person information from the text"
                }
            ]
        }
    }


class AnalyzeEmotionReportRequest(BaseModel):
    """Request model for analyzing emotion detection report"""
    
    emotion_counts: Dict[str, int] = Field(..., description="Emotion distribution counts")
    duration_seconds: float = Field(..., ge=0, description="Interview duration in seconds")
    dominant_emotions: List[Dict[str, Any]] = Field(..., description="Top dominant emotions with percentages")
    context: Optional[str] = Field(None, description="Additional context about the interview")
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "emotion_counts": {"happy": 30, "neutral": 15, "sad": 5},
                    "duration_seconds": 45.2,
                    "dominant_emotions": [
                        {"emotion": "happy", "count": 30, "percentage": 60.0}
                    ],
                    "context": "Job interview for software engineer position"
                }
            ]
        }
    }
