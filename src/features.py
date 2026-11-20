"""Feature extraction for password typing.

Every account has its own password, so features are built separately for each
account (target). For a password with n characters and key i with press time
p_i and release time r_i:

    dwell time   D_i = r_i - p_i            n values      (d00, d01, ...)
    flight time  F_i = p_(i+1) - r_i        n - 1 values  (f00, f01, ...)

The feature vector of one attempt is [D_0 ... D_(n-1), F_0 ... F_(n-2)],
so it has 2n - 1 numbers. Flight times are negative when keys overlap; the
sign is kept. The Shift key is not recorded, so "@" counts as one key.

The same function, features_from_keys(), is used for training data and for
login attempts.

Run:  python -m src.features      (add --workspace sim for simulated data)
"""
import argparse

import numpy as np
import pandas as pd

from src import config, users

ID_COLUMNS = ["typist_id", "target_id", "role", "session", "attempt_id"]


def feature_names(n_keys):
    return ([f"d{i:02d}" for i in range(n_keys)]
            + [f"f{i:02d}" for i in range(n_keys - 1)])


def features_from_keys(keys):
    """Feature vector (as a dict) for one attempt. keys: dicts with press_ms, release_ms."""
    press = np.array([k["press_ms"] for k in keys], dtype=float)
    release = np.array([k["release_ms"] for k in keys], dtype=float)
    dwell = release - press
    flight = press[1:] - release[:-1]
    return dict(zip(feature_names(len(keys)), np.concatenate([dwell, flight]).tolist()))


def load_raw(path):
    return pd.read_csv(path, dtype={"typist_id": str, "target_id": str, "role": str})


def build_features(raw, target_id, n_keys):
    """One row per attempt on one account."""
    rows = []
    sub = raw[raw["target_id"] == target_id]
    for ids, group in sub.groupby(ID_COLUMNS, sort=True):
        group = group.sort_values("key_index")
        if list(group["key_index"]) != list(range(n_keys)):
            print(f"Skipping incomplete attempt {dict(zip(ID_COLUMNS, ids))}")
            continue
        row = dict(zip(ID_COLUMNS, ids))
        row.update(features_from_keys(group.to_dict("records")))
        rows.append(row)
    return pd.DataFrame(rows, columns=ID_COLUMNS + feature_names(n_keys))


def build_all(ws):
    raw = load_raw(ws.raw_file)
    return {u["user_id"]: build_features(raw, u["user_id"], u["password_length"])
            for u in users.load_users(ws)}


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    config.add_workspace_argument(parser)
    args = parser.parse_args()
    ws = config.Workspace(args.workspace)
    if not ws.raw_file.exists():
        raise SystemExit(f"No raw data yet: {ws.raw_file}")
    ws.ensure_dirs()
    for user_id, df in build_all(ws).items():
        df.to_csv(ws.features_file(user_id), index=False, float_format="%.2f")
        n = (len(df.columns) - len(ID_COLUMNS))
        counts = df.groupby(["session", "role"]).size().to_dict()
        print(f"{user_id}: {len(df)} attempts, {n} features  {counts}")
    print(f"Wrote feature files to {ws.features_dir}")


if __name__ == "__main__":
    main()
