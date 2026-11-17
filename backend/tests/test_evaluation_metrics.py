"""Approved research results replace old metrics once and remain isolated from later submissions."""

import unittest

from app.evaluation import approved_evaluation, install_approved_evaluation
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session


class EvaluationMetricsTests(unittest.TestCase):
    def test_approved_cv_selection_is_persisted_and_old_values_archived(self):
        from app.database import METRICS_DDL

        engine = create_engine("sqlite://")
        with engine.begin() as con:
            for statement in filter(str.strip, METRICS_DDL.split(";")):
                con.execute(text(statement))
            con.execute(
                text(
                    "INSERT INTO model_metrics(cohort,algorithm,pr_auc) "
                    "VALUES ('perinatal','gradient_boosting',0.01)"
                )
            )
            install_approved_evaluation(con)
            install_approved_evaluation(con)
            self.assertEqual(con.scalar(text("SELECT COUNT(*) FROM model_metrics_archive")), 1)
        with Session(engine) as db:
            rows = approved_evaluation(db)
            self.assertEqual(len(rows), 9)
            selected = {r["cohort"]: r["algorithm"] for r in rows if r["is_best"]}
            self.assertEqual(
                selected,
                {
                    "perinatal": "gradient_boosting",
                    "lbw": "gradient_boosting",
                    "perinatal_anc": "logistic_regression",
                },
            )
            for row in rows:
                self.assertEqual(row["prediction_context"], "completed_pregnancy_research")
                group = [r for r in rows if r["cohort"] == row["cohort"]]
                self.assertEqual(
                    row["is_best"], row["cv_pr_auc"] == max(r["cv_pr_auc"] for r in group)
                )
            self.assertAlmostEqual(
                next(r for r in rows if r["cohort"] == "perinatal" and r["is_best"])["cv_pr_auc"],
                0.08159981107834284,
            )
        engine.dispose()
