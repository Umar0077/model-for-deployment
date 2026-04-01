"""
Google Gemini AI service wrapper with fallback support
"""

import json
import asyncio
from typing import Dict, Any, Optional
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions

from app.config import settings
from app.utils.logger import get_logger
from app.utils.retry import async_retry

logger = get_logger(__name__)


class GeminiService:
    """Service for interacting with Google Gemini AI with model fallback"""
    
    def __init__(self):
        """Initialize Gemini service"""
        genai.configure(api_key=settings.gemini_api_key)
        self.primary_model_id = settings.gemini_model_id
        self.fallback_model_id = settings.gemini_fallback_model_id
        self.timeout = settings.gemini_timeout
        self.max_retries = settings.gemini_max_retries
        
        logger.info(
            "gemini_service_initialized",
            primary_model=self.primary_model_id,
            fallback_model=self.fallback_model_id
        )
    
    def _get_model(self, model_id: str, **generation_config):
        """Get configured Gemini model instance"""
        return genai.GenerativeModel(
            model_name=model_id,
            generation_config=generation_config
        )
    
    async def _generate_with_fallback(
        self,
        prompt: str,
        **generation_config
    ) -> tuple[str, str]:
        """
        Internal method to generate content with automatic fallback
        
        Args:
            prompt: The prompt to send to the model
            **generation_config: Generation configuration parameters
            
        Returns:
            Tuple of (generated_text, model_id_used)
            
        Raises:
            Exception: If both primary and fallback models fail
        """
        last_exception = None
        
        # Try primary model first
        try:
            logger.info("attempting_primary_model", model=self.primary_model_id)
            model = self._get_model(self.primary_model_id, **generation_config)
            response = await asyncio.to_thread(model.generate_content, prompt)
            
            logger.info(
                "primary_model_success",
                model=self.primary_model_id,
                response_length=len(response.text)
            )
            return response.text, self.primary_model_id
            
        except Exception as e:
            last_exception = e
            error_msg = str(e).lower()
            
            # Check if this is a model not found error
            is_model_not_found = any(phrase in error_msg for phrase in [
                "model not found",
                "not found",
                "invalid model",
                "unknown model",
                "does not exist"
            ])
            
            if is_model_not_found:
                logger.warning(
                    "primary_model_not_found",
                    model=self.primary_model_id,
                    error=str(e),
                    attempting_fallback=True
                )
                
                # Try fallback model
                try:
                    logger.info("attempting_fallback_model", model=self.fallback_model_id)
                    fallback_model = self._get_model(self.fallback_model_id, **generation_config)
                    response = await asyncio.to_thread(fallback_model.generate_content, prompt)
                    
                    logger.info(
                        "fallback_model_success",
                        model=self.fallback_model_id,
                        response_length=len(response.text)
                    )
                    return response.text, self.fallback_model_id
                    
                except Exception as fallback_error:
                    logger.error(
                        "fallback_model_failed",
                        model=self.fallback_model_id,
                        error=str(fallback_error)
                    )
                    raise Exception(
                        f"Both primary model ({self.primary_model_id}) and fallback model "
                        f"({self.fallback_model_id}) failed. "
                        f"Primary error: {str(e)}. Fallback error: {str(fallback_error)}"
                    )
            else:
                # Not a model not found error, raise original exception
                logger.error("primary_model_error", model=self.primary_model_id, error=str(e))
                raise
        
        # Should not reach here, but just in case
        if last_exception:
            raise last_exception
    
    @async_retry(
        max_attempts=settings.gemini_max_retries,
        initial_delay=1.0,
        backoff_factor=2.0,
        exceptions=(Exception,)
    )
    async def generate_text(
        self,
        message: str,
        system_prompt: Optional[str] = None,
        context: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024
    ) -> tuple[str, str]:
        """
        Generate text response from user message
        
        Args:
            message: User message/prompt
            system_prompt: System prompt to set context
            context: Additional context information
            temperature: Sampling temperature (0.0 to 2.0)
            max_tokens: Maximum tokens to generate
            
        Returns:
            Tuple of (generated_text, model_id_used)
        """
        logger.info(
            "generate_text_start",
            message_length=len(message),
            has_system_prompt=system_prompt is not None,
            has_context=context is not None
        )
        
        # Build complete prompt
        full_prompt = ""
        if system_prompt:
            full_prompt += f"System: {system_prompt}\n\n"
        if context:
            full_prompt += f"Context: {context}\n\n"
        full_prompt += f"User: {message}"
        
        try:
            result, model_used = await self._generate_with_fallback(
                prompt=full_prompt,
                temperature=temperature,
                max_output_tokens=max_tokens
            )
            
            logger.info(
                "generate_text_success",
                response_length=len(result),
                model_used=model_used
            )
            
            return result, model_used
            
        except Exception as e:
            logger.error("generate_text_error", error=str(e))
            raise
    
    async def summarize(
        self,
        text: str,
        max_length: int = 200,
        style: str = "concise"
    ) -> tuple[str, str]:
        """
        Summarize text
        
        Args:
            text: Text to summarize
            max_length: Maximum length of summary
            style: Summary style (concise, detailed, bullet-points)
            
        Returns:
            Tuple of (summary_text, model_id_used)
        """
        logger.info("summarize_start", text_length=len(text), max_length=max_length, style=style)
        
        style_instructions = {
            "concise": "Provide a concise summary",
            "detailed": "Provide a detailed summary with key points",
            "bullet-points": "Summarize in bullet points"
        }
        
        instruction = style_instructions.get(style, style_instructions["concise"])
        
        prompt = f"""{instruction} of the following text in approximately {max_length} words:

{text}

Summary:"""
        
        try:
            summary, model_used = await self._generate_with_fallback(
                prompt=prompt,
                temperature=0.5,
                max_output_tokens=max_length * 2
            )
            
            summary = summary.strip()
            
            logger.info("summarize_success", summary_length=len(summary), model_used=model_used)
            return summary, model_used
            
        except Exception as e:
            logger.error("summarize_error", error=str(e))
            raise
    
    async def extract_json(
        self,
        text: str,
        schema: Dict[str, Any],
        instructions: Optional[str] = None
    ) -> tuple[Dict[str, Any], str, str]:
        """
        Extract structured JSON from text using schema
        
        Args:
            text: Text to extract information from
            schema: JSON schema describing expected structure
            instructions: Additional extraction instructions
            
        Returns:
            Tuple of (extracted_data, raw_model_response, model_id_used)
        """
        logger.info("extract_json_start", text_length=len(text), schema_keys=list(schema.keys()))
        
        schema_str = json.dumps(schema, indent=2)
        
        prompt = f"""Extract information from the following text and return it as valid JSON.

Schema (expected structure):
{schema_str}

{"Additional instructions: " + instructions if instructions else ""}

Text:
{text}

Return ONLY valid JSON matching the schema. Do not include any explanatory text, just the JSON object."""
        
        try:
            raw_text, model_used = await self._generate_with_fallback(
                prompt=prompt,
                temperature=0.3,
                max_output_tokens=2048
            )
            
            # Try to parse JSON from response
            # Remove markdown code blocks if present
            json_text = raw_text
            if "```json" in json_text:
                json_text = json_text.split("```json")[1].split("```")[0].strip()
            elif "```" in json_text:
                json_text = json_text.split("```")[1].split("```")[0].strip()
            
            try:
                data = json.loads(json_text)
            except json.JSONDecodeError:
                # Try to find JSON in the response
                import re
                json_match = re.search(r'\{.*\}', json_text, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group(0))
                else:
                    raise ValueError("Could not parse JSON from model response")
            
            logger.info("extract_json_success", extracted_keys=list(data.keys()), model_used=model_used)
            return data, raw_text, model_used
            
        except Exception as e:
            logger.error("extract_json_error", error=str(e))
            raise
    
    async def analyze_emotion_report(
        self,
        emotion_counts: Dict[str, int],
        duration_seconds: float,
        dominant_emotions: list[Dict[str, Any]],
        context: Optional[str] = None
    ) -> tuple[str, Dict[str, Any], list[str], str]:
        """
        Analyze emotion detection report and provide insights
        
        Args:
            emotion_counts: Dictionary of emotion labels to counts
            duration_seconds: Duration of the session
            dominant_emotions: List of dominant emotions with percentages
            context: Additional context about the interview/session
            
        Returns:
            Tuple of (analysis_text, insights_dict, recommendations_list, model_id_used)
        """
        logger.info(
            "analyze_emotion_report_start",
            total_frames=sum(emotion_counts.values()),
            duration=duration_seconds
        )
        
        total_frames = sum(emotion_counts.values())
        emotion_distribution = {
            emotion: f"{(count/total_frames)*100:.1f}%"
            for emotion, count in emotion_counts.items()
        }
        
        prompt = f"""Analyze this emotion detection report from {"an interview" if context else "a session"}:

Duration: {duration_seconds:.1f} seconds
Total frames analyzed: {total_frames}

Emotion Distribution:
{json.dumps(emotion_distribution, indent=2)}

Dominant Emotions:
{json.dumps(dominant_emotions, indent=2)}

{f"Context: {context}" if context else ""}

Provide:
1. A comprehensive analysis of the emotional patterns
2. Key insights about the person's emotional state
3. Specific recommendations based on the patterns observed

Return your response in this JSON format:
{{
  "analysis": "detailed analysis text",
  "insights": {{
    "overall_sentiment": "positive/neutral/negative",
    "confidence_level": "high/medium/low",
    "stress_indicators": "high/medium/low",
    "authenticity": "high/medium/low",
    "engagement": "high/medium/low"
  }},
  "recommendations": ["recommendation 1", "recommendation 2", ...]
}}"""
        
        try:
            raw_text, model_used = await self._generate_with_fallback(
                prompt=prompt,
                temperature=0.5,
                max_output_tokens=2048
            )
            
            # Parse JSON response
            if "```json" in raw_text:
                json_text = raw_text.split("```json")[1].split("```")[0].strip()
            elif "```" in raw_text:
                json_text = raw_text.split("```")[1].split("```")[0].strip()
            else:
                json_text = raw_text
            
            result = json.loads(json_text)
            
            analysis = result.get("analysis", "")
            insights = result.get("insights", {})
            recommendations = result.get("recommendations", [])
            
            logger.info("analyze_emotion_report_success", model_used=model_used)
            return analysis, insights, recommendations, model_used
            
        except Exception as e:
            logger.error("analyze_emotion_report_error", error=str(e))
            raise


# Global service instance
gemini_service = GeminiService()
