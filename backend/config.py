import os
from dataclasses import dataclass


@dataclass
class DeepgramConfig:
    api_key: str
    base_url: str = "https://api.deepgram.com/v1"
    listen_endpoint: str = "/listen"
    timeout: float = 30.0

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    @property
    def listen_url(self) -> str:
        return f"{self.base_url}{self.listen_endpoint}"


@dataclass
class TrelloConfig:
    api_key: str
    token: str
    list_id: str
    list_id_done: str
    base_url: str = "https://api.trello.com/1"
    timeout: float = 15.0

    @property
    def is_configured(self) -> bool:
        return all([self.api_key, self.token, self.list_id])

    @property
    def cards_url(self) -> str:
        return f"{self.base_url}/cards"


@dataclass
class AppSettings:
    host: str = "0.0.0.0"
    port: int = 8001
    app_title: str = "Assist Link API"
    cors_origins: list[str] = None

    def __post_init__(self):
        if self.cors_origins is None:
            self.cors_origins = ["*"]


def get_deepgram_config() -> DeepgramConfig:
    return DeepgramConfig(
        api_key=os.environ.get("DEEPGRAM_API_KEY", ""),
    )


def get_trello_config() -> TrelloConfig:
    return TrelloConfig(
        api_key=os.environ.get("TRELLO_API_KEY", ""),
        token=os.environ.get("TRELLO_TOKEN", ""),
        list_id=os.environ.get("TRELLO_LIST_ID", ""),
        list_id_done=os.environ.get("TRELLO_LIST_ID_DONE", ""),
    )


def get_app_settings() -> AppSettings:
    return AppSettings(
        port=int(os.environ.get("FASTAPI_PORT", "8001")),
    )
