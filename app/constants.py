from enum import Enum


class Channel(str, Enum):
    email = "email"
    sms = "sms"
    push = "push"


class Priority(str, Enum):
    high = "high"
    normal = "normal"
    low = "low"


class Status(str, Enum):
    queued = "queued"
    scheduled = "scheduled"
    sent = "sent"
    delivered = "delivered"
    failed = "failed"
    skipped = "skipped"


FINAL_STATUSES = {Status.sent.value, Status.delivered.value, Status.failed.value, Status.skipped.value}
PRIORITY_ORDER = [Priority.high.value, Priority.normal.value, Priority.low.value]
