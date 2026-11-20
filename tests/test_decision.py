"""Tests for error counts and threshold choice."""
import numpy as np

from src import decision


def test_far_frr_counts():
    genuine = np.array([0.9, 0.6, 0.3])
    impostor = np.array([0.1, 0.2, 0.4, 0.05])
    assert decision.frr(genuine, 0.5) == {"count": 1, "total": 3, "rate": 1 / 3}
    assert decision.far(impostor, 0.4)["count"] == 1      # equal to t is accepted
    assert decision.far(impostor, 0.41)["count"] == 0


def test_threshold_separates_clean_scores():
    genuine = np.array([0.8, 0.9, 0.7, 0.75])
    impostor = np.array([0.1, 0.2, 0.05, 0.3])
    t = decision.choose_threshold(genuine, impostor)
    assert t == 0.7          # zero errors; ties go to the highest such threshold


def test_threshold_balances_errors():
    genuine = np.array([0.2, 0.5, 0.6, 0.8])
    impostor = np.array([0.1, 0.3, 0.55, 0.05])
    t = decision.choose_threshold(genuine, impostor)
    assert decision.far(impostor, t)["rate"] == decision.frr(genuine, t)["rate"] == 0.25
