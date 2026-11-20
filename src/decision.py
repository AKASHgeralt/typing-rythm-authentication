"""Decision rule, error counts and threshold selection.

Each account has its own models. A model gives a login attempt a "genuine
score" between 0 and 1 (from predict_proba): how much the typing looks like
the account owner. The rhythm check passes when the score is at least the
model's threshold t. Scores are treated as scores, not calibrated probabilities.
"""
import numpy as np

THRESHOLD_GRID = np.round(np.arange(0.0, 1.0001, 0.01), 2)


def count(values, condition):
    n = int(np.sum(condition))
    return {"count": n, "total": int(len(values)),
            "rate": float(n / len(values)) if len(values) else float("nan")}


def frr(genuine, t):
    """Genuine attempts rejected (score below t)."""
    genuine = np.asarray(genuine)
    return count(genuine, genuine < t)


def far(impostor, t):
    """Impostor attempts accepted (score at or above t)."""
    impostor = np.asarray(impostor)
    return count(impostor, impostor >= t)


def far_frr_curve(genuine, impostor, grid=THRESHOLD_GRID):
    return [{"threshold": float(t), "far": far(impostor, t)["rate"],
             "frr": frr(genuine, t)["rate"]} for t in grid]


def choose_threshold(genuine, impostor, grid=THRESHOLD_GRID):
    """Threshold where FAR and FRR are closest (approximate equal error rate).

    Ties are broken by the lower total error, then by the higher threshold.
    """
    best_key, best_t = None, None
    for t in grid:
        a, r = far(impostor, t)["rate"], frr(genuine, t)["rate"]
        key = (abs(a - r), a + r, -t)
        if best_key is None or key < best_key:
            best_key, best_t = key, float(t)
    return best_t
