"""Regressions for access, pinned results, release integrity and data recovery."""

from __future__ import annotations

import unittest
from unittest.mock import patch
from uuid import uuid4

import numpy as np
import pandas as pd
from app.auth import create_token
from app.config import settings
from app.database import SessionLocal
from app.main import app
from app.models import Doctor
from app.schemas import AssessmentResult, ChecklistResult, OutcomeResult
from app.seeding import seed_cohorts
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text

from ml.src.artifacts import FORMAT_VERSION, contract_hash, validate_bundle
from ml.src.dataset import check_counts


class AccessTests(unittest.TestCase):
    def setUp(self):
        self.seeding = patch("app.main.seed_cohorts")
        self.seeding.start()
        self.client = TestClient(app).__enter__()
        result = self.client.post(
            "/clinics/register",
            json={
                "clinic_name": "Audit clinic",
                "doctor_name": "Test clinician",
                "email": f"{uuid4()}@example.com",
                "password": "valid-test-password",
            },
        )
        self.assertEqual(result.status_code, 200, result.text)
        self.session = result.json()
        self.headers = {"Authorization": f"Bearer {self.session['token']}"}

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self.seeding.stop()

    def test_membership_and_deactivation_are_checked(self):
        unknown = {"Authorization": "Bearer " + create_token(999999, 999999)}
        self.assertEqual(self.client.get("/history", headers=unknown).status_code, 401)
        with SessionLocal() as db:
            doctor = db.get(Doctor, self.session["doctor_id"])
            doctor.is_active = False
            db.commit()
        self.assertEqual(self.client.get("/history", headers=self.headers).status_code, 401)

    def test_logout_revokes_the_bearer_token(self):
        self.assertEqual(self.client.post("/logout", headers=self.headers).status_code, 200)
        self.assertEqual(self.client.get("/history", headers=self.headers).status_code, 401)

    def test_registration_rejects_blank_names_and_password(self):
        result = self.client.post(
            "/clinics/register",
            json={
                "clinic_name": " ",
                "doctor_name": "",
                "email": f"{uuid4()}@example.com",
                "password": "",
            },
        )
        self.assertEqual(result.status_code, 422)

    def test_registration_accepts_six_character_password_and_other_countries(self):
        email = f"{uuid4()}@example.com"
        body = {
            "clinic_name": "Test clinic",
            "doctor_name": "Test clinician",
            "email": email,
            "country": "United Kingdom of Great Britain and Northern Ireland",
            "password": "test66",
        }
        result = self.client.post("/clinics/register", json=body)
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual(
            self.client.post("/login", json={"email": email, "password": "test66"}).status_code,
            200,
        )
        body.update(email=f"{uuid4()}@example.com", password="short")
        self.assertEqual(self.client.post("/clinics/register", json=body).status_code, 422)

    def test_metrics_reads_require_sign_in_and_writes_require_publishing_key(self):
        body = {
            "cohort": "perinatal",
            "algorithm": "random_forest",
            "pr_auc": 0.1,
            "roc_auc": 0.6,
            "recall_at_flag": 0.5,
            "beats_checklist": True,
            "test_events": 20,
            "is_best": True,
        }
        self.assertEqual(self.client.get("/metrics").status_code, 401)
        self.assertEqual(self.client.get("/metrics", headers=self.headers).status_code, 200)
        self.assertEqual(self.client.post("/metrics", json=body).status_code, 401)
        with patch.object(settings, "metrics_key", "unit-test-publication-key"):
            headers = {"X-Metrics-Key": "unit-test-publication-key"}
            self.assertEqual(
                self.client.post("/metrics", json=body, headers=headers).status_code, 200
            )
            other = body | {"algorithm": "gradient_boosting"}
            self.assertEqual(
                self.client.post("/metrics", json=other, headers=headers).status_code, 200
            )
            rows = self.client.get("/metrics", headers=self.headers).json()
            selected = [row for row in rows if row["cohort"] == "perinatal" and row["is_best"]]
            self.assertEqual([row["algorithm"] for row in selected], ["gradient_boosting"])
            self.assertEqual(
                self.client.post(
                    "/metrics", json=body | {"pr_auc": 4}, headers=headers
                ).status_code,
                422,
            )

    def test_birth_followup_is_scoped_versioned_and_does_not_change_prediction(self):
        from app.models import Prediction
        from app.seed_followups import seed_followups

        self.assertEqual(seed_followups(self.session["doctor_id"]), 3)
        self.assertEqual(seed_followups(self.session["doctor_id"]), 0)
        rows = self.client.get("/history", headers=self.headers).json()
        row = next(r for r in rows if r["patient_ref"] == "DEMO-FOLLOWUP-1")
        url = f"/predictions/{row['id']}/outcomes"
        self.assertEqual(len(row["outcomes"]), 1)
        before = row["outcomes"][0]
        body = {
            key: before[key]
            for key in [
                "baby_number",
                "birth_date",
                "observed_on",
                "status",
                "death_age_days",
                "birth_weight_grams",
                "source",
                "notes",
            ]
        } | {"expected_version": 1, "notes": "Follow-up and referral reviewed."}
        self.assertEqual(self.client.post(url, json=body).status_code, 401)
        saved = self.client.post(url, json=body, headers=self.headers)
        self.assertEqual(saved.status_code, 200, saved.text)
        self.assertEqual(saved.json()["version"], 2)
        self.assertEqual(self.client.post(url, json=body, headers=self.headers).status_code, 409)
        self.assertEqual(
            self.client.post(
                url, json=body | {"baby_number": 2, "expected_version": 0}, headers=self.headers
            ).status_code,
            422,
        )
        revisions = self.client.get(url, headers=self.headers).json()
        self.assertEqual([r["version"] for r in revisions], [2, 1])
        self.assertEqual(revisions[1]["notes"], before["notes"])
        self.assertEqual(revisions[0]["doctor_id"], self.session["doctor_id"])
        refreshed = self.client.get("/history", headers=self.headers).json()
        latest = next(r for r in refreshed if r["id"] == row["id"])
        self.assertEqual(latest["outcomes"][0]["version"], 2)
        self.assertEqual(latest["recommendation"], row["recommendation"])
        self.assertEqual(latest["risk"], row["risk"])
        other = self.client.post(
            "/clinics/register",
            json={
                "clinic_name": "Other clinic",
                "doctor_name": "Other clinician",
                "email": f"{uuid4()}@example.com",
                "password": "test66",
            },
        ).json()
        other_headers = {"Authorization": f"Bearer {other['token']}"}
        self.assertEqual(self.client.get(url, headers=other_headers).status_code, 404)
        self.assertEqual(self.client.post(url, json=body, headers=other_headers).status_code, 404)
        with SessionLocal() as db:
            prediction = db.get(Prediction, row["id"])
            prediction.inputs = prediction.inputs | {"multiple": True}
            db.commit()
        twin = self.client.post(
            url,
            json=body | {"baby_number": 2, "expected_version": 0, "birth_weight_grams": 2400},
            headers=self.headers,
        )
        self.assertEqual(twin.status_code, 200, twin.text)
        latest = next(
            r
            for r in self.client.get("/history", headers=self.headers).json()
            if r["id"] == row["id"]
        )
        self.assertEqual({o["baby_number"] for o in latest["outcomes"]}, {1, 2})

    def test_outcome_dates_and_unknowns_are_validated(self):
        from datetime import datetime, timedelta, timezone

        from app.schemas import BirthOutcomeIn

        today = datetime.now(timezone.utc).date()
        body = {
            "baby_number": 1,
            "expected_version": 0,
            "observed_on": today,
            "status": "unknown",
            "source": "Mother’s report",
        }
        self.assertIsNone(BirthOutcomeIn(**body).birth_weight_grams)
        for update in [
            {"source": "  "},
            {"status": "alive"},
            {"observed_on": today + timedelta(days=1)},
            {"birth_date": today + timedelta(days=1)},
            {"birth_weight_grams": -1},
            {"status": "died", "birth_date": today},
            {"status": "died", "birth_date": today, "death_age_days": 1},
            {"death_age_days": 0},
        ]:
            with self.assertRaises(ValueError):
                BirthOutcomeIn(**(body | update))
        death = BirthOutcomeIn(
            **(body | {"birth_date": today, "status": "died", "death_age_days": 0})
        )
        self.assertEqual(death.death_age_days, 0)

    def test_save_uses_the_reviewed_snapshot_after_model_change(self):
        outcome = OutcomeResult(
            status="available",
            label="Research",
            description="Research",
            score=0.04,
            model_id="reviewed-release",
            message="Research",
        )
        result = AssessmentResult(
            perinatal=outcome,
            lbw=outcome,
            notes=[],
            baseline=ChecklistResult(
                flagged=False, factors=[], unknown_factors=[], summary="Clear"
            ),
            recommendation="Review",
        )
        body = {
            "patient_ref": "ANC-014",
            "request_id": str(uuid4()),
            "age": 29,
            "parity": 1,
            "interval_months": 30,
        }
        with patch("app.routers.predictions.score", return_value=result) as scoring:
            preview = self.client.post("/assess", json=body, headers=self.headers).json()
            scoring.side_effect = RuntimeError("Model service changed after preview")
            saved = self.client.post(
                "/predict",
                json=body
                | {
                    "assessment_token": preview["assessment_token"],
                },
                headers=self.headers,
            )
        self.assertEqual(saved.status_code, 200, saved.text)
        self.assertEqual(saved.json()["risk"], 0.04)
        self.assertEqual(scoring.call_count, 1)

    def test_invited_colleague_joins_existing_clinic(self):
        invitation = self.client.post(
            "/clinics/invitations", json={"email": f"{uuid4()}@example.com"}, headers=self.headers
        ).json()
        joined = self.client.post(
            "/clinics/join",
            json={
                "token": invitation["token"],
                "doctor_name": "Colleague",
                "password": "another-valid-password",
            },
        )
        self.assertEqual(joined.status_code, 200, joined.text)
        self.assertEqual(joined.json()["clinic_id"], self.session["clinic_id"])
        self.assertFalse(joined.json()["is_owner"])
        replay = self.client.post(
            "/clinics/join",
            json={
                "token": invitation["token"],
                "doctor_name": "Colleague",
                "password": "another-valid-password",
            },
        )
        self.assertEqual(replay.status_code, 400)

    def test_readiness_reports_missing_models(self):
        with patch("app.main.model_readiness", return_value={"perinatal": False}):
            self.assertEqual(self.client.get("/ready").status_code, 503)


