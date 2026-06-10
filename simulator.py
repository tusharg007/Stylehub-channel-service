import asyncio
import logging
import random
from datetime import datetime

import httpx


logger = logging.getLogger(__name__)

CHANNEL_CONFIG = {
    "whatsapp": {
        "failure": 0.03,
        "open": 0.55,
        "click": 0.32,
        "delivery_delay": (0.5, 2.0),
        "open_delay": (2.0, 6.0),
        "click_delay": (1.0, 3.0),
    },
    "sms": {
        "failure": 0.08,
        "open": 0.35,
        "click": 0.18,
        "delivery_delay": (1.0, 4.0),
        "open_delay": (5.0, 12.0),
        "click_delay": (2.0, 5.0),
    },
    "email": {
        "failure": 0.05,
        "open": 0.25,
        "click": 0.22,
        "delivery_delay": (0.3, 1.0),
        "open_delay": (10.0, 30.0),
        "click_delay": (3.0, 8.0),
    },
}


class DeliverySimulator:
    def __init__(self, crm_receipt_url: str):
        self.crm_url = crm_receipt_url

    async def _post_event(self, message_id: str, event: str) -> None:
        payload = {
            "message_id": message_id,
            "event": event,
            "timestamp": datetime.utcnow().isoformat(),
        }
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(self.crm_url, json=payload)
        except Exception as exc:
            logger.warning("Callback failed for %s event=%s: %s", message_id, event, exc)

    async def simulate(self, message_id: str, channel: str) -> None:
        cfg = CHANNEL_CONFIG.get(channel, CHANNEL_CONFIG["whatsapp"])
        jitter = lambda: random.uniform(0.8, 1.2)

        await self._post_event(message_id, "sent")

        await asyncio.sleep(random.uniform(*cfg["delivery_delay"]) * jitter())
        if random.random() < cfg["failure"]:
            await self._post_event(message_id, "failed")
            return
        await self._post_event(message_id, "delivered")

        await asyncio.sleep(random.uniform(*cfg["open_delay"]) * jitter())
        if random.random() < cfg["open"]:
            await self._post_event(message_id, "opened")
            await asyncio.sleep(random.uniform(*cfg["click_delay"]) * jitter())
            if random.random() < cfg["click"]:
                await self._post_event(message_id, "clicked")
