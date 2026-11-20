"""Feature extraction: raw keystroke timings -> one row of features per attempt.

For key i with press time p_i and release time r_i:
    dwell time          D_i = r_i - p_i
    flight time         F_i = p_(i+1) - r_i      (negative when keys overlap)
    press-to-press      I_i = p_(i+1) - p_i

Set A (primary, 9 features) summarises these values. Standard deviations are
population standard deviations (numpy default, ddof=0).

The same function, features_from_keys(), is used for training data and for
new authentication attempts, so both are processed identically.

Run from the project folder:  python -m src.features
"""
import argparse

import numpy as np
import pandas as pd

from src import config

FEATURE_COLUMNS = [
    "dwell_mean", "dwell_median", "dwell_std",
    "flight_mean", "flight_median", "flight_std",
    "p2p_std", "overlap_ratio", "chars_per_sec",
]
ID_COLUMNS = ["participant_id", "role", "session", "attempt_id"]

N_KEYS = len(config.SENTENCE)
SET_B_COLUMNS = ([f"dwell_{i:02d}" for i in range(N_KEYS)]
                 + [f"flight_{i:02d}" for i in range(N_KEYS - 1)])


def timings(keys):
    """Return dwell, flight and press-to-press arrays for one attempt.

    keys: sequence of dicts (or rows) with press_ms and release_ms, in typing order.
    """
    press = np.array([k["press_ms"] for k in keys], dtype=float)
    release = np.array([k["release_ms"] for k in keys], dtype=float)
    dwell = release - press
    flight = press[1:] - release[:-1]
    p2p = press[1:] - press[:-1]
    return press, release, dwell, flight, p2p


def total_duration_ms(keys):
    """First key press to last key release."""
    press, release, *_ = timings(keys)
    return float(release.max() - press[0])


def features_from_keys(keys):
    """Compute the nine Set A features for one attempt."""
    press, release, dwell, flight, p2p = timings(keys)
    duration_s = (release.max() - press[0]) / 1000.0
    return {
        "dwell_mean": float(np.mean(dwell)),
        "dwell_median": float(np.median(dwell)),
        "dwell_std": float(np.std(dwell)),
        "flight_mean": float(np.mean(flight)),
        "flight_median": float(np.median(flight)),
        "flight_std": float(np.std(flight)),
        "p2p_std": float(np.std(p2p)),
        "overlap_ratio": float(np.mean(flight < 0)),
        "chars_per_sec": float(len(keys) / duration_s),
    }


def set_b_from_keys(keys):
    """Optional Set B: every dwell time and every flight time (85 values)."""
    _, _, dwell, flight, _ = timings(keys)
    out = {f"dwell_{i:02d}": float(d) for i, d in enumerate(dwell)}
    out.update({f"flight_{i:02d}": float(f) for i, f in enumerate(flight)})
    return out


def load_raw(path):
    # keep_default_na=False keeps the space key as " " instead of a missing value.
    return pd.read_csv(path, keep_default_na=False,
                       dtype={"participant_id": str, "role": str, "key": str, "code": str})


def _valid_attempts(raw):
    """Yield (id values, keys) for complete attempts; skip and report broken ones."""
    for ids, group in raw.groupby(ID_COLUMNS, sort=True):
        group = group.sort_values("key_index")
        typed = "".join(group["key"])
        if list(group["key_index"]) != list(range(N_KEYS)) or typed != config.SENTENCE:
            print(f"Skipping incomplete attempt {dict(zip(ID_COLUMNS, ids))}")
            continue
        yield ids, group.to_dict("records")


def build_features(raw, feature_set="A"):
    """One row per attempt: ID columns, total_duration_ms and the chosen features."""
    extract = features_from_keys if feature_set == "A" else set_b_from_keys
    rows = []
    for ids, keys in _valid_attempts(raw):
        row = dict(zip(ID_COLUMNS, ids))
        row["total_duration_ms"] = total_duration_ms(keys)
        row.update(extract(keys))
        rows.append(row)
    columns = ID_COLUMNS + ["total_duration_ms"] + (
        FEATURE_COLUMNS if feature_set == "A" else SET_B_COLUMNS)
    return pd.DataFrame(rows, columns=columns)


def main():
    parser = argparse.ArgumentParser(description="Build the feature CSV from raw keystrokes.")
    parser.add_argument("--set-b", action="store_true",
                        help="also write the optional 85-feature Set B file")
    config.add_workspace_argument(parser)
    args = parser.parse_args()
    ws = config.Workspace(args.workspace)

    if not ws.raw_file.exists():
        raise SystemExit(f"No raw data yet: {ws.raw_file}")
    raw = load_raw(ws.raw_file)

    features = build_features(raw, "A")
    out = ws.features_file
    features.to_csv(out, index=False, float_format="%.4f")
    print(f"Wrote {len(features)} attempts to {out}")
    print(features.groupby(["participant_id", "session"]).size()
          .rename("attempts").to_string())

    if args.set_b:
        set_b = build_features(raw, "B")
        out_b = ws.features_b_file
        set_b.to_csv(out_b, index=False, float_format="%.4f")
        print(f"Wrote Set B ({len(SET_B_COLUMNS)} features) to {out_b}")


if __name__ == "__main__":
    main()
