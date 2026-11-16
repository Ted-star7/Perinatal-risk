"""Catch notebook publishing failures and configuration changes after import."""

import io
import json
import os
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from db.metrics import save_metrics


class MetricsClientTests(unittest.TestCase):
    def test_configuration_is_read_when_the_notebook_publishes(self):
        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def read(self):
                return b'{"saved":"lbw/random_forest"}'

        environment = {"METRICS_API_URL": "http://localhost:8000/", "METRICS_KEY": "test-key"}
        with (
            patch.dict(os.environ, environment),
            patch("db.metrics.urllib.request.urlopen", return_value=Response()) as send,
        ):
            save_metrics(
                "lbw",
                "random_forest",
                pr_auc=0.14,
                roc_auc=0.65,
                recall_at_flag=0.5,
                beats_checklist=True,
                test_events=130,
            )
        request = send.call_args.args[0]
        self.assertEqual(request.full_url, "http://localhost:8000/metrics")
        self.assertEqual(request.get_header("X-metrics-key"), "test-key")
        self.assertEqual(json.loads(request.data)["test_events"], 130)

    def test_a_rejected_metric_is_reported_as_a_failure(self):
        failure = HTTPError("http://localhost:8000/metrics", 401, "Unauthorized", {}, io.BytesIO())
        with patch("db.metrics.urllib.request.urlopen", side_effect=failure):
            with self.assertRaisesRegex(RuntimeError, "HTTP 401"):
                save_metrics(
                    "lbw",
                    "random_forest",
                    pr_auc=0.14,
                    roc_auc=0.65,
                    recall_at_flag=0.5,
                    beats_checklist=True,
                    test_events=130,
                )
