"""Count attempts and plot mean dwell and mean flight time per account,
genuine vs impostor (Session 1), for checking the data and for the report.

Run:  python -m src.explore     (add --workspace sim for simulated data)
"""
import argparse

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from src import config, users
from src.features import build_all


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    config.add_workspace_argument(parser)
    args = parser.parse_args()
    ws = config.Workspace(args.workspace)
    ws.ensure_dirs()

    all_users = users.load_users(ws)
    names = {u["user_id"]: u["name"] for u in all_users}
    feats = build_all(ws)

    print("Attempts per account (target), session and role:")
    for uid, df in feats.items():
        print(f"  {uid} ({names[uid]}): " + ", ".join(
            f"S{s} {r}: {n}" for (s, r), n in df.groupby(["session", "role"]).size().items()))

    fig, axes = plt.subplots(2, len(feats), figsize=(2.4 * len(feats), 5.2), squeeze=False)
    for j, (uid, df) in enumerate(feats.items()):
        s1 = df[df["session"] == 1]
        dwell = s1.filter(regex=r"^d\d+$").mean(axis=1)
        flight = s1.filter(regex=r"^f\d+$").mean(axis=1)
        for i, (vals, label) in enumerate([(dwell, "Mean dwell (ms)"), (flight, "Mean flight (ms)")]):
            ax = axes[i][j]
            ax.boxplot([vals[s1["role"] == "genuine"], vals[s1["role"] == "impostor"]])
            ax.set_xticks([1, 2], ["owner", "others"])
            ax.tick_params(labelsize=8)
            if j == 0:
                ax.set_ylabel(label, fontsize=9)
            if i == 0:
                ax.set_title(f"{uid}'s password", fontsize=9)
    fig.suptitle("Session 1: owner vs others typing the same password", fontsize=11)
    fig.tight_layout()
    out = ws.figures_dir / "owner_vs_others.png"
    fig.savefig(out, dpi=150)
    print(f"Saved {out}")


if __name__ == "__main__":
    main()
