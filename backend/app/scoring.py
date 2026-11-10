"""Risk scoring.

A transparent heuristic mirroring the EDA drivers, used until the trained model
is wired in. Swap `score()` to load the joblib artifact when the model is ready
— the response shape stays the same, so the frontend doesn't change.
"""

from __future__ import annotations

import math

from app.schemas import PredictRequest


def score(req: PredictRequest) -> tuple[float, str, list[dict], str]:
    first_pregnancy = req.parity == 0
    drivers: list[dict] = []
    z = -3.25  # baseline log-odds ~3.7%

    def add(cond: bool, weight: float, label: str) -> None:
        nonlocal z
        if cond:
            z += weight
            drivers.append({"label": label, "weight": weight})

    add(req.multiple, 1.4, "Multiple pregnancy")
    add(req.previous_stillbirth, 1.0, "Previous stillbirth")
    add(req.told_high_bp, 0.9, "Told high blood pressure")
    add(req.previous_loss, 0.5, "Previous pregnancy loss")
    add(req.age < 18, 0.4, "Age under 18")
    add(req.age >= 35, 0.5, "Age 35 or older")
    add(req.parity >= 5, 0.4, "Five or more births")
    add(
        not first_pregnancy and req.interval_months is not None and req.interval_months < 24,
        0.4,
        "Short birth interval",
    )
    add(first_pregnancy, 0.3, "First pregnancy")

    risk = 1 / (1 + math.exp(-z))
    pct = risk * 100
    band = "low" if pct < 3 else "moderate" if pct < 8 else "high"
    drivers.sort(key=lambda d: d["weight"], reverse=True)
    return round(risk, 4), band, drivers, _recommend(band)


def _recommend(band: str) -> str:
    if band == "high":
        return (
            "Flag for closer follow-up. Discuss a birth plan and arrange referral to a "
            "facility that can manage a high-risk delivery. Check blood pressure and "
            "urine at every visit."
        )
    if band == "moderate":
        return (
            "Keep antenatal visits frequent. Check blood pressure and urine, confirm "
            "iron is taken, and review again before delivery."
        )
    return (
        "Continue routine antenatal care. Keep attending visits so blood pressure, "
        "urine and iron can be checked."
    )
