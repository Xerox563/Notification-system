# Notification System

An asynchronous notification service for email, SMS and push, built with FastAPI, Postgres and Redis.

The API accepts a request and answers `202` right away. Workers deliver it in the background with retries, rate limits, priorities and provider fallback.

See [FEATURES.md](FEATURES.md) for the feature checklist and [docs/design.md](docs/design.md) for the design, capacity estimate and trade offs.

## Run it

You need Docker.

```bash
docker compose up --build
```

| Service | URL |
|---|---|
| API and docs | http://localhost:8000/docs |
| Mailhog inbox (email goes here) | http://localhost:8025 |
| Worker metrics | http://localhost:9101 (email), 9102 (sms), 9103 (push) |

Compose starts the API, one worker per channel, a bulk worker, the scheduler, Postgres, Redis and Mailhog. SMS and push providers are mocks. They fail 20% and 10% of the time by default so you can watch retries and fallback work.

## Try it

```bash
# create a user and a template
curl -X POST localhost:8000/users -H "content-type: application/json" \
  -d '{"name":"Sam","email":"sam@example.com","phone":"+911234567890","timezone":"Asia/Kolkata"}'

curl -X POST localhost:8000/templates -H "content-type: application/json" \
  -d '{"name":"otp","channel":"email","subject":"Hi {{ name }}","body":"Your code is {{ code }}"}'

# send a notification (use the user id from the first call)
curl -X POST localhost:8000/notifications -H "content-type: application/json" \
  -H "Idempotency-Key: order-1001" \
  -d '{"user_id":"<USER_ID>","channel":"email","template":"otp","payload":{"code":"4821"},"priority":"high"}'

# check its status and attempts
curl localhost:8000/notifications/<NOTIFICATION_ID>
```

Send the same request again with the same `Idempotency-Key` and you get the original notification back with the header `Idempotent-Replay: true`.

## API

| Method | Path | Purpose |
|---|---|---|
| POST | `/notifications` | Send one notification. Supports `priority` (high, normal, low) and `send_at` |
| POST | `/notifications/bulk` | Send one template to many users. Body takes `user_ids` or `"segment": "all"` |
| GET | `/bulk/{id}` | Bulk progress |
| GET | `/notifications/{id}` | Status and attempt history |
| GET | `/notifications?user_id=` | A user's notifications |
| POST | `/notifications/{id}/delivered` | Delivery receipt callback, moves `sent` to `delivered` |
| POST, GET | `/users`, `/users/{id}` | Create and read users |
| PUT | `/users/{id}/preferences/{channel}` | Opt in or out, set quiet hours (`HH:MM`) |
| GET | `/users/{id}/preferences` | Read preferences |
| POST, GET | `/templates`, `/templates/{name}` | Jinja2 templates |
| GET | `/admin/queues` | Queue depths per channel |
| POST | `/admin/dlq/replay?channel=` | Put dead lettered jobs back on the queue |
| GET | `/health`, `/metrics` | Liveness and Prometheus metrics |

Statuses: `queued`, `scheduled`, `sent`, `delivered`, `failed`, `skipped`.

## How a send works

1. The API validates the request, renders the template and saves the notification.
2. The job goes onto a Redis queue for its channel and priority, or onto a delayed set if it is scheduled or inside the user's quiet hours.
3. A channel worker takes the job, checks the user and provider rate limits, then tries the primary provider and falls back to the backup if it fails or its circuit is open.
4. Failures retry with exponential backoff and jitter. After the last attempt the job goes to the dead letter queue.
5. The scheduler moves due delayed jobs onto the queues and returns jobs from crashed workers.

## Configuration

Set through environment variables (see `app/config.py` for all of them).

| Variable | Default | Meaning |
|---|---|---|
| `DATABASE_URL` | local Postgres | Async SQLAlchemy URL |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection |
| `MAX_ATTEMPTS` | 5 | Attempts before the dead letter queue |
| `BACKOFF_BASE_SECONDS` | 2 | Retry delay base |
| `BACKOFF_CAP_SECONDS` | 300 | Longest retry delay |
| `USER_RATE_CAPACITY` / `USER_RATE_PER_SECOND` | 10 / 1 | Per user and channel bucket |
| `PROVIDER_RATE_CAPACITY` / `PROVIDER_RATE_PER_SECOND` | 200 / 100 | Per provider bucket |
| `BREAKER_FAILURE_THRESHOLD` | 5 | Failures before a provider is skipped |
| `BREAKER_RECOVERY_SECONDS` | 30 | Wait before a probe call |
| `SMS_FAILURE_RATE`, `PUSH_FAILURE_RATE` | 0 | Mock provider failure rates |
| `WORKER_CONCURRENCY` | 5 | Consumers per worker process |

## Run without Docker

Start Postgres, Redis and (optionally) Mailhog yourself, then:

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
python -m app.workers.email_worker
python -m app.workers.sms_worker
python -m app.workers.push_worker
python -m app.workers.bulk_worker
python -m app.core.scheduler
```

## Load test

```bash
pip install locust
locust -f loadtest/locustfile.py --host http://localhost:8000
```

Results are not recorded yet. Run it against your own setup and add the numbers here.

## Layout

```
app/
  api/         HTTP routes
  core/        queue, rate limiter, retry, circuit breaker, idempotency, scheduler
  providers/   email (SMTP), SMS and push (mock), backups
  services/    notification, bulk, preference and template logic
  workers/     delivery worker, bulk worker, entry points per channel
  models/      SQLAlchemy tables
  schemas/     request and response models
loadtest/      Locust scenarios
docs/          design document
```
