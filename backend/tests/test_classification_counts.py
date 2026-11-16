"""Verify confusion-matrix direction, rare-outcome rates and equal-capacity flags."""

import unittest

import numpy as np

from ml.src.compare_classification import classification_counts, flag_top_k


class ClassificationCountTests(unittest.TestCase):
    def test_confusion_matrix_and_rates(self):
        # TP=2, FN=1, FP=1, TN=3: actual outcomes are the reference.
        result = classification_counts([1, 1, 1, 0, 0, 0, 0], [1, 1, 0, 1, 0, 0, 0])
        self.assertEqual([result[k] for k in ["tn", "fp", "fn", "tp"]], [3, 1, 1, 2])
        self.assertAlmostEqual(result["recall"], 2 / 3)
        self.assertAlmostEqual(result["precision"], 2 / 3)
        self.assertAlmostEqual(result["specificity"], 3 / 4)
        self.assertAlmostEqual(result["negative_predictive_value"], 3 / 4)

    def test_no_flags_or_events_do_not_create_false_perfect_rates(self):
        result = classification_counts([0, 0], [0, 0])
        self.assertIsNone(result["recall"])
        self.assertIsNone(result["precision"])
        self.assertIsNone(result["f1"])
        self.assertEqual(result["specificity"], 1)

    def test_equal_capacity_is_exact_and_ties_are_deterministic(self):
        flags = flag_top_k([0.1, 0.8, 0.8, 0.9], 2)
        np.testing.assert_array_equal(flags, [False, True, False, True])
        self.assertEqual(int(flag_top_k([0.1, 0.9], 0).sum()), 0)
        self.assertEqual(int(flag_top_k([0.1, 0.9], 2).sum()), 2)

    def test_invalid_outcomes_scores_and_capacity_are_rejected(self):
        for truth, flags in [([], []), ([1], [1, 0]), ([1, np.nan], [1, 0]), ([2], [0])]:
            with self.subTest(truth=truth):
                with self.assertRaises(ValueError):
                    classification_counts(truth, flags)
        for scores, count in [
            ([0.2, np.nan], 1),
            ([1.1], 1),
            ([0.1], 2),
            ([0.1], -1),
            ([0.1], 0.5),
            ([[0.1]], 1),
        ]:
            with self.subTest(scores=scores, count=count):
                with self.assertRaises(ValueError):
                    flag_top_k(scores, count)
