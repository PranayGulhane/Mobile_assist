import logging

from fastapi import FastAPI

from backend.config import get_app_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
from backend.routes import (
    conversations_router,
    voice_router,
    sentiment_router,
    health_router,
)


def create_app() -> FastAPI:
    settings = get_app_settings()

    app = FastAPI(title=settings.app_title)

    app.include_router(health_router)
    app.include_router(conversations_router)
    app.include_router(voice_router)
    app.include_router(sentiment_router)

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    settings = get_app_settings()
    uvicorn.run(app, host=settings.host, port=settings.port)
