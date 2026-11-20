"""Feature extraction test with a hand-worked example.

    key   press   release   dwell
    0         0        80      80
    1       100       200     100
    2       150       260     110
    flight: 100 - 80 = 20,  150 - 200 = -50 (overlap)

    feature vector [d00, d01, d02, f00, f01] = [80, 100, 110, 20, -50]
"""
import pandas as pd

from src.features import build_features, feature_names, features_from_keys

EXAMPLE = [{"press_ms": 0.0, "release_ms": 80.0},
           {"press_ms": 100.0, "release_ms": 200.0},
           {"press_ms": 150.0, "release_ms": 260.0}]


def test_hand_worked_example():
    f = features_from_keys(EXAMPLE)
    assert list(f) == ["d00", "d01", "d02", "f00", "f01"]
    assert list(f.values()) == [80.0, 100.0, 110.0, 20.0, -50.0]


def test_vector_length_is_2n_minus_1():
    assert len(feature_names(9)) == 17
    assert len(feature_names(11)) == 21


def test_build_features_per_account():
    rows = []
    for attempt_id, (typist, role) in enumerate([("U01", "genuine"), ("U02", "impostor")], 1):
        for k, key in enumerate(reversed(EXAMPLE)):          # order in file must not matter
            rows.append({"typist_id": typist, "target_id": "U01", "role": role, "session": 1,
                         "attempt_id": attempt_id, "key_index": 2 - k, **key})
    rows.append({"typist_id": "U02", "target_id": "U02", "role": "genuine", "session": 1,
                 "attempt_id": 3, "key_index": 0, "press_ms": 0.0, "release_ms": 90.0})
    f = build_features(pd.DataFrame(rows), "U01", 3)
    assert len(f) == 2                                         # other accounts ignored
    assert f.iloc[0][["d00", "f01"]].tolist() == [80.0, -50.0]
