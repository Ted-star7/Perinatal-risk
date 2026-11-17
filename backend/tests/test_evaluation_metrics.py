"""The comparison must describe the loaded antenatal models and select by CV."""

import unittest

from app.routers.metrics import evaluation_metrics


class EvaluationMetricsTests(unittest.TestCase):
    def test_loaded_release_cv_drives_selection_instead_of_test_ap(self):
        rows = evaluation_metrics(who={})
        self.assertEqual(len(rows), 9)
        expected = {
            "perinatal": "logistic_regression",
            "lbw": "random_forest",
            "perinatal_anc": "logistic_regression",
        }
        for cohort, algorithm in expected.items():
            group = [row for row in rows if row["cohort"] == cohort]
            selected = [row for row in group if row["is_best"]]
            self.assertEqual([row["algorithm"] for row in selected], [algorithm])
            self.assertEqual(selected[0]["cv_pr_auc"], max(r["cv_pr_auc"] for r in group))
            self.assertEqual(len({r["evaluation_id"] for r in group}), 1)
            self.assertTrue(all(r["prediction_context"] == "antenatal_history_v1" for r in group))
        lbw = [row for row in rows if row["cohort"] == "lbw"]
        self.assertNotEqual(max(lbw, key=lambda r: r["pr_auc"])["algorithm"], expected["lbw"])
