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


simulator = DeliverySimulator(crm_receipt_url=settings.crm_receipt_url)
app = FastAPI(title="Xeno Channel Service")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "xeno-channel-service"}


@app.post("/send")
async def send(req: SendRequest) -> dict[str, str]:
    asyncio.create_task(simulator.simulate(req.message_id, req.channel))
    return {"status": "queued", "message_id": req.message_id}


@app.post("/send-batch")
async def send_batch(requests: list[SendRequest]) -> dict[str, object]:
    truncated_requests = requests[:1000]
    channel_counts = Counter(req.channel for req in truncated_requests)
    for req in truncated_requests:
        asyncio.create_task(simulator.simulate(req.message_id, req.channel))
    return {
        "queued": len(truncated_requests),
        "channel_breakdown": dict(channel_counts),
    }
