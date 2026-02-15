import httpx

from backend.config import get_deepgram_config
from backend.models import SentimentResult

NEGATIVE_WORDS = [
    "angry", "frustrated", "annoyed", "terrible", "horrible", "worst",
    "hate", "ridiculous", "unacceptable", "disgusting", "furious",
    "outraged", "stupid", "useless", "pathetic", "scam", "fraud",
    "steal", "cheat", "liar", "incompetent", "never", "nothing", "waste",
]

STRONG_NEGATIVE_WORDS = [
    "furious", "outraged", "scam", "fraud", "steal",
    "cheat", "liar", "pathetic", "disgusting",
]


def analyze_sentiment_from_text(message: str) -> SentimentResult:
    message_lower = message.lower()

    negative_count = sum(1 for word in NEGATIVE_WORDS if word in message_lower)
    strong_negative_count = sum(1 for word in STRONG_NEGATIVE_WORDS if word in message_lower)

    if strong_negative_count > 0 or negative_count >= 3:
        return SentimentResult(
            sentiment="negative",
            confidence=0.95,
            details="High dissatisfaction detected. Customer shows strong negative emotions.",
        )
    elif negative_count >= 1:
        return SentimentResult(
            sentiment="mixed",
            confidence=0.7,
            details="Some frustration detected. Monitoring for escalation.",
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
        return SentimentResult(
            sentiment="neutral",
            confidence=0.5,
            details="Sentiment analysis unavailable - Deepgram API key not configured",
        )

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{config.listen_url}?sentiment=true&language=en",
                headers={
                    "Authorization": f"Token {config.api_key}",
                    "Content-Type": "audio/wav",
                },
                content=audio_data,
                timeout=config.timeout,
            )

            if response.status_code != 200:
                return SentimentResult(
                    sentiment="neutral",
                    confidence=0.5,
                    details=f"Deepgram API returned status {response.status_code}",
                )

            result = response.json()
            sentiments = _extract_sentiments(result)

            if not sentiments:
                return SentimentResult(
                    sentiment="neutral",
                    confidence=0.6,
                    details="Mixed or neutral sentiment detected",
                )

            return _aggregate_sentiments(sentiments)

    except Exception as e:
        return SentimentResult(
            sentiment="neutral",
            confidence=0.5,
            details=f"Sentiment analysis error: {str(e)}",
        )


def _extract_sentiments(result: dict) -> list[str]:
    sentiments = []
    channels = result.get("results", {}).get("channels", [])
    for channel in channels:
        for alt in channel.get("alternatives", []):
            for para in alt.get("paragraphs", {}).get("paragraphs", []):
                for sentence in para.get("sentences", []):
                    sentiments.append(sentence.get("sentiment", "neutral"))
    return sentiments


def _aggregate_sentiments(sentiments: list[str]) -> SentimentResult:
    neg_count = sentiments.count("negative")
    pos_count = sentiments.count("positive")
    total = len(sentiments)

    if neg_count / total > 0.5:
        return SentimentResult(
            sentiment="negative",
            confidence=neg_count / total,
            details=f"Detected negative sentiment in {neg_count}/{total} segments",
        )
    elif pos_count / total > 0.5:
        return SentimentResult(
            sentiment="positive",
            confidence=pos_count / total,
            details=f"Detected positive sentiment in {pos_count}/{total} segments",
        )

    return SentimentResult(
        sentiment="neutral",
        confidence=0.6,
        details="Mixed or neutral sentiment detected",
    )
