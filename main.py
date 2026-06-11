"""
Xeno channel service — stubbed message delivery simulation.

Exposes two send endpoints:
  POST /send       — single message (fire and forget)
  POST /send-batch — up to 1000 messages (chunks, parallel)

Each received message is simulated asynchronously via asyncio.create_task.
The simulation fires callbacks to CRM_RECEIPT_URL as the message progresses
through its delivery lifecycle: sent → delivered → opened → clicked (or failed).

This service is intentionally stateless — no database, no persistence.
All simulation state lives in the asyncio event loop.
"""

import asyncio
import logging
from collections import Counter

from fastapi import FastAPI
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

from simulator import DeliverySimulator


logging.basicConfig(level=logging.INFO)


class Settings(BaseSettings):
    crm_receipt_url: str = "http://localhost:8000/receipt"
    crm_base_url: str = "http://localhost:8000"
    port: int = 8001

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()


class SendRequest(BaseModel):
    message_id: str
    campaign_id: str
    customer_id: str
    phone: str
    message: str
    channel: str


simulator = DeliverySimulator(
    crm_receipt_url=settings.crm_receipt_url,
    crm_base_url=settings.crm_base_url,
)
app = FastAPI(title="Xeno Channel Service")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "xeno-channel-service"}


@app.get("/status")
async def status() -> dict[str, object]:
    """Observability endpoint — shows simulation statistics.

    Useful for verifying the channel service is processing messages
    and callbacks are reaching the CRM during demos and debugging.
    """
    return {
        "status": "ok",
        "service": "xeno-channel-service",
        "stats": {
            "total_simulated": simulator.total_simulated,
            "callbacks_sent": simulator.total_callbacks_sent,
            "callbacks_failed": simulator.total_callbacks_failed,
            "success_rate": (
                round(
                    simulator.total_callbacks_sent
                    / max(
                        simulator.total_callbacks_sent
                        + simulator.total_callbacks_failed,
                        1,
                    )
                    * 100,
                    1,
                )
            ),
        },
    }


@app.post("/send")
async def send(req: SendRequest) -> dict[str, str]:
    asyncio.create_task(
        simulator.simulate(req.message_id, req.channel, req.customer_id, req.campaign_id)
    )
    return {"status": "queued", "message_id": req.message_id}


@app.post("/send-batch")
async def send_batch(requests: list[SendRequest]) -> dict[str, object]:
    truncated_requests = requests[:1000]
    channel_counts = Counter(req.channel for req in truncated_requests)
    for req in truncated_requests:
        asyncio.create_task(
            simulator.simulate(req.message_id, req.channel, req.customer_id, req.campaign_id)
        )
    return {
        "queued": len(truncated_requests),
        "channel_breakdown": dict(channel_counts),
    }
