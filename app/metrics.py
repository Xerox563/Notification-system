from prometheus_client import Counter, Gauge

NOTIFICATIONS_CREATED = Counter(
    "notifications_created_total", "Notifications accepted by the api", ["channel", "priority", "status"]
)
DELIVERIES = Counter(
    "deliveries_total", "Provider send results", ["channel", "provider", "outcome"]
)
RETRIES = Counter("retries_total", "Notifications scheduled for another attempt", ["channel"])
DEAD_LETTERED = Counter("dead_lettered_total", "Notifications moved to the dead letter queue", ["channel"])
BREAKER_STATE = Gauge("circuit_breaker_state", "0 closed, 1 half open, 2 open", ["provider"])
QUEUE_DEPTH = Gauge("queue_depth", "Jobs waiting in a queue", ["channel", "priority"])
