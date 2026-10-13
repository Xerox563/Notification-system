# Notification System: Project Spec

A scalable, asynchronous notification service built with FastAPI, Postgres, and Redis.
Supports email, SMS, and push, with retries, idempotency, priorities, scheduling, bulk fan-out, and provider failover.

---

## 1. Features

### Must have
- [x] **API:** `POST /notifications` accepts a user, channel, template, and payload, and returns `202 Accepted` right away with a notification id.
- [x] **Async processing:** a Redis-backed queue with separate hand-rolled workers per channel (email, SMS, push). SMS and push providers are mocked, with a configurable failure rate for testing. Email goes through real SMTP (Mailhog locally).
- [x] **Retries:** exponential backoff with jitter, a max attempt limit, and a dead-letter queue, plus a DLQ replay script/endpoint.
- [x] **Idempotency:** an `Idempotency-Key` header stored in Redis (with a unique constraint in Postgres as backup), so retries return the original response and never send duplicates.
- [x] **User preferences:** opt-in/out per channel, plus quiet hours with timezone support. Notifications that fall in quiet hours are deferred, not dropped.
- [x] **Templates:** Jinja2 templates with variables, stored in Postgres, with CRUD endpoints and validation of required variables.
- [x] **Status tracking:** `queued -> sent -> delivered/failed`, exposed via `GET /notifications/{id}`, with the full per-attempt history (`delivery_attempts` table).
- [x] **Rate limiting:** a token bucket in Redis (Lua for atomicity), applied per user and per provider.

### Nice to have (all included)
- [x] **Priority queues:** high (OTP/alerts), normal, and low (marketing) queues per channel. Workers use weighted polling so low priority never starves.
- [x] **Circuit breaker with fallback:** closed/open/half-open states around each provider. When the primary email or SMS provider is failing, traffic routes to a second provider.
- [x] **Scheduled notifications:** a `send_at` field, backed by a Redis sorted set and a scheduler loop that moves due jobs onto the live queues.
- [x] **Bulk fan-out:** `POST /notifications/bulk` takes one event and a list or segment of users (up to 100k). It splits them into chunked batches, processes them as background jobs, and tracks progress via `GET /bulk/{id}`.

### Supporting features
- [x] **Observability:** structured JSON logs, Prometheus `/metrics` (queue depth, send rate, failure rate, retries, breaker state), and `/health`.
- [x] **Graceful shutdown:** workers finish in-flight jobs and re-queue anything unfinished.
- [x] **Crash safety:** a visibility-timeout / processing-list pattern, so a job isn't lost if a worker dies mid-send.
- [ ] **Load testing:** Locust scenarios, with results recorded in the README.
- [ ] **CI:** GitHub Actions running ruff and a Docker build.
- [ ] **Design doc:** requirements, capacity estimates, architecture diagram, trade-offs, failure scenarios, and a 100x scaling plan.

### Skip
Real SMS/push integrations, multi-region, and Kafka.

---

## 2. Stack
FastAPI, Postgres (notifications, preferences, templates, attempts), Redis (queues, scheduling, rate limits, idempotency keys), hand-rolled async worker processes, Docker Compose (api, workers, scheduler, postgres, redis, mailhog), pytest (local only), and Locust.

---

