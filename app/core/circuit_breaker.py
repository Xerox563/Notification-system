import time


class CircuitBreaker:
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

    def __init__(self, failure_threshold: int = 5, recovery_seconds: float = 30.0, clock=time.monotonic):
        self.failure_threshold = failure_threshold
        self.recovery_seconds = recovery_seconds
        self.clock = clock
        self.state = self.CLOSED
        self.failures = 0
        self.opened_at = 0.0
        self.probe_in_flight = False

    def allow(self) -> bool:
        if self.state == self.CLOSED:
            return True
        if self.state == self.OPEN:
            if self.clock() - self.opened_at < self.recovery_seconds:
                return False
            self.state = self.HALF_OPEN
            self.probe_in_flight = False
        if self.probe_in_flight:
            return False
        self.probe_in_flight = True
        return True

    def record_success(self) -> None:
        self.state = self.CLOSED
        self.failures = 0
        self.probe_in_flight = False

    def record_failure(self) -> None:
        if self.state == self.HALF_OPEN:
            self._open()
            return
        self.failures += 1
        if self.failures >= self.failure_threshold:
            self._open()

    def _open(self) -> None:
        self.state = self.OPEN
        self.opened_at = self.clock()
        self.probe_in_flight = False

    @property
    def state_value(self) -> int:
        return {self.CLOSED: 0, self.HALF_OPEN: 1, self.OPEN: 2}[self.state]
