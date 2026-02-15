from fastapi import APIRouter

from backend.config import get_deepgram_config, get_trello_config

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
async def health_check():
    deepgram = get_deepgram_config()
    trello = get_trello_config()

    return {
        "status": "ok",
        "service": "Assist Link API",
        "integrations": {
            "deepgram": "configured" if deepgram.is_configured else "not configured",
            "trello": "configured" if trello.is_configured else "not configured",
        },
    }
