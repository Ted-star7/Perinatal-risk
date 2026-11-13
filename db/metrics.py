"""Save a model's results to the shared, hosted metrics store.

Call this at the end of a modeling notebook. It POSTs one row to the hosted
API's /metrics endpoint, so everyone's results collect in the ONE hosted
database and the team can compare all nine models in one place (GET /metrics or
the eval dashboard) — no database password needed on your machine.

    from db.metrics import save_metrics
    save_metrics("perinatal", "gradient_boosting",
                 pr_auc=0.41, roc_auc=0.78, recall_at_flag=0.33,
                 beats_checklist=True, test_events=6189)

Override the target with METRICS_API_URL (e.g. http://localhost:8000 when
running the backend locally). If the server requires a key, set METRICS_KEY.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

# The PUBLIC API URL — not a secret, no credentials. Points at production so
# every teammate's save lands in the same hosted database.
METRICS_API_URL = os.getenv("METRICS_API_URL", "https://perinatal-api.onrender.com")
METRICS_KEY = os.getenv("METRICS_KEY", "")


def save_metrics(
    cohort: str,
    algorithm: str,
    *,
    pr_auc: float,
    roc_auc: float,
    recall_at_flag: float,
    beats_checklist: bool,
    test_events: int,
    is_best: bool = False,
) -> None:
    """POST one model's metrics to the shared /metrics endpoint (upsert)."""
    payload = {
        "cohort": cohort,
        "algorithm": algorithm,
        "pr_auc": float(pr_auc),
        "roc_auc": float(roc_auc),
        "recall_at_flag": float(recall_at_flag),
        "beats_checklist": bool(beats_checklist),
        "test_events": int(test_events),
        "is_best": bool(is_best),
    }
    headers = {"Content-Type": "application/json"}
    if METRICS_KEY:
        headers["X-Metrics-Key"] = METRICS_KEY

    req = urllib.request.Request(
        f"{METRICS_API_URL}/metrics",
        data=json.dumps(payload).encode(),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:  # noqa: S310 (fixed host)
            json.loads(resp.read())
        print(f"saved metrics for {cohort} / {algorithm} -> {METRICS_API_URL}")
    except urllib.error.URLError as exc:
        print(
            f"could not save metrics ({exc}). The API may be waking up (free tier) "
            f"— re-run this cell, or set METRICS_API_URL to a reachable backend."
        )
