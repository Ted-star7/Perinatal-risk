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
running the backend locally). Set METRICS_KEY to the API’s publishing key before saving.
Configuration is read for each call, so notebook environment changes take effect immediately.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

# The PUBLIC API URL — not a secret, no credentials. Points at production so
# every teammate's save lands in the same hosted database.
METRICS_API_URL = "https://perinatal-api.onrender.com"
METRICS_KEY = ""


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
    base_url = os.getenv("METRICS_API_URL", METRICS_API_URL).rstrip("/")
    publishing_key = os.getenv("METRICS_KEY", METRICS_KEY)
    headers = {"Content-Type": "application/json"}
    if publishing_key:
        headers["X-Metrics-Key"] = publishing_key

    req = urllib.request.Request(
        f"{base_url}/metrics",
        data=json.dumps(payload).encode(),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            confirmation = json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        raise RuntimeError(
            f"Could not save {cohort}/{algorithm}: the API returned HTTP {exc.code}. "
            "Check METRICS_API_URL and the publishing key, then retry."
        ) from exc
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        raise RuntimeError(
            f"Could not confirm that {cohort}/{algorithm} was saved. "
            "Check the API connection and retry."
        ) from exc
    if not isinstance(confirmation, dict) or confirmation.get("saved") != f"{cohort}/{algorithm}":
        raise RuntimeError(
            "The API did not confirm the submitted model metric. Retry the publication."
        )
    print(f"saved metrics for {cohort} / {algorithm} -> {base_url}")
