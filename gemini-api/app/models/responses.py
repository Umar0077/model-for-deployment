"""Response models for API endpoints"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class GenerateTextResponse(BaseModel):
    """Response model for text generation"""
    
    text: str = Field(..., description="Generated text")
    request_id: str = Field(..., description="Unique request identifier")
    model: str = Field(..., description="Model used for generation")
    tokens_used: Optional[int] = Field(None, description="Approximate tokens used")
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "text": "Quantum computing uses quantum bits...",
                    "request_id": "req_abc123",
                    "model": "gemini-pro",
                    "tokens_used": 150
                }
            ]
        }
    }


class SummarizeResponse(BaseModel):
    """Response model for text summarization"""
    
    summary: str = Field(..., description="Generated summary")
    original_length: int = Field(..., description="Length of original text")
    summary_length: int = Field(..., description="Length of summary")
    compression_ratio: float = Field(..., description="Ratio of summary to original length")
    request_id: str = Field(..., description="Unique request identifier")
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "summary": "This is a concise summary...",
                    "original_length": 1000,
                    "summary_length": 200,
                    "compression_ratio": 0.2,
                    "request_id": "req_def456"
                }
            ]
        }
    }


class ExtractJSONResponse(BaseModel):
    """Response model for JSON extraction"""
    
    data: Dict[str, Any] = Field(..., description="Extracted structured data")
    raw_text: str = Field(..., description="Raw text from model before JSON parsing")
    request_id: str = Field(..., description="Unique request identifier")
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "data": {
                        "name": "John Doe",
                        "age": 30,
                        "city": "New York",
                        "occupation": "software engineer"
                    },
                    "raw_text": "{'name': 'John Doe', ...}",
                    "request_id": "req_ghi789"
                }
            ]
        }
    }


class AnalyzeEmotionReportResponse(BaseModel):
    """Response model for emotion report analysis"""
    
    analysis: str = Field(..., description="Detailed analysis of the emotion report")
    insights: Dict[str, Any] = Field(..., description="Key insights extracted from the report")
    recommendations: list[str] = Field(..., description="Recommendations based on emotion patterns")
    request_id: str = Field(..., description="Unique request identifier")
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "analysis": "The candidate showed predominantly positive emotions...",
                    "insights": {
                        "overall_sentiment": "positive",
                        "confidence_level": "high",
                        "stress_indicators": "low"
                    },
                    "recommendations": [
                        "Candidate appears confident and engaged",
                        "Consider for next interview round"
                    ],
                    "request_id": "req_jkl012"
                }
            ]
        }
    }


class ErrorResponse(BaseModel):
    """Response model for errors"""
    
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    request_id: str = Field(..., description="Unique request identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "error": "Invalid request",
                    "detail": "Message field cannot be empty",
                    "request_id": "req_error123",
                    "timestamp": "2026-02-03T18:00:00Z"
                }
            ]
        }
    }
