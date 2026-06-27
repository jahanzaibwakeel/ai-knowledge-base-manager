import unittest

from app.core.metrics import RequestMetrics, normalize_path


class MetricsTests(unittest.TestCase):
    def test_normalize_path_replaces_high_cardinality_ids(self):
        self.assertEqual(normalize_path("/api/v1/documents/507f1f77bcf86cd799439011"), "/api/v1/documents/:id")
        self.assertEqual(normalize_path("/api/v1/workspaces/123/documents"), "/api/v1/workspaces/:id/documents")

    def test_request_metrics_records_counts_and_latency(self):
        metrics = RequestMetrics()
        metrics.start_request()
        metrics.finish_request("get", "/api/v1/documents/507f1f77bcf86cd799439011", 200, 25.5)

        snapshot = metrics.snapshot()

        self.assertEqual(snapshot["total_requests"], 1)
        self.assertEqual(snapshot["in_flight"], 0)
        self.assertEqual(snapshot["status_counts"]["2xx"], 1)
        self.assertEqual(snapshot["method_counts"]["GET"], 1)
        self.assertEqual(snapshot["path_counts"]["/api/v1/documents/:id"], 1)
        self.assertEqual(snapshot["average_latency_ms"], 25.5)

    def test_prometheus_output_contains_core_metrics(self):
        metrics = RequestMetrics()
        metrics.finish_request("post", "/api/v1/rag/query", 500, 10)

        output = metrics.prometheus()

        self.assertIn("kb_requests_total 1", output)
        self.assertIn('kb_requests_by_status_total{status="500"} 1', output)
        self.assertIn('kb_requests_by_status_total{status="5xx"} 1', output)


if __name__ == "__main__":
    unittest.main()
