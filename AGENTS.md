# AGENTS.md

## What this project is
Stubbed channel service for Xeno CRM. Simulates WhatsApp/SMS/Email delivery.
Receives send requests from the CRM backend, fires async callbacks to CRM /receipt endpoint.

## Stack
- Python 3.11, FastAPI 0.111.0, Pydantic v2, httpx. No database — fully stateless.

## Code rules
- All simulation logic must be async. Never block the event loop.
- Callbacks: always wrap httpx calls in try/except. Failure to reach CRM must never crash service.
- No print(). Use logging module.
- Background tasks via asyncio.create_task(), not FastAPI BackgroundTasks.