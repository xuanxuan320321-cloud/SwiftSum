from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from transformers import pipeline
import os

# Configuration
API_KEY = os.getenv("API_KEY", "your_super_secret_api_key") # Replace with a strong, unique key in production
API_KEY_NAME = "X-API-Key"

api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=True)

def get_api_key(api_key: str = Depends(api_key_header)):
    if api_key == API_KEY:
        return api_key
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API Key")

app = FastAPI(
    title="SwiftSum: Lightweight Text Summarization API",
    description="A high-performance, lightweight text summarization API based on Transformer models.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Load pre-trained summarization model
# Using 'distilbert-base-uncased' for demonstration, consider larger models for better quality
# or smaller ones for faster inference based on your needs.
# Ensure the model is downloaded or available in the Docker image.
summarizer = pipeline("summarization", model="sshleifer/distilbart-cnn-12-6")

class TextToSummarize(BaseModel):
    text: str
    min_length: int = 30
    max_length: int = 150

@app.get("/", tags=["Health Check"])
async def root():
    return {"message": "Welcome to SwiftSum API! Visit /docs for API documentation."}

@app.post("/summarize", tags=["Summarization"], response_model=dict)
async def summarize_text(
    item: TextToSummarize,
    api_key: str = Depends(get_api_key)
):
    """
    Summarize a given text using a pre-trained Transformer model.

    - **text**: The input text to be summarized.
    - **min_length**: Minimum length of the generated summary (default: 30).
    - **max_length**: Maximum length of the generated summary (default: 150).
    - Requires `X-API-Key` header for authentication.
    """
    if not item.text:
        raise HTTPException(status_code=400, detail="Input text cannot be empty")

    try:
        summary = summarizer(
            item.text,
            min_length=item.min_length,
            max_length=item.max_length,
            do_sample=False
        )[0]["summary_text"]
        return {"summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Summarization failed: {str(e)}")

# Rate Limiting (basic example, for production consider a dedicated library like `fastapi-limiter`)
# This is a placeholder and not a full-fledged rate limiter.
request_counts = {}

@app.middleware("http")
async def add_process_time_header(request, call_next):
    # Simple rate limiting: 10 requests per minute per IP
    client_ip = request.client.host
    current_time = int(time.time())

    if client_ip not in request_counts:
        request_counts[client_ip] = []
    
    # Remove old requests (older than 60 seconds)
    request_counts[client_ip] = [t for t in request_counts[client_ip] if current_time - t < 60]

    if len(request_counts[client_ip]) >= 10:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded")
    
    request_counts[client_ip].append(current_time)

    response = await call_next(request)
    return response

import time # Import time for rate limiting example