## 3. Folder structure
```
notification-system/
├── app/
│   ├── main.py                  # FastAPI app, startup/shutdown
│   ├── config.py                # env settings (pydantic-settings)
│   ├── api/
│   │   ├── notifications.py     # POST/GET notifications, bulk
│   │   ├── preferences.py       # user channel opt-in/out, quiet hours
│   │   ├── templates.py         # template CRUD
│   │   └── health.py            # /health, /metrics
│   ├── core/
│   │   ├── queue.py             # Queue interface + Redis impl (priority, delayed)
│   │   ├── scheduler.py         # moves due scheduled jobs to live queues
│   │   ├── retry.py             # backoff + jitter
│   │   ├── rate_limiter.py      # token bucket (Redis + Lua)
│   │   ├── idempotency.py       # Idempotency-Key handling
│   │   └── circuit_breaker.py   # closed/open/half-open
│   ├── providers/
│   │   ├── base.py              # Provider interface
│   │   ├── email_smtp.py        # real SMTP (Mailhog)
│   │   ├── email_backup.py      # fallback provider
│   │   ├── sms_mock.py          # mock, configurable failure rate
│   │   └── push_mock.py
│   ├── services/
│   │   ├── notification_service.py   # validate, check prefs, render, enqueue
│   │   ├── bulk_service.py           # chunked fan-out
│   │   ├── preference_service.py
│   │   └── template_service.py       # Jinja2 rendering
│   ├── workers/
│   │   ├── worker.py            # generic consumer loop
│   │   ├── email_worker.py
│   │   ├── sms_worker.py
│   │   └── push_worker.py
│   ├── models/                  # SQLAlchemy models
│   ├── schemas/                 # Pydantic schemas
│   └── db/                      # session and table creation
├── loadtest/locustfile.py
├── docs/
│   ├── design.md                # requirements, estimates, trade-offs
│   └── architecture.png
├── docker-compose.yml           # api, workers, scheduler, postgres, redis, mailhog
├── Dockerfile
├── .github/workflows/ci.yml
├── pyproject.toml
├── .gitignore                   # tests/ is ignored (local only)
└── README.md
```

> `tests/` exists locally for development but is **git-ignored** and never pushed.

---

## 4. API endpoints
| Method | Path | Purpose |
|---|---|---|
| POST | `/notifications` | Accept request, return `202` + id. Supports `Idempotency-Key`, `priority`, `channel`, `template`, `payload`, `send_at` |
| POST | `/notifications/bulk` | Fan out one event to many users in chunked batches |
| GET | `/bulk/{id}` | Bulk job progress |
| GET | `/notifications/{id}` | Status and attempt history |
| GET | `/notifications?user_id=` | List a user's notifications |
| PUT | `/users/{id}/preferences` | Channel opt-in/out, quiet hours, timezone |
| GET | `/users/{id}/preferences` | Read preferences |
| POST/GET | `/templates` | Create and fetch Jinja2 templates |
| POST | `/admin/dlq/replay` | Replay dead-lettered jobs |
| GET | `/health`, `/metrics` | Liveness and Prometheus metrics |

---

## 5. Data model (Postgres)
- **users:** id, email, phone, device_token, timezone
- **user_preferences:** user_id, channel, enabled, quiet_start, quiet_end
- **templates:** id, name, channel, subject, body
- **notifications:** id, user_id, channel, template_id, payload, priority, status, send_at, idempotency_key (unique), bulk_id, created_at
- **delivery_attempts:** id, notification_id, attempt_no, provider, status, error, timestamp
- **bulk_jobs:** id, total, processed, failed, status, created_at

---

## 6. Request flow
1. Client calls `POST /notifications` with an `Idempotency-Key`.
2. The API checks idempotency (a duplicate returns the original response), validates, checks user preferences and quiet hours, renders the template, saves the row as `queued`, and pushes to the Redis queue for that channel and priority (or to the scheduled set if `send_at` is in the future). It returns `202`.
3. A channel worker polls queues (high, normal, low, with weighting to avoid starvation).
4. The worker checks the rate limit (per user and per provider), then the circuit breaker, then calls the provider.
5. On success, status becomes `sent`. On failure, it retries with exponential backoff and jitter, and after max attempts the job goes to the dead-letter queue and status becomes `failed`.
6. Each attempt is logged in `delivery_attempts`.
7. If the primary provider's circuit is open, the worker routes to the fallback provider.

---

## 7. Design doc contents (`docs/design.md`)
- Functional and non-functional requirements.
- Capacity estimate (e.g. 10M notifications/day is about 115/s average, about 1k/s peak).
- Architecture diagram and the request flow above.
- Trade-offs: Redis vs. RabbitMQ/Kafka, at-least-once with idempotency, Postgres as the source of truth.
- Failure scenarios (worker crash, Redis down, provider down) and how each is handled.
- How to scale 100x: partitioned queues, more workers, read replicas, and moving to Kafka.

---

## 8. Testing policy
- Tests are written and run **locally** during development (pytest, fakeredis, SQLite).
- Coverage: backoff and jitter bounds, token bucket, breaker transitions, template rendering, quiet-hours logic, end-to-end send, duplicate request, provider failure and retry, DLQ, fallback, scheduling, and bulk.
- The `tests/` folder is listed in `.gitignore` and **is not pushed to GitHub**.
