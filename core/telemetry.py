"""
TripWeaver AI — Enterprise Telemetry & Metrics
================================================
Thread-safe, lightweight metrics registry collecting operational counters,
execution timings, agent invocations, and error rates.
"""

import threading
import time
from typing import Any, Dict


class MetricsRegistry:
    """Enterprise metrics collector for operational observability and Prometheus scraping."""

    def __init__(self):
        self._lock = threading.Lock()
        self.request_count = 0
        self.request_errors = 0
        self.total_llm_calls = 0
        self.agent_runs: Dict[str, int] = {
            "supervisor_agent": 0,
            "flight_agent": 0,
            "hotel_agent": 0,
            "weather_agent": 0,
            "budget_agent": 0,
            "itinerary_agent": 0,
            "human_approval_agent": 0,
            "final_agent": 0,
        }
        self.agent_latencies_ms: Dict[str, float] = {}
        self.start_time = time.time()

    def record_request(self, success: bool = True):
        with self._lock:
            self.request_count += 1
            if not success:
                self.request_errors += 1

    def record_agent_run(self, agent_name: str, duration_ms: float):
        with self._lock:
            self.agent_runs[agent_name] = self.agent_runs.get(agent_name, 0) + 1
            prev_avg = self.agent_latencies_ms.get(agent_name, 0.0)
            count = self.agent_runs[agent_name]
            # Running average
            self.agent_latencies_ms[agent_name] = (
                (prev_avg * (count - 1) + duration_ms) / count if count > 0 else duration_ms
            )

    def record_llm_calls(self, count: int = 1):
        with self._lock:
            self.total_llm_calls += count

    def get_snapshot(self) -> Dict[str, Any]:
        with self._lock:
            uptime_seconds = round(time.time() - self.start_time, 2)
            return {
                "uptime_seconds": uptime_seconds,
                "total_requests": self.request_count,
                "error_requests": self.request_errors,
                "error_rate_pct": round(
                    (self.request_errors / self.request_count * 100)
                    if self.request_count > 0 else 0.0,
                    2,
                ),
                "total_llm_calls": self.total_llm_calls,
                "agent_invocations": dict(self.agent_runs),
                "agent_avg_latencies_ms": {
                    k: round(v, 2) for k, v in self.agent_latencies_ms.items()
                },
            }


metrics = MetricsRegistry()
