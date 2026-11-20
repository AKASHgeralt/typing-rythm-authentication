"""Authentication decision rule, error rates and threshold selection.

Decision rule: a claim "I am participant c" is accepted when the model's score
for c is at least the model's threshold t. The scores come from predict_proba;
they are treated as scores, not as calibrated probabilities.

When t is above 0.5, an accepted claimed ID is always the model's top
prediction, because the five scores add up to 1.
"""
import numpy as np

THRESHOLD_GRID = np.round(np.arange(0.0, 1.0001, 0.01), 2)


def split_scores(scores, classes, true_ids):
    """Split a score matrix into genuine scores and false-claim scores.

    scores:   (n_attempts, n_classes) array from predict_proba
    classes:  class labels in column order
    true_ids: the real participant of each attempt

    Every attempt gives one genuine score (its own ID) and n_classes - 1
    false-claim scores (every other ID). The false-claim scores of one attempt
    come from the same typing, so they are not independent samples.
    """
    classes = list(classes)
    genuine, false_claims = [], []
    for row, true_id in zip(scores, true_ids):
        for j, c in enumerate(classes):
            (genuine if c == true_id else false_claims).append(row[j])
    return np.array(genuine), np.array(false_claims)


def count(values, condition):
    n = int(np.sum(condition))
    return {"count": n, "total": int(len(values)),
            "rate": float(n / len(values)) if len(values) else float("nan")}


def frr(genuine, t):
    """Genuine claims that are rejected (score below t)."""
    return count(genuine, genuine < t)


def far(false_claims, t):
    """False claims that are accepted (score at or above t)."""
    return count(false_claims, false_claims >= t)


def far_frr_curve(genuine, false_claims, grid=THRESHOLD_GRID):
    return [{"threshold": float(t),
             "far": far(false_claims, t)["rate"],
             "frr": frr(genuine, t)["rate"]} for t in grid]


def choose_threshold(genuine, false_claims, grid=THRESHOLD_GRID):
    """Threshold where FAR and FRR are closest (approximate equal error rate).

    Ties are broken by the lower total error, then by the higher threshold.
    """
    best_key, best_t = None, None
    for t in grid:
        a, r = far(false_claims, t)["rate"], frr(genuine, t)["rate"]
        key = (abs(a - r), a + r, -t)
        if best_key is None or key < best_key:
            best_key, best_t = key, float(t)
    return best_t
