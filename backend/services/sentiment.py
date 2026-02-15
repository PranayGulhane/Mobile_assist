import logging

import httpx

from backend.config import get_deepgram_config
from backend.models import SentimentResult

logger = logging.getLogger(__name__)

NEGATIVE_WORDS = [
    "angry", "frustrated", "annoyed", "terrible", "horrible", "worst",
    "hate", "ridiculous", "unacceptable", "disgusting", "furious",
    "outraged", "stupid", "useless", "pathetic", "scam", "fraud",
    "steal", "cheat", "liar", "incompetent", "waste", "awful",
    "disappointed", "disappointing", "upset", "unfair", "unbelievable",
]

STRONG_NEGATIVE_WORDS = [
    "furious", "outraged", "scam", "fraud", "steal",
    "cheat", "liar", "pathetic", "disgusting",
]

FRUSTRATION_PHRASES = [
    "why don't you", "why can't you", "why won't you",
    "don't want to go", "don't want to check",
    "don't want to call", "don't want to go anywhere",
    "i don't want to", "should have", "should already",
    "not helpful", "not useful", "no help", "can't believe",
    "what's the point", "what good is", "waste of time",
    "makes no sense", "doesn't make sense", "doesn't help",
    "why should i", "you should have", "you should know",
    "this is not", "that's not", "what kind of",
    "i shouldn't have to", "why do i have to",
    "go somewhere else", "go anywhere else", "check somewhere else",
    "not good enough", "don't have my",
]


def analyze_sentiment_from_text(message: str) -> SentimentResult:
    message_lower = message.lower()

    negative_count = sum(1 for word in NEGATIVE_WORDS if word in message_lower)
    strong_negative_count = sum(1 for word in STRONG_NEGATIVE_WORDS if word in message_lower)
    frustration_count = sum(1 for phrase in FRUSTRATION_PHRASES if phrase in message_lower)

    if strong_negative_count > 0 or negative_count >= 3 or frustration_count >= 2:
        return SentimentResult(
            sentiment="negative",
            confidence=0.95,
            details="High dissatisfaction detected. Customer shows strong negative emotions.",
        )
    elif frustration_count >= 1 or negative_count >= 1:
        return SentimentResult(
            sentiment="negative",
            confidence=0.8,
            details="Frustration or dissatisfaction detected in customer message.",
        )
    else:
        return SentimentResult(
            sentiment="positive",
            confidence=0.8,
            details="Customer appears calm and engaged.",
        )


async def analyze_sentiment_deepgram(audio_data: bytes) -> SentimentResult:
    config = get_deepgram_config()

    if not config.is_configured:
        logger.warning("Deepgram API key not configured - audio sentiment analysis unavailable")
        return SentimentResult(
            sentiment="neutral",
            confidence=0.5,
            details="Sentiment analysis unavailable - Deepgram API key not configured",
        )

    try:
        url = f"{config.listen_url}?sentiment=true&language=en"
        logger.info(
            f"Calling Deepgram Audio Intelligence API for sentiment analysis: "
            f"audio_size={len(audio_data)} bytes, url={url}"
        )

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers={
                    "Authorization": f"Token {config.api_key}",
                    "Content-Type": "audio/wav",
                },
                content=audio_data,
                timeout=config.timeout,
            )

            if response.status_code != 200:
                logger.error(
                    f"Deepgram Audio Intelligence API error: "
                    f"status={response.status_code}, body={response.text[:500]}"
                )
                return SentimentResult(
                    sentiment="neutral",
                    confidence=0.5,
                    details=f"Deepgram API returned status {response.status_code}",
                )

            result = response.json()
            sentiments = _extract_sentiments(result)

            logger.info(
                f"Deepgram Audio Intelligence sentiment segments: {sentiments}"
            )

            if not sentiments:
                logger.info("No sentiment segments found in audio response")
                return SentimentResult(
                    sentiment="neutral",
                    confidence=0.6,
                    details="No sentiment segments detected in audio",
                )

            aggregated = _aggregate_sentiments(sentiments)
            logger.info(
                f"Aggregated audio sentiment: {aggregated.sentiment} "
                f"(confidence={aggregated.confidence:.0%})"
            )
            return aggregated

    except Exception as e:
        logger.error(f"Deepgram Audio Intelligence sentiment error: {e}")
        return SentimentResult(
            sentiment="neutral",
            confidence=0.5,
            details=f"Sentiment analysis error: {str(e)}",
        )


def _extract_sentiments(result: dict) -> list[str]:
    sentiments = []

    sentiment_data = result.get("results", {}).get("sentiments", {})
    segments = sentiment_data.get("segments", [])
    for segment in segments:
        sent = segment.get("sentiment", "neutral")
        sentiments.append(sent)

    if not sentiments:
        average = sentiment_data.get("average", {})
        avg_sent = average.get("sentiment")
        if avg_sent and avg_sent != "neutral":
            sentiments.append(avg_sent)

    return sentiments


def _aggregate_sentiments(sentiments: list[str]) -> SentimentResult:
    neg_count = sentiments.count("negative")
    pos_count = sentiments.count("positive")
    total = len(sentiments)

    if neg_count / total > 0.5:
        return SentimentResult(
            sentiment="negative",
            confidence=neg_count / total,
            details=f"Deepgram Audio Intelligence: negative sentiment in {neg_count}/{total} segments",
        )
    elif pos_count / total > 0.5:
        return SentimentResult(
            sentiment="positive",
            confidence=pos_count / total,
            details=f"Deepgram Audio Intelligence: positive sentiment in {pos_count}/{total} segments",
        )

    return SentimentResult(
        sentiment="neutral",
        confidence=0.6,
        details=f"Deepgram Audio Intelligence: mixed/neutral sentiment ({neg_count} neg, {pos_count} pos out of {total} segments)",
    )
