# Messaging Channel Service

Stateless FastAPI microservice that simulates message delivery for WhatsApp, SMS, and email. In the full analytics project, this service acts like an external communication provider: it receives queued campaign messages, simulates delivery states, and posts callbacks back to the analytics backend.

This service is useful for demonstrating webhook-style event ingestion, delivery funnel analytics, and attribution tracking without sending real messages to real users.

## Role In The Architecture

```text
Campaign launch
  -> backend creates message records
  -> channel service queues simulations
  -> sent / delivered / read / opened / clicked / failed callbacks
  -> backend receipt endpoint updates analytics
  -> campaign dashboards and AI insights refresh
```

## Run Locally

Install dependencies:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

Copy the environment example:

```powershell
copy .env.example .env
```

Start the service on port `8001`:

```powershell
uvicorn main:app --port 8001 --reload
```

Health check:

```text
http://localhost:8001/health
```

Status endpoint:

```text
http://localhost:8001/status
```

## Configuration

Local `.env` example:

```env
CRM_RECEIPT_URL=http://localhost:8000/receipt
CRM_BASE_URL=http://localhost:8000
PORT=8001
```

`CRM_RECEIPT_URL` receives lifecycle callbacks. `CRM_BASE_URL` is used for simulated attribution events such as order-attributed callbacks.

## Callback Lifecycle

For each message, the simulator follows this lifecycle:

```text
queued -> sent -> delivered OR failed -> read -> opened -> clicked -> optional attribution
```

Details:

- `sent` is posted immediately.
- `delivered` or `failed` is posted after a channel-specific delay.
- `read` may happen for WhatsApp-style messages.
- `opened` may happen after delivery, based on channel open probability.
- `clicked` may happen after open, based on channel click probability.
- Attribution may be posted after a click to simulate a conversion.

Failures are terminal. If the backend is temporarily unavailable, the service retries callbacks with exponential backoff and keeps running.

## Endpoints

### `GET /health`

Returns:

```json
{"status": "ok", "service": "xeno-channel-service"}
```

### `GET /status`

Returns simulation observability counters:

```json
{
  "status": "ok",
  "service": "xeno-channel-service",
  "stats": {
    "total_simulated": 0,
    "callbacks_sent": 0,
    "callbacks_failed": 0,
    "success_rate": 100.0
  }
}
```

### `POST /send`

Queues one message for delivery simulation.

### `POST /send-batch`

Queues up to `1000` messages for delivery simulation and returns a per-channel breakdown.
