from datetime import datetime
from typing import Optional

import httpx

from backend.config import get_trello_config


async def create_trello_ticket(
    title: str,
    description: str,
    labels: Optional[list[str]] = None,
) -> Optional[str]:
    config = get_trello_config()

    if not config.is_configured:
        return _generate_local_ticket_id()

    try:
        async with httpx.AsyncClient() as client:
            params = {
                "key": config.api_key,
                "token": config.token,
                "idList": config.list_id,
                "name": title,
                "desc": description,
            }

            response = await client.post(
                config.cards_url,
                params=params,
                timeout=config.timeout,
            )

            if response.status_code == 200:
                card = response.json()
                return card.get("id", _generate_local_ticket_id())

            return _generate_local_ticket_id()

    except Exception:
        return _generate_local_ticket_id()


def _generate_local_ticket_id() -> str:
    return f"LOCAL-{datetime.now().strftime('%Y%m%d%H%M%S')}"
