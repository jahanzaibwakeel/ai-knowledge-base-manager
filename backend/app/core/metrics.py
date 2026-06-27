import re
import time
from collections import Counter, deque
from threading import Lock


ID_PATTERN = re.compile(r"/([a-f0-9]{24}|[a-f0-9]{12,}|[0-9]+)(?=/|$)", re.IGNORECASE)


def normalize_path(path: str) -> str:
    return ID_PATTERN.sub("/:id", path)


class RequestMetrics:
    def __init__(self) -> None:
        self.started_at = time.time()
        self.total_requests = 0
        self.in_flight = 0
        self.total_latency_ms = 0.0
        self.status_counts: Counter[str] = Counter()
        self.method_counts: Counter[str] = Counter()
        self.path_counts: Counter[str] = Counter()
        self.recent_errors: deque[dict] = deque(maxlen=25)
        self._lock = Lock()

    def start_request(self) -> None:
        with self._lock:
            self.in_flight += 1

    def finish_request(self, method: str, path: str, status_code: int, elapsed_ms: float) -> None:
        normalized_path = normalize_path(path)
        status_family = f"{status_code // 100}xx"
        with self._lock:
            self.in_flight = max(0, self.in_flight - 1)
            self.total_requests += 1
            self.total_latency_ms += elapsed_ms
            self.status_counts[status_family] += 1
            self.status_counts[str(status_code)] += 1
            self.method_counts[method.upper()] += 1
            self.path_counts[normalized_path] += 1
            if status_code >= 500:
                self.recent_errors.append(
                    {
                        "method": method.upper(),
                        "path": normalized_path,
                        "status_code": status_code,
                        "elapsed_ms": round(elapsed_ms, 2),
                        "timestamp": time.time(),
                    }
                )

    def snapshot(self) -> dict:
        with self._lock:
            average_latency = self.total_latency_ms / self.total_requests if self.total_requests else 0.0
            return {
                "uptime_seconds": round(time.time() - self.started_at, 2),
                "total_requests": self.total_requests,
                "in_flight": self.in_flight,
                "average_latency_ms": round(average_latency, 2),
                "status_counts": dict(self.status_counts),
                "method_counts": dict(self.method_counts),
                "path_counts": dict(self.path_counts),
                "recent_errors": list(self.recent_errors),
            }

    def prometheus(self) -> str:
        snapshot = self.snapshot()
        lines = [
            "# HELP kb_uptime_seconds Application uptime in seconds.",
            "# TYPE kb_uptime_seconds gauge",
            f"kb_uptime_seconds {snapshot['uptime_seconds']}",
            "# HELP kb_requests_total Total HTTP requests.",
            "# TYPE kb_requests_total counter",
            f"kb_requests_total {snapshot['total_requests']}",
            "# HELP kb_requests_in_flight Current in-flight HTTP requests.",
            "# TYPE kb_requests_in_flight gauge",
            f"kb_requests_in_flight {snapshot['in_flight']}",
            "# HELP kb_request_latency_average_ms Average request latency in milliseconds.",
            "# TYPE kb_request_latency_average_ms gauge",
            f"kb_request_latency_average_ms {snapshot['average_latency_ms']}",
        ]
        for status, count in sorted(snapshot["status_counts"].items()):
            lines.append(f'kb_requests_by_status_total{{status="{status}"}} {count}')
        for method, count in sorted(snapshot["method_counts"].items()):
            lines.append(f'kb_requests_by_method_total{{method="{method}"}} {count}')
        for path, count in sorted(snapshot["path_counts"].items()):
            lines.append(f'kb_requests_by_path_total{{path="{path}"}} {count}')
        return "\n".join(lines) + "\n"


request_metrics = RequestMetrics()
