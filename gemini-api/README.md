# Gemini AI FastAPI Service

A production-ready FastAPI service for integrating Google Gemini AI capabilities into your applications. This service provides endpoints for text generation, summarization, structured data extraction, and emotion analysis.

## Features

✨ **Core Capabilities**
- 🤖 Text generation with customizable parameters
- 📝 Intelligent text summarization
- 📊 Structured JSON data extraction
- 😊 Emotion report analysis (perfect for interview apps)

🛡️ **Production Ready**
- **Model fallback**: Automatically falls back to Gemini 2.5 Flash Lite if primary model unavailable
- Rate limiting with SlowAPI
- Request ID tracking
- Structured logging with structlog
- Automatic retry logic with exponential backoff
- CORS support
- Environment-based configuration
- Comprehensive error handling

🧪 **Developer Friendly**
- Full type hints with Pydantic
- Interactive API docs (Swagger/ReDoc)
- Unit and integration tests
- Clean architecture (routes/services/models)

---

## Prerequisites

- Python 3.8+
- Google Gemini API key ([Get one here](https://makersuite.google.com/app/apikey))

---

## Quick Start

### 1. Installation

```bash
# Clone or navigate to the gemini-api directory
cd gemini-api

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` and add your Gemini API key:

```env
GEMINI_API_KEY=your_actual_api_key_here
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO
```

### 3. Run the Server

```bash
# Option 1: Run directly with Python
python -m app.main

# Option 2: Run with uvicorn (recommended for production)
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

The server will start at `http://localhost:8001`

### 4. Test the API

Open your browser and navigate to:
- **Interactive Docs**: http://localhost:8001/docs
- **ReDoc**: http://localhost:8001/redoc
- **Health Check**: http://localhost:8001/health

---

## API Endpoints

### Health Check

```bash
GET /health
```

Returns service status and configuration info.

### Generate Text

```bash
POST /api/v1/gemini/generate
Content-Type: application/json

{
  "prompt": "Write a creative story about a robot",
  "temperature": 0.7,
  "max_output_tokens": 500
}
```

### Summarize Text

```bash
POST /api/v1/gemini/summarize
Content-Type: application/json

{
  "text": "Long article or document text...",
  "max_length": 100
}
```

### Extract Structured Data

```bash
POST /api/v1/gemini/extract
Content-Type: application/json

{
  "text": "John Smith, age 30, scored 85% on the assessment",
  "schema": "Extract name, age, and score as JSON"
}
```

### Analyze Emotions

```bash
POST /api/v1/gemini/analyze-emotions
Content-Type: application/json

{
  "emotion_data": {
    "happy": 0.6,
    "neutral": 0.3,
    "confident": 0.1
  },
  "context": "Job interview",
  "analysis_type": "detailed"
}
```

---

## Flutter Integration Example

```dart
import 'dart:convert';
import 'package:http/http.dart' as http;

class GeminiService {
  final String baseUrl;
  
  GeminiService({required this.baseUrl});
  
  Future<String> generateText(String prompt) async {
    final response = await http.post(
      Uri.parse('$baseUrl/api/v1/gemini/generate'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'prompt': prompt,
        'temperature': 0.7,
        'max_output_tokens': 500,
      }),
    );
    
    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      return data['text'];
    } else {
      throw Exception('Failed to generate text');
    }
  }
  
  Future<String> analyzeEmotions(Map<String, double> emotionData) async {
    final response = await http.post(
      Uri.parse('$baseUrl/api/v1/gemini/analyze-emotions'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'emotion_data': emotionData,
        'context': 'Interview session',
        'analysis_type': 'detailed',
      }),
    );
    
    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      return data['analysis'];
    } else {
      throw Exception('Failed to analyze emotions');
    }
  }
}

// Usage
final geminiService = GeminiService(baseUrl: 'http://10.19.40.133:8001');
final analysis = await geminiService.analyzeEmotions({
  'happy': 0.65,
  'neutral': 0.25,
  'surprised': 0.10,
});
print(analysis);
```

---

## Configuration Options

All configuration is done via environment variables (`.env` file):

| Variable | Description | Default |
|----------|-------------|---------|
| `GEMINI_API_KEY` | Google Gemini API key | *Required* |
| `GEMINI_MODEL_ID` | Primary model name | `gemini-2.5-flash` |
| `GEMINI_FALLBACK_MODEL_ID` | Fallback model if primary unavailable | `gemini-2.5-flash-lite` |
| `APP_NAME` | Application name | `Gemini AI API` |
| `APP_VERSION` | API version | `1.0.0` |
| `ENVIRONMENT` | Environment (dev/prod) | `development` |
| `DEBUG` | Enable debug mode | `true` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `HOST` | Server host | `0.0.0.0` |
| `PORT` | Server port | `8001` |
| `CORS_ORIGINS` | Allowed CORS origins | `*` |
| `RATE_LIMIT_ENABLED` | Enable rate limiting | `true` |
| `RATE_LIMIT_PER_MINUTE` | Requests per minute | `20` |

---

## Model Fallback Mechanism

The service automatically handles model availability issues:

**Primary Model**: `gemini-2.5-flash` (default)
**Fallback Model**: `gemini-2.5-flash-lite` (automatically used if primary is unavailable)

**How it works:**
1. Service attempts to use the primary model (`GEMINI_MODEL_ID`)
2. If model returns "not found" or "invalid model" error, automatically retries with fallback
3. Logs which model was used for transparency
4. Returns clear error if both models fail

**Example log output:**
```json
{
  "event": "attempting_primary_model",
  "model": "gemini-2.5-flash"
}
{
  "event": "primary_model_not_found",
  "model": "gemini-2.5-flash",
  "attempting_fallback": true
}
{
  "event": "fallback_model_success",
  "model": "gemini-2.5-flash-lite"
}
```

---

## API Key Security & Rotation

### Protecting Your API Key

**Never commit your API key to version control:**
```bash
# Always add .env to .gitignore
echo ".env" >> .gitignore
```

**If your key is accidentally leaked:**

1. **Immediately revoke** the compromised key:
   - Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Delete the compromised API key

2. **Generate a new key**:
   - Create a new API key in Google AI Studio
   - Update your `.env` file with the new key
   - Restart the service

3. **Update all deployments**:
   ```bash
   # Update production environment variable
   # For Docker:
   docker stop gemini-api
   # Update .env or environment variables
   docker start gemini-api
   
   # For cloud deployments (Azure/AWS/GCP):
   # Update environment variables in your cloud console
   ```

4. **Monitor usage** for any unauthorized activity in [Google Cloud Console](https://console.cloud.google.com/)

### Key Rotation Best Practices

- **Rotate keys quarterly** or after team member departures
- **Use different keys** for dev/staging/production environments
- **Set up billing alerts** to detect unusual usage
- **Restrict API key** to specific IP addresses when possible (in Google Cloud Console)

---

## Testing

Run the test suite:

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_gemini_service.py -v
```

---

## Project Structure

```
gemini-api/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI application entry point
│   ├── config.py                  # Configuration management
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── health.py          # Health check endpoints
│   │       └── gemini.py          # Gemini AI endpoints
│   ├── services/
│   │   ├── __init__.py
│   │   └── gemini_service.py      # Gemini API wrapper
│   ├── models/
│   │   ├── __init__.py
│   │   ├── requests.py            # Request schemas
│   │   └── responses.py           # Response schemas
│   ├── middleware/
│   │   ├── __init__.py
│   │   ├── request_id.py          # Request ID middleware
│   │   └── rate_limiter.py        # Rate limiting
│   └── utils/
│       ├── __init__.py
│       ├── logger.py              # Logging configuration
│       └── retry.py               # Retry decorator
├── tests/
│   ├── __init__.py
│   ├── test_gemini_service.py     # Service tests
│   └── test_endpoints.py          # API endpoint tests
├── requirements.txt
├── .env.example
└── README.md
```

---

## Deployment

### Docker Deployment (Recommended)

Create a `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8001

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
```

Build and run:

```bash
docker build -t gemini-api .
docker run -p 8001:8001 --env-file .env gemini-api
```

### Production Considerations

1. **Use a proper ASGI server** (uvicorn with multiple workers):
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8001 --workers 4
   ```

2. **Set DEBUG=false** in production

3. **Configure CORS_ORIGINS** to only allowed domains:
   ```env
   CORS_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
   ```

4. **Enable rate limiting** to prevent abuse

5. **Use environment variables** for sensitive data (never commit `.env`)

6. **Set up monitoring** and logging aggregation

---

## Troubleshooting

### "Invalid API key" error

Verify your `.env` file has the correct API key:
```env
GEMINI_API_KEY=AIzaSy...
```

### Rate limit exceeded

Adjust rate limiting in `.env`:
```env
RATE_LIMIT_PER_MINUTE=50
```

### Connection refused from mobile

Ensure you're using your computer's IP address (not `localhost`):
```dart
baseUrl: 'http://10.19.40.133:8001'  // Use ipconfig/ifconfig to find your IP
```

Also check firewall settings allow connections on port 8001.

---

## Integration with Emotion Detection API

This service is designed to work alongside the emotion detection API. Example workflow:

1. **Emotion Detection API** (port 8000) - Detects emotions from video frames
2. **Gemini AI API** (port 8001) - Analyzes emotion reports and generates insights

```python
# Get emotion data from emotion API
emotion_response = requests.post("http://localhost:8000/predict_frame", ...)
emotion_data = emotion_response.json()

# Analyze with Gemini
gemini_response = requests.post(
    "http://localhost:8001/api/v1/gemini/analyze-emotions",
    json={"emotion_data": emotion_data, "context": "interview"}
)
analysis = gemini_response.json()["analysis"]
```

---

## License

MIT License - feel free to use in your projects!

---

## Support

For issues or questions:
1. Check the interactive docs at `/docs`
2. Review the test files for usage examples
3. Check Google Gemini API documentation

---

## Changelog

### v1.0.0 (2024)
- Initial release
- Text generation endpoint
- Summarization endpoint
- JSON extraction endpoint
- Emotion analysis endpoint
- Rate limiting
- Request tracking
- Comprehensive tests

