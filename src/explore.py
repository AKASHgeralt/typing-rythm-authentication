"""Stage 4: box plots of each feature per participant (Session 1), for checking
the data and for the report.

Run:  python -m src.explore     (add --workspace sim for simulated data)
"""
import argparse

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from src import config
from src.features import FEATURE_COLUMNS

LABELS = {
    "dwell_mean": "Mean dwell (ms)", "dwell_median": "Median dwell (ms)",
    "dwell_std": "Std. dwell (ms)", "flight_mean": "Mean flight (ms)",
    "flight_median": "Median flight (ms)", "flight_std": "Std. flight (ms)",
    "p2p_std": "Std. press-to-press (ms)", "overlap_ratio": "Overlap ratio",
    "chars_per_sec": "Characters per second",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    config.add_workspace_argument(parser)
    args = parser.parse_args()
    ws = config.Workspace(args.workspace)
    ws.ensure_dirs()

    df = pd.read_csv(ws.features_file, dtype={"participant_id": str, "role": str})
    print(df.groupby(["role", "participant_id", "session"]).size()
          .rename("attempts").to_string())
    s1 = df[(df["role"] == "enrolled") & (df["session"] == 1)]
    ids = sorted(s1["participant_id"].unique())

    fig, axes = plt.subplots(3, 3, figsize=(10, 8))
    for ax, col in zip(axes.ravel(), FEATURE_COLUMNS):
        ax.boxplot([s1.loc[s1["participant_id"] == p, col] for p in ids])
        ax.set_xticks(range(1, len(ids) + 1), ids)
        ax.set_title(LABELS[col], fontsize=9)
        ax.tick_params(labelsize=8)
    fig.suptitle("Session 1 features by participant", fontsize=11)
    fig.tight_layout()
    out = ws.figures_dir / "features_by_participant.png"
    fig.savefig(out, dpi=150)
    print(f"Saved {out}")


if __name__ == "__main__":
    main()
