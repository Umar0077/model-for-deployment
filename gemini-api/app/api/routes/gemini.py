"""Gemini AI routes"""

from fastapi import APIRouter, HTTPException, Request, Depends, Header
from typing import Optional

from app.models.requests import (
    GenerateTextRequest,
    SummarizeRequest,
    ExtractJSONRequest,
    AnalyzeEmotionReportRequest
)
from app.models.responses import (
    GenerateTextResponse,
    SummarizeResponse,
    ExtractJSONResponse,
    AnalyzeEmotionReportResponse,
    ErrorResponse
)
from app.services.gemini_service import gemini_service
from app.config import settings
from app.utils.logger import get_logger
from app.middleware.rate_limiter import limiter

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Gemini AI"])


async def verify_api_key(x_api_key: Optional[str] = Header(None)):
    """Verify API key if configured"""
    if settings.api_key and x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return True


@router.post(
    "/generate",
    response_model=GenerateTextResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}
)
@limiter.limit(f"{settings.rate_limit_requests}/{settings.rate_limit_period}second")
async def generate_text(
    request: Request,
    body: GenerateTextRequest,
    _: bool = Depends(verify_api_key)
):
    """
    Generate text response from user message
    
    Supports:
    - Custom system prompts
    - Additional context
    - Temperature control
    - Token limit control
    """
    request_id = request.state.request_id
    
    logger.info(
        "generate_text_request",
        request_id=request_id,
        message_length=len(body.message)
    )
    
    try:
        result, model_used = await gemini_service.generate_text(
            message=body.message,
            system_prompt=body.system_prompt,
            context=body.context,
            temperature=body.temperature,
            max_tokens=body.max_tokens
        )
        
        return GenerateTextResponse(
            text=result,
            request_id=request_id,
            model=model_used,
            tokens_used=len(result.split())  # Approximate
        )
        
    except Exception as e:
        logger.error("generate_text_error", request_id=request_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")


@router.post(
    "/summarize",
    response_model=SummarizeResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}
)
@limiter.limit(f"{settings.rate_limit_requests}/{settings.rate_limit_period}second")
async def summarize_text(
    request: Request,
    body: SummarizeRequest,
    _: bool = Depends(verify_api_key)
):
    """
    Summarize long text
    
    Supports different summary styles:
    - concise: Brief summary
    - detailed: Comprehensive summary with key points
    - bullet-points: Summary in bullet point format
    """
    request_id = request.state.request_id
    
    logger.info(
        "summarize_request",
        request_id=request_id,
        text_length=len(body.text),
        style=body.style
    )
    
    try:
        summary, model_used = await gemini_service.summarize(
            text=body.text,
            max_length=body.max_length,
            style=body.style
        )
        
        original_length = len(body.text)
        summary_length = len(summary)
        compression_ratio = summary_length / original_length if original_length > 0 else 0
        
        return SummarizeResponse(
            summary=summary,
            original_length=original_length,
            summary_length=summary_length,
            compression_ratio=round(compression_ratio, 3),
            request_id=request_id
        )
        
    except Exception as e:
        logger.error("summarize_error", request_id=request_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Summarization failed: {str(e)}")


@router.post(
    "/extract",
    response_model=ExtractJSONResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}
)
@limiter.limit(f"{settings.rate_limit_requests}/{settings.rate_limit_period}second")
async def extract_json(
    request: Request,
    body: ExtractJSONRequest,
    _: bool = Depends(verify_api_key)
):
    """
    Extract structured JSON from unstructured text
    
    Provide a schema describing the expected JSON structure,
    and the AI will extract matching information from the text.
    """
    request_id = request.state.request_id
    
    logger.info(
        "extract_json_request",
        request_id=request_id,
        text_length=len(body.text),
        schema_keys=list(body.schema.keys())
    )
    
    try:
        data, raw_text, model_used = await gemini_service.extract_json(
            text=body.text,
            schema=body.schema,
            instructions=body.instructions
        )
        
        return ExtractJSONResponse(
            data=data,
            raw_text=raw_text,
            request_id=request_id
        )
        
    except Exception as e:
        logger.error("extract_json_error", request_id=request_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"JSON extraction failed: {str(e)}")


@router.post(
    "/analyze-emotions",
    response_model=AnalyzeEmotionReportResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}
)
@limiter.limit(f"{settings.rate_limit_requests}/{settings.rate_limit_period}second")
async def analyze_emotion_report(
    request: Request,
    body: AnalyzeEmotionReportRequest,
    _: bool = Depends(verify_api_key)
):
    """
    Analyze emotion detection report using AI
    
    Provides:
    - Comprehensive analysis of emotional patterns
    - Key insights (sentiment, confidence, stress, engagement)
    - Actionable recommendations
    
    Useful for analyzing interview sessions from the emotion detection API.
    """
    request_id = request.state.request_id
    
    logger.info(
        "analyze_emotion_report_request",
        request_id=request_id,
        total_frames=sum(body.emotion_counts.values()),
        duration=body.duration_seconds
    )
    
    try:
        analysis, insights, recommendations, model_used = await gemini_service.analyze_emotion_report(
            emotion_counts=body.emotion_counts,
            duration_seconds=body.duration_seconds,
            dominant_emotions=body.dominant_emotions,
            context=body.context
        )
        
        return AnalyzeEmotionReportResponse(
            analysis=analysis,
            insights=insights,
            recommendations=recommendations,
            request_id=request_id
        )
        
    except Exception as e:
        logger.error("analyze_emotion_report_error", request_id=request_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
