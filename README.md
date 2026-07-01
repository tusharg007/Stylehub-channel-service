# Channel Service

Stateless FastAPI microservice that simulates WhatsApp, SMS, and email delivery for the Mini CRM backend.

The CRM backend sends queued campaign messages to this service. The channel service immediately starts async delivery simulations and posts receipt callbacks back to the CRM `/receipt` endpoint.

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

```txt
http://localhost:8001/health
```

## Callback Lifecycle

For each message, the simulator follows this lifecycle:

```txt
send -> sent -> delivered OR failed -> opened -> clicked
```

Details:

- `sent` is posted immediately.
- `delivered` or `failed` is posted after a channel-specific delivery delay.
- `opened` may happen after delivery, based on channel open probability.
- `clicked` may happen after open, based on channel click probability.

Failures are terminal. If the CRM backend is unavailable, callback errors are logged and the channel service keeps running.

## Configuration

Set `CRM_RECEIPT_URL` in `.env` to point at the CRM backend receipt endpoint:

```env
CRM_RECEIPT_URL=http://localhost:8000/receipt
PORT=8001
```

When running both repos locally:

- CRM backend: `http://localhost:8000`
- Channel service: `http://localhost:8001`

## Endpoints

### `GET /health`

Returns:

```json
{"status": "ok", "service": "xeno-channel-service"}
```

### `POST /send`

Queues one message for delivery simulation.

### `POST /send-batch`

Queues up to `1000` messages for delivery simulation and returns a per-channel breakdown.
