import logging
from datetime import datetime
from typing import Optional

import httpx

from backend.config import get_trello_config

logger = logging.getLogger(__name__)


async def create_trello_ticket(
    title: str,
    description: str,
    labels: Optional[list[str]] = None,
) -> Optional[str]:
    config = get_trello_config()

    if not config.is_configured:
        logger.warning(
            "Trello not configured - missing API key, token, or list ID. "
            "Generating local ticket ID."
        )
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

            logger.info(f"Creating Trello card: '{title}' on list {config.list_id}")

            response = await client.post(
                config.cards_url,
                params=params,
                timeout=config.timeout,
            )

            if response.status_code in (200, 201):
                card = response.json()
                card_id = card.get("id", _generate_local_ticket_id())
                card_url = card.get("shortUrl", "N/A")
                logger.info(f"Trello card created: id={card_id}, url={card_url}")
                return card_id

            logger.error(
                f"Trello API error: status={response.status_code}, "
                f"body={response.text[:500]}"
            )
            return _generate_local_ticket_id()

    except Exception as e:
        logger.error(f"Trello ticket creation failed: {e}")
        return _generate_local_ticket_id()


def _generate_local_ticket_id() -> str:
    return f"LOCAL-{datetime.now().strftime('%Y%m%d%H%M%S')}"
