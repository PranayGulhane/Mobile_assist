import httpx

from backend.config import get_deepgram_config


async def transcribe_audio_deepgram(audio_data: bytes) -> str:
    config = get_deepgram_config()

    if not config.is_configured:
        return ""

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{config.listen_url}?model=nova-2&language=en",
                headers={
                    "Authorization": f"Token {config.api_key}",
                    "Content-Type": "audio/wav",
                },
                content=audio_data,
                timeout=config.timeout,
            )

            if response.status_code == 200:
                result = response.json()
                return _extract_transcript(result)

            return ""
    except Exception:
        return ""


def _extract_transcript(result: dict) -> str:
    channels = result.get("results", {}).get("channels", [])
    if channels:
        alternatives = channels[0].get("alternatives", [])
        if alternatives:
            return alternatives[0].get("transcript", "")
    return ""