class ReleaseAndDataTests(unittest.TestCase):
    def test_antenatal_training_uses_age_at_pregnancy_start(self):
        from ml.src import antenatal

        source = pd.DataFrame({"p3": [1500], "p20": [9], "v011": [1140]})
        with (
            patch("ml.src.antenatal.build_cohort", return_value=pd.DataFrame({"row": [1]})),
            patch("ml.src.antenatal.load_cohort", return_value=source),
        ):
            result = antenatal.dataset("lbw")
        self.assertEqual(result.maternal_age_at_start.iloc[0], 29)
        self.assertEqual((source.p3.iloc[0] - source.v011.iloc[0]) // 12, 30)

    def test_model_outcome_is_verified(self):
        class Model:
            feature_names_in_ = np.array(["maternal_age"])

        bundle = {
            "format_version": FORMAT_VERSION,
            "cohort": "lbw",
            "target": "low_birth_weight",
            "calibration": "sigmoid_grouped_oof",
            "contract_hash": contract_hash("lbw"),
            "model": Model(),
            "features": ["maternal_age"],
        }
        validate_bundle(bundle, "lbw")
        with self.assertRaisesRegex(ValueError, "outcome"):
            validate_bundle(bundle, "perinatal")

    def test_country_completeness_is_checked(self):
        with self.assertRaisesRegex(ValueError, "expected countries"):
            check_counts(pd.DataFrame({"country": ["Kenya"], "perinatal_death": [0]}), "perinatal")

    def test_partial_cohort_seeding_recovers_missing_tables(self):
        engine = create_engine("sqlite://")
        with engine.begin() as con:
            con.execute(text("CREATE TABLE combined_perinatal (id INTEGER)"))
        with patch("ml.src.dataset.build_cohort", return_value=pd.DataFrame({"id": [1]})) as build:
            seed_cohorts(engine)
        self.assertEqual(build.call_count, 2)
        self.assertEqual(
            set(inspect(engine).get_table_names()),
            {"combined_perinatal", "combined_perinatal_anc", "combined_lbw"},
        )
