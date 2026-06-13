"""
Delivery simulator for Xeno channel service.

Simulates the real-world lifecycle of a branded message:
  sent → delivered (or failed) → opened → clicked

Each stage has channel-specific probability profiles based on
industry benchmarks for WhatsApp, SMS, and Email.

The _post_event method uses a retry loop (3 attempts, exponential backoff)
to handle transient failures reaching the CRM receipt endpoint.
In production this would be a message queue with dead-letter handling.
"""

import asyncio
import logging
import random
from datetime import datetime

import httpx


logger = logging.getLogger(__name__)
CALLBACK_ATTEMPTS = 8
CALLBACK_TIMEOUT_SECONDS = 15.0
CALLBACK_CONCURRENCY = 8

CHANNEL_CONFIG = {
    "whatsapp": {
        "failure": 0.03,
        "open": 0.55,
        "click": 0.32,
        "read_rate": 0.70,
        "delivery_delay": (0.5, 2.0),
        "open_delay": (2.0, 6.0),
        "click_delay": (1.0, 3.0),
    },
    "sms": {
        "failure": 0.08,
        "open": 0.35,
        "click": 0.18,
        "read_rate": 0.0,
        "delivery_delay": (1.0, 4.0),
        "open_delay": (5.0, 12.0),
        "click_delay": (2.0, 5.0),
    },
    "email": {
        "failure": 0.05,
        "open": 0.25,
        "click": 0.22,
        "read_rate": 0.0,
        "delivery_delay": (0.3, 1.0),
        "open_delay": (10.0, 30.0),
        "click_delay": (3.0, 8.0),
    },
}


class DeliverySimulator:
    def __init__(self, crm_receipt_url: str, crm_base_url: str):
        self.crm_url = crm_receipt_url
        self.crm_base_url = crm_base_url.rstrip("/")
        self.total_simulated = 0
        self.total_callbacks_sent = 0
        self.total_callbacks_failed = 0
        self._callback_semaphore = asyncio.Semaphore(CALLBACK_CONCURRENCY)

    async def _post_event(self, message_id: str, event: str) -> None:
        """POST a delivery event to the CRM receipt endpoint.

        Retries with exponential backoff on connection errors and server errors.
        After 3 failures, logs and continues — the simulation does not stop.
        """
        payload = {
            "message_id": message_id,
            "event": event,
            "timestamp": datetime.utcnow().isoformat(),
        }
        for attempt in range(CALLBACK_ATTEMPTS):
            try:
                async with self._callback_semaphore:
                    async with httpx.AsyncClient(timeout=CALLBACK_TIMEOUT_SECONDS) as client:
                        response = await client.post(self.crm_url, json=payload)
                if 200 <= response.status_code < 300:
                    self.total_callbacks_sent += 1
                    return
                logger.warning(
                    "Receipt endpoint returned %s for %s/%s, attempt %s/%s",
                    response.status_code,
                    message_id,
                    event,
                    attempt + 1,
                    CALLBACK_ATTEMPTS,
                )
                if response.status_code in {400, 404, 422}:
                    break
            except Exception as exc:
                logger.warning(
                    "Callback failed for %s/%s attempt %s/%s: %s",
                    message_id,
                    event,
                    attempt + 1,
                    CALLBACK_ATTEMPTS,
                    exc,
                )
            if attempt < CALLBACK_ATTEMPTS - 1:
                await asyncio.sleep(min(20.0, 1.0 * (2**attempt)) + random.uniform(0, 0.5))
        self.total_callbacks_failed += 1
        logger.error("All retry attempts failed for %s/%s", message_id, event)

    async def _post_attribution(self, customer_id: str, campaign_id: str) -> None:
        order_amount = round(random.uniform(500, 4000), 2)
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(
                    f"{self.crm_base_url}/customers/{customer_id}/order-attributed",
                    json={"campaign_id": campaign_id, "order_amount": order_amount},
                )
        except Exception as exc:
            logger.warning("Attribution call failed: %s", exc)

    async def simulate(
        self,
        message_id: str,
        channel: str,
        customer_id: str,
        campaign_id: str,
    ) -> None:
        self.total_simulated += 1
        cfg = CHANNEL_CONFIG.get(channel, CHANNEL_CONFIG["whatsapp"])
        jitter = lambda: random.uniform(0.8, 1.2)

        await self._post_event(message_id, "sent")

        await asyncio.sleep(random.uniform(*cfg["delivery_delay"]) * jitter())
        if random.random() < cfg["failure"]:
            await self._post_event(message_id, "failed")
            return
        await self._post_event(message_id, "delivered")

        await asyncio.sleep(random.uniform(1.0, 3.0) * jitter())
        if cfg.get("read_rate", 0) > 0 and random.random() < cfg["read_rate"]:
            await self._post_event(message_id, "read")

        await asyncio.sleep(random.uniform(*cfg["open_delay"]) * jitter())
        if random.random() < cfg["open"]:
            await self._post_event(message_id, "opened")
            await asyncio.sleep(random.uniform(*cfg["click_delay"]) * jitter())
            if random.random() < cfg["click"]:
                await self._post_event(message_id, "clicked")
                await asyncio.sleep(random.uniform(30.0, 120.0))
                if random.random() < 0.25:
                    await self._post_attribution(customer_id, campaign_id)
