"""Regression coverage for model serving and saved assessment compatibility."""

import os
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import numpy as np
import pandas as pd
from fastapi.testclient import TestClient
from sqlalchemy import text

DATABASE = tempfile.TemporaryDirectory()
os.environ["APP_DB_URL"] = f"sqlite:///{DATABASE.name}/app.db"

from app.database import engine, init_db  # noqa: E402
from app.main import app  # noqa: E402
from app.schemas import PredictRequest  # noqa: E402
from app.scoring import (  # noqa: E402
    ModelUnavailable,
    checklist,
    download_model,
    feature_row,
    load_model,
    predict_outcome,
    score,
)

from ml.src.select_models import published_winner  # noqa: E402


class FittedModel:
    feature_names_in_ = np.array(["maternal_age_at_start", "first_pregnancy"])
    release_metadata_ = {"prediction_context": "antenatal_history_v1"}

    def predict_proba(self, frame):
        self.frame = frame
        return np.array([[0.2, 0.8]])


class FormControls(HTMLParser):
    def __init__(self):
        super().__init__()
        self.names = set()

    def handle_starttag(self, tag, attrs):
        name = dict(attrs).get("name")
        if tag in {"input", "select"} and name:
            self.names.add(name)


class PredictionTests(unittest.TestCase):
    def setUp(self):
        self.request = PredictRequest(
            patient_ref="ANC-014",
            age=29,
            age_at_start=29,
            parity=1,
            first_pregnancy=False,
            interval_months=30,
            anc_visits=3,
        )

    def test_patient_reference_is_required_and_trimmed(self):
        body = self.request.model_dump()
        for value in [None, "", "   ", "x" * 61]:
            with self.assertRaises(ValueError):
                PredictRequest(**(body | {"patient_ref": value}))
        del body["patient_ref"]
        with self.assertRaises(ValueError):
            PredictRequest(**body)
        self.assertEqual(
            PredictRequest(**(body | {"patient_ref": " ANC-014 "})).patient_ref, "ANC-014"
        )

    def test_first_pregnancy_and_previous_losses_have_different_features(self):
        first = feature_row(
            PredictRequest(
                patient_ref="ANC-014", age=25, age_at_start=25, parity=0, first_pregnancy=True
            ),
            "perinatal",
        )
        loss = feature_row(
            PredictRequest(
                patient_ref="ANC-014", age=25, age_at_start=25, parity=0, previous_loss=True
            ),
            "perinatal",
        )
        self.assertEqual(first["first_pregnancy"], 1)
        self.assertEqual(loss["first_pregnancy"], 0)
        self.assertEqual(loss["prior_loss"], 1)
        self.assertNotIn("preceding_interval_m", loss)
        self.assertNotIn("no_anc", loss)

    def test_published_selection_honors_best_flag_then_recorded_pr_auc(self):
        rows = [
            {"cohort": "lbw", "algorithm": algorithm, "pr_auc": value, "is_best": False}
            for algorithm, value in [
                ("random_forest", 0.14),
                ("logistic_regression", 0.15),
                ("gradient_boosting", 0.16),
            ]
        ]
        self.assertEqual(published_winner(rows, "lbw")["algorithm"], "gradient_boosting")
        rows[0]["is_best"] = True
        self.assertEqual(published_winner(rows, "lbw")["algorithm"], "random_forest")
        with self.assertRaises(ValueError):
            published_winner(rows[:2], "lbw")

    def test_completed_pregnancy_anc_inputs_do_not_change_antenatal_features(self):
        details = self.request.model_copy(
            update={
                "anc_visits": 8,
                "urine_tested": True,
                "iron_tablets": True,
                "interval_months": 12,
            }
        )
        self.assertEqual(feature_row(self.request, "lbw"), feature_row(details, "lbw"))
        with patch("app.scoring.load_model", return_value=(FittedModel(), 1, "primary")) as load:
            result = score(details)
            self.assertIn("antenatal/perinatal/", load.call_args_list[0].args[0])
            self.assertEqual(result.perinatal.model_id, "primary")

    def test_historical_model_release_is_rejected_for_antenatal_prediction(self):
        model = FittedModel()
        model.release_metadata_ = {"prediction_context": None}
        with patch("app.scoring.load_model", return_value=(model, 1, "historical")):
            with self.assertRaises(ModelUnavailable):
                score(self.request)

    def test_antenatal_checklist_handles_available_history_factors(self):
        self.assertFalse(checklist(self.request).flagged)
        for updates in [
            {"age_at_start": 17},
            {"age_at_start": 35},
            {"parity": 5},
            {"multiple": True},
            {"previous_stillbirth": True},
        ]:
            self.assertTrue(checklist(self.request.model_copy(update=updates)).flagged)
        self.assertFalse(checklist(self.request.model_copy(update={"interval_months": 12})).flagged)

    def test_output_comes_from_model_positive_class_without_heuristic(self):
        model = FittedModel()
        with patch("app.scoring.load_model", return_value=(model, 0, "test:sha")):
            result = score(self.request)
        self.assertEqual(result.perinatal.score, 0.2)
        self.assertEqual(result.lbw.score, 0.2)
        self.assertEqual(list(model.frame.columns), list(model.feature_names_in_))
        self.assertEqual(result.perinatal.model_id, "test:sha")

    def test_secondary_failure_keeps_primary_and_primary_failure_is_explicit(self):
        model = FittedModel()
        with patch(
            "app.scoring.load_model", side_effect=[(model, 1, "test:sha"), FileNotFoundError]
        ):
            self.assertEqual(score(self.request).lbw.status, "unavailable")
        with patch("app.scoring.load_model", side_effect=FileNotFoundError):
            with self.assertRaises(ModelUnavailable):
                score(self.request)

    def test_invalid_model_probabilities_are_rejected(self):
        model = FittedModel()
        model.predict_proba = lambda frame: np.array([[np.nan, 0.8]])
        with patch("app.scoring.load_model", return_value=(model, 1, "test:sha")):
            with self.assertRaises(ModelUnavailable):
                score(self.request)

    def test_unknown_education_is_reported_without_fabricating_value(self):
        model = FittedModel()
        model.feature_names_in_ = np.array(["education"])
        with patch(
            "app.scoring.load_model",
            side_effect=[
                (FittedModel(), 1, "primary"),
                (model, 1, "secondary"),
            ],
        ):
            result = score(self.request)
        self.assertEqual(result.lbw.status, "unavailable")
        self.assertIn("education", result.lbw.message)

    def test_baby_count_and_birth_spacing_are_recorded_without_changing_model_features(self):
        twin = PredictRequest(
            **(
                self.request.model_dump()
                | {"multiple": True, "baby_count": 2, "birth_spacing_months": 18}
            )
        )
        self.assertEqual(twin.baby_count, 2)
        self.assertNotIn("birth_spacing_months", feature_row(twin, "perinatal"))
        self.assertNotIn("baby_count", feature_row(twin, "perinatal"))
        for updates in [
            {"multiple": True, "baby_count": None},
            {"baby_count": 2},
            {"multiple": True, "baby_count": 11},
            {"birth_spacing_months": -1},
        ]:
            with self.assertRaises(ValueError):
                PredictRequest(**(self.request.model_dump() | updates))

    def test_conflicting_history_and_invalid_numeric_inputs_are_rejected(self):
        for updates in [
            {"first_pregnancy": True},
            {"age": 10},
            {"parity": -1},
            {"interval_months": 0},
            {"anc_visits": -1},
            {"age": 25.5},
        ]:
            body = self.request.model_dump() | updates
            with self.assertRaises(ValueError):
                PredictRequest(**body)

    def test_download_checks_digest_before_loading(self):
        class Response:
            url = "https://example.com/model.joblib"

            def __enter__(self):
                self.remaining = b"wrong file"
                return self

            def __exit__(self, *args):
                pass

            def read(self, size):
                content, self.remaining = self.remaining, b""
                return content

        with patch("app.scoring.urllib.request.urlopen", return_value=Response()):
            with self.assertRaisesRegex(ValueError, "checksum"):
                download_model("https://example.com/model.joblib", "0" * 64)

    def test_saved_results_retries_clinic_isolation_and_legacy_history(self):
        with (
            patch("app.main.seed_cohorts"),
            patch(
                "app.scoring.load_model",
                return_value=(
                    FittedModel(),
                    1,
                    "test:sha",
                ),
            ),
            TestClient(app) as client,
        ):
            email = f"{uuid4()}@example.com"
            session = client.post(
                "/clinics/register",
                json={
                    "clinic_name": "Test clinic",
                    "doctor_name": "Doctor",
                    "email": email,
                    "password": "test-password",
                },
            ).json()
            headers = {"Authorization": f"Bearer {session['token']}"}
            body = self.request.model_dump(mode="json") | {"request_id": str(uuid4())}
            self.assertEqual(client.post("/assess", json=body).status_code, 401)
            assessed = client.post("/assess", json=body, headers=headers)
            self.assertEqual(assessed.status_code, 200)
            body["assessment_token"] = assessed.json()["assessment_token"]
            saved = client.post("/predict", json=body, headers=headers)
            self.assertEqual(saved.status_code, 200, saved.text)
            duplicate = client.post("/predict", json=body, headers=headers)
            self.assertEqual(saved.json()["id"], duplicate.json()["id"])
            conflict = client.post("/predict", json=body | {"age": 30}, headers=headers)
            self.assertEqual(conflict.status_code, 409)
            self.assertEqual(
                saved.json()["assessment"], assessed.json() | {"assessment_token": None}
            )
            self.assertEqual(saved.json()["risk_band"], "unclassified")
            with engine.begin() as con:
                con.execute(
                    text("UPDATE predictions SET assessment = NULL WHERE id = :id"),
                    {"id": saved.json()["id"]},
                )
            rows = client.get("/history", headers=headers).json()
            self.assertIsNone(rows[0]["assessment"])
            other = client.post(
                "/clinics/register",
                json={
                    "clinic_name": "Other clinic",
                    "doctor_name": "Doctor",
                    "email": f"{uuid4()}@example.com",
                    "password": "test-password",
                },
            ).json()
            other_headers = {"Authorization": f"Bearer {other['token']}"}
            self.assertEqual(client.get("/history", headers=other_headers).json(), [])

    def test_legacy_baby_count_backfill_does_not_guess_multiple_counts(self):
        from app import database
        from sqlalchemy import create_engine

        legacy = create_engine("sqlite://")
        with legacy.begin() as con:
            con.execute(
                text(
                    "CREATE TABLE predictions (id INTEGER PRIMARY KEY, "
                    "clinic_id INTEGER, risk DOUBLE PRECISION, inputs JSON)"
                )
            )
            for pid, value in [
                (1, '{"multiple": false}'),
                (2, '{"multiple": true}'),
                (3, '{"multiple": true, "baby_count": 3}'),
            ]:
                con.execute(
                    text(
                        "INSERT INTO predictions(id,clinic_id,risk,inputs) "
                        "VALUES (:id,1,0.1,:inputs)"
                    ),
                    {"id": pid, "inputs": value},
                )
        with patch.object(database, "engine", legacy):
            database.init_db()
            database.init_db()
        with legacy.connect() as con:
            result = con.execute(
                text("SELECT id,baby_count,pregnancy_id FROM predictions ORDER BY id")
            ).all()
            self.assertEqual([tuple(row) for row in result], [(1, 1, 1), (2, None, 2), (3, 3, 3)])
        legacy.dispose()

    def test_existing_database_upgrade_is_repeatable(self):
        init_db()
        init_db()
        with engine.connect() as con:
            con.execute(text("SELECT assessment, request_id FROM predictions LIMIT 1"))

    def test_selected_exports_match_direct_pipeline_predictions(self):
        root = Path(__file__).resolve().parents[2]
        for cohort in ["perinatal", "perinatal_anc", "lbw"]:
            path = root / "ml" / "models" / "antenatal" / cohort / "selected.joblib"
            if not path.exists():
                self.skipTest("Run python -m ml.src.select_models to export selected models.")
            model, index, model_id = load_model(str(path), cohort)
            request = self.request.model_copy(
                update={
                    "education": "Primary",
                    "urine_tested": True if cohort == "perinatal_anc" else None,
                    "iron_tablets": True if cohort == "perinatal_anc" else None,
                }
            )
            frame = pd.DataFrame([feature_row(request, cohort)], columns=model.feature_names_in_)
            expected = float(model.predict_proba(frame)[0, index])
            actual = predict_outcome(request, cohort)
            self.assertAlmostEqual(actual.score, expected)
            self.assertEqual(actual.model_id, model_id)

    def test_clinical_form_questions_match_selected_model_features(self):
        root = Path(__file__).resolve().parents[2]
        feature_controls = {
            "maternal_age_at_start": {"age"},
            "prior_live_births": {"parity"},
            "first_pregnancy": {"firstPregnancy"},
            "prior_stillbirth": {"previousStillbirth"},
            "prior_loss": {"previousLoss"},
            "multiple": {"multiple"},
            "education": {"education"},
        }
        required_controls = set()
        for cohort in ["perinatal", "perinatal_anc", "lbw"]:
            path = root / "ml" / "models" / "antenatal" / cohort / "selected.joblib"
            if not path.exists():
                self.skipTest("Export the selected models before checking the form contract.")
            model, _, _ = load_model(str(path), cohort)
            for feature in model.feature_names_in_:
                self.assertIn(
                    feature, feature_controls, f"Map the new {cohort} feature to the form."
                )
                required_controls.update(feature_controls[feature])
        parser = FormControls()
        template = (
            root / "frontend/src/app/pages/clinician-dashboard/clinician-dashboard.component.html"
        )
        parser.feed(template.read_text())
        self.assertEqual(
            parser.names - {"patientRef", "babyCount", "birthSpacing"}, required_controls
        )

    def test_assessment_api_matches_the_real_model_files(self):
        root = Path(__file__).resolve().parents[2]
        for cohort in ["perinatal", "perinatal_anc", "lbw"]:
            if not (root / "ml/models/antenatal" / cohort / "selected.joblib").exists():
                self.skipTest("Export the selected models before running this integration check.")
        with patch("app.main.seed_cohorts"), TestClient(app) as client:
            registered = client.post(
                "/clinics/register",
                json={
                    "clinic_name": "Model integration test",
                    "doctor_name": "Test clinician",
                    "email": f"{uuid4()}@example.com",
                    "password": "test66",
                },
            )
            self.assertEqual(registered.status_code, 200, registered.text)
            headers = {"Authorization": f"Bearer {registered.json()['token']}"}
            legacy = self.request.model_dump(mode="json")
            legacy.pop("age_at_start")
            self.assertEqual(client.post("/assess", json=legacy, headers=headers).status_code, 422)
            for with_anc in [False, True]:
                request = self.request.model_copy(
                    update={
                        "education": "Primary",
                        "urine_tested": True if with_anc else None,
                        "iron_tablets": True if with_anc else None,
                    }
                )
                payload = request.model_dump(mode="json")
                payload.pop("age")
                response = client.post("/assess", json=payload, headers=headers)
                self.assertEqual(response.status_code, 200, response.text)
                primary = "perinatal"
                for outcome, cohort in [("perinatal", primary), ("lbw", "lbw")]:
                    path = root / "ml/models/antenatal" / cohort / "selected.joblib"
                    model, index, identifier = load_model(str(path), cohort)
                    frame = pd.DataFrame(
                        [feature_row(request, cohort)], columns=model.feature_names_in_
                    )
                    expected = float(model.predict_proba(frame)[0, index])
                    actual = response.json()[outcome]
                    self.assertEqual(actual["status"], "available")
                    self.assertAlmostEqual(actual["score"], expected)
                    self.assertEqual(actual["model_id"], identifier)


if __name__ == "__main__":
    unittest.main()
