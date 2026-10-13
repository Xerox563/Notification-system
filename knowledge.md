# Knowledge

What this project already does, and what can be added next.

---

## 1. Features built

### Must have
- **API:** `POST /notifications` takes a user, channel, template and payload, and returns `202 Accepted` right away with a notification id.
- **Async processing:** a Redis queue with a separate worker per channel (email, SMS, push). SMS and push providers are mocks with a configurable failure rate. Email goes through real SMTP (Mailhog locally).
- **Retries:** exponential backoff with jitter, a max attempt limit, and a dead letter queue. `POST /admin/dlq/replay` puts dead lettered jobs back.
- **Idempotency:** the `Idempotency-Key` header is stored in Redis, with a unique column in Postgres as backup. A repeat returns the original notification and never sends twice.
- **User preferences:** opt in or out per channel, plus quiet hours with timezone support. Quiet hours delay a send, they do not drop it. High priority ignores quiet hours.
- **Templates:** Jinja2 templates with variables, stored in Postgres. Required variables are detected when the template is saved and checked on every send.
- **Status tracking:** `queued`, `scheduled`, `sent`, `delivered`, `failed`, `skipped`. `GET /notifications/{id}` returns the status and every attempt.
- **Rate limiting:** a token bucket in Redis (Lua, so it is atomic), applied per user and channel and per provider.

### Nice to have
- **Priority queues:** high, normal and low queues per channel. Workers rotate which priority they check first, so low priority is never starved.
- **Circuit breaker with fallback:** closed, open and half open states around each provider. When the primary fails, traffic goes to the backup provider.
- **Scheduled notifications:** `send_at` puts the job in a Redis sorted set. The scheduler moves it onto the live queue when it is due.
- **Bulk fan out:** `POST /notifications/bulk` takes a user list or the `all` segment (up to 100k users), splits it into chunks of 500, and tracks progress at `GET /bulk/{id}`.

### Supporting features
- **Observability:** JSON logs, Prometheus `/metrics` (queue depth, sends, retries, dead letters, breaker state), and `/health` that checks Postgres and Redis.
- **Graceful shutdown:** workers finish the job in hand, then stop.
- **Crash safety:** a popped job sits in a processing set with a deadline. If a worker dies, the scheduler puts the job back on the queue.
- **Admin endpoints:** queue depths per channel and dead letter replay.
- **Delivery receipts:** `POST /notifications/{id}/delivered` moves `sent` to `delivered`.
- **Docker setup:** one `docker compose up --build` starts everything.
- **CI:** GitHub Actions runs ruff and a Docker build.
- **Load test:** Locust scenarios in `loadtest/`. No numbers recorded yet.
- **Design doc:** requirements, capacity estimate, diagram, trade offs, failure table and a 100x plan in `docs/design.md`.

---

## 2. What we can add

### Fix known gaps first
- **Recovery for lost queue pushes:** if Redis fails right after a notification is saved, it stays `queued` forever. Add a job that finds old `queued` rows with no job and enqueues them again, or use the outbox pattern.
- **Shared circuit breaker state:** keep breaker state in Redis so all workers agree, instead of each worker learning alone.
- **Real load test numbers:** run Locust and record requests per second, p95 latency and queue drain time in the README.
- **Database migrations:** replace create on startup with Alembic migrations.

### Good next features
- **Cancel a notification:** `DELETE /notifications/{id}` for anything still `queued` or `scheduled`.
- **API key authentication:** protect every endpoint, with per client keys.
- **Rate limit headers:** return `Retry-After` and remaining tokens to the caller.
- **Template versions:** keep old versions and let a send pin one.
- **Template localization:** pick the template language from the user's locale.
- **Digest mode:** batch many low priority notifications into one summary message.
- **Dedupe window:** drop the same message to the same user within a set time.
- **Unsubscribe links:** one click opt out that updates preferences.
- **Per channel retry rules:** different attempt limits and backoff for OTP and marketing.
- **Smarter fallback order:** choose the backup provider by live success rate.

### Bigger upgrades
- **Real providers:** SendGrid or SES for email, Twilio for SMS, FCM and APNs for push, with real delivery webhooks.
- **Kafka instead of Redis lists:** partitioned by user id for ordering and replay.
- **Multi tenant:** separate apps or teams with their own templates, limits and keys.
- **Tracing:** OpenTelemetry traces from API request through worker to provider.
- **Dashboards and alerts:** Grafana boards, SLOs, and burn rate alerts for failure rate and queue age.
- **Kubernetes:** manifests or a Helm chart, with autoscaling on queue depth.
- **Table partitioning:** partition notifications and attempts by date and drop old partitions for retention.
- **Admin UI:** a small page to browse notifications, the dead letter queue and bulk jobs.
- **Live status stream:** a WebSocket or server sent events feed of status changes.
- **Segments:** saved audiences for bulk sends instead of only a user list or all users.
- **Multi region:** a full stack per region with users routed to their home region.
