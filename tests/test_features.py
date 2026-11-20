"""Tests for feature extraction (Stage 3).

Hand-worked example with three keys:

    key   press   release   dwell
    0         0        80      80
    1       100       200     100
    2       150       260     110

    flight:  100 - 80 = 20,   150 - 200 = -50   (key 2 pressed before key 1 released)
    press-to-press:  100, 50

    dwell  mean 96.667, median 100, std sqrt(466.667 / 3) = 12.472
    flight mean -15,    median -15, std 35
    press-to-press std 25
    overlap ratio 1 / 2 = 0.5
    duration 260 ms -> 3 keys / 0.26 s = 11.538 characters per second
"""
import pandas as pd
import pytest

from src import config
from src.features import (FEATURE_COLUMNS, SET_B_COLUMNS, build_features,
                          features_from_keys, set_b_from_keys, total_duration_ms)

EXAMPLE = [
    {"press_ms": 0.0, "release_ms": 80.0},
    {"press_ms": 100.0, "release_ms": 200.0},
    {"press_ms": 150.0, "release_ms": 260.0},
]


def test_hand_worked_example():
    f = features_from_keys(EXAMPLE)
    assert list(f) == FEATURE_COLUMNS
    assert f["dwell_mean"] == pytest.approx(96.6667, abs=1e-3)
    assert f["dwell_median"] == pytest.approx(100.0)
    assert f["dwell_std"] == pytest.approx(12.4722, abs=1e-3)
    assert f["flight_mean"] == pytest.approx(-15.0)
    assert f["flight_median"] == pytest.approx(-15.0)
    assert f["flight_std"] == pytest.approx(35.0)
    assert f["p2p_std"] == pytest.approx(25.0)
    assert f["overlap_ratio"] == pytest.approx(0.5)
    assert f["chars_per_sec"] == pytest.approx(11.5385, abs=1e-3)


def test_duration_uses_latest_release():
    keys = [{"press_ms": 0.0, "release_ms": 300.0},   # held past the last key
            {"press_ms": 100.0, "release_ms": 200.0}]
    assert total_duration_ms(keys) == 300.0


def test_set_b_values():
    b = set_b_from_keys(EXAMPLE)
    assert [b["dwell_00"], b["dwell_01"], b["dwell_02"]] == [80.0, 100.0, 110.0]
    assert [b["flight_00"], b["flight_01"]] == [20.0, -50.0]


def raw_attempt(attempt_id, pid="P01", session=1, shuffle=False):
    rows = []
    for i, ch in enumerate(config.SENTENCE):
        rows.append({"participant_id": pid, "role": "enrolled", "session": session,
                     "attempt_id": attempt_id, "key_index": i, "key": ch,
                     "code": "Space" if ch == " " else "Key" + ch.upper(),
                     "press_ms": i * 150.0, "release_ms": i * 150.0 + 100.0})
    if shuffle:
        rows.reverse()
    return rows


def test_build_features_one_row_per_attempt():
    raw = pd.DataFrame(raw_attempt(1) + raw_attempt(2, "P02", shuffle=True))
    f = build_features(raw)
    assert len(f) == 2
    assert list(f.columns) == ["participant_id", "role", "session", "attempt_id",
                               "total_duration_ms"] + FEATURE_COLUMNS
    # Row order in the file must not matter.
    assert f.iloc[0][FEATURE_COLUMNS].tolist() == f.iloc[1][FEATURE_COLUMNS].tolist()
    assert f.iloc[0]["dwell_mean"] == 100.0
    assert f.iloc[0]["flight_mean"] == 50.0
    assert f.iloc[0]["overlap_ratio"] == 0.0
    assert f.iloc[0]["total_duration_ms"] == 42 * 150.0 + 100.0


def test_incomplete_attempt_is_skipped():
    broken = raw_attempt(2)[:-1]
    raw = pd.DataFrame(raw_attempt(1) + broken)
    f = build_features(raw)
    assert f["attempt_id"].tolist() == [1]


def test_set_b_has_85_columns():
    f = build_features(pd.DataFrame(raw_attempt(1)), "B")
    assert len(SET_B_COLUMNS) == 85
    assert list(f.columns[5:]) == SET_B_COLUMNS
