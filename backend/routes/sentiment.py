from fastapi import APIRouter, UploadFile, File

from backend.models import TextQueryRequest
from backend.services.sentiment import analyze_sentiment_from_text, analyze_sentiment_deepgram

router = APIRouter(prefix="/api/sentiment", tags=["sentiment"])


@router.post("/analyze")
async def analyze_sentiment_endpoint(audio: UploadFile = File(...)):
    audio_data = await audio.read()
    result = await analyze_sentiment_deepgram(audio_data)
    return result.model_dump()


@router.post("/text")
async def analyze_text_sentiment(request: TextQueryRequest):
    result = analyze_sentiment_from_text(request.message)
    return result.model_dump()
