"""Tests for the decision rule, error counts and threshold choice (Stage 5)."""
import numpy as np

from src import decision


def test_split_scores():
    classes = ["P01", "P02", "P03"]
    scores = np.array([[0.7, 0.2, 0.1],
                       [0.3, 0.5, 0.2]])
    genuine, false_claims = decision.split_scores(scores, classes, ["P01", "P02"])
    assert genuine.tolist() == [0.7, 0.5]
    assert sorted(false_claims.tolist()) == [0.1, 0.2, 0.2, 0.3]   # 2 per attempt


def test_far_frr_counts():
    genuine = np.array([0.9, 0.6, 0.3])
    false_claims = np.array([0.1, 0.2, 0.4, 0.05])
    assert decision.frr(genuine, 0.5) == {"count": 1, "total": 3, "rate": 1 / 3}
    assert decision.far(false_claims, 0.4)["count"] == 1      # score equal to t is accepted
    assert decision.far(false_claims, 0.41)["count"] == 0


def test_threshold_separates_clean_scores():
    genuine = np.array([0.8, 0.9, 0.7, 0.75])
    false_claims = np.array([0.1, 0.2, 0.05, 0.3, 0.15, 0.1])
    t = decision.choose_threshold(genuine, false_claims)
    assert 0.3 < t <= 0.7
    assert decision.far(false_claims, t)["count"] == 0
    assert decision.frr(genuine, t)["count"] == 0
    assert t == 0.7          # ties go to the highest threshold with zero errors


def test_threshold_balances_errors():
    genuine = np.array([0.2, 0.5, 0.6, 0.8])
    false_claims = np.array([0.1, 0.3, 0.55, 0.05])
    t = decision.choose_threshold(genuine, false_claims)
    a, r = decision.far(false_claims, t)["rate"], decision.frr(genuine, t)["rate"]
    assert a == r == 0.25
