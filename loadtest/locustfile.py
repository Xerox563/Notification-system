import random
import uuid

from locust import HttpUser, between, task

TEMPLATES = {
    "email": "load_email",
    "sms": "load_sms",
    "push": "load_push",
}


class NotificationUser(HttpUser):
    wait_time = between(0.05, 0.2)

    def on_start(self):
        self.user_ids = []
        for i in range(5):
            r = self.client.post(
                "/users",
                json={
                    "name": f"load{i}",
                    "email": f"load{i}-{uuid.uuid4().hex[:6]}@example.com",
                    "phone": "+911234567890",
                    "device_token": uuid.uuid4().hex,
                },
                name="/users",
            )
            self.user_ids.append(r.json()["id"])
        for channel, name in TEMPLATES.items():
            self.client.post(
                "/templates",
                json={
                    "name": name,
                    "channel": channel,
                    "subject": "Hello {{ name }}",
                    "body": "Code {{ code }}",
                },
                name="/templates",
            )

    def send(self, channel: str, priority: str, key: str | None = None):
        headers = {"Idempotency-Key": key} if key else {}
        self.client.post(
            "/notifications",
            json={
                "user_id": random.choice(self.user_ids),
                "channel": channel,
                "template": TEMPLATES[channel],
                "payload": {"code": str(random.randint(1000, 9999))},
                "priority": priority,
            },
            headers=headers,
            name="/notifications",
        )

    @task(6)
    def send_email(self):
        self.send("email", "normal", uuid.uuid4().hex)

    @task(3)
    def send_sms_otp(self):
        self.send("sms", "high", uuid.uuid4().hex)

    @task(2)
    def send_push(self):
        self.send("push", "low")

    @task(1)
    def check_status(self):
        r = self.client.post(
            "/notifications",
            json={
                "user_id": random.choice(self.user_ids),
                "channel": "email",
                "template": TEMPLATES["email"],
                "payload": {"code": "0000"},
            },
            name="/notifications",
        )
        if r.status_code == 202:
            self.client.get(f"/notifications/{r.json()['id']}", name="/notifications/{id}")
