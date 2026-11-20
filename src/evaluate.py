"""Final evaluation on Session 2. Run this ONCE.

For every account, Session 2 contains 10 attempts by the owner (genuine) and
5 attempts by other people who know the password (impostor). Each attempt is
checked with that account's saved model and the model type's threshold.

Reported per model type, pooled over the 5 accounts and per account,
always with raw counts:
  - FRR: owners rejected                  (out of 50)
  - FAR: impostors accepted               (out of 25)
  - accuracy, precision, recall, F1 for the genuine class, and the 2x2
    confusion matrix

Run:  python -m src.evaluate     (add --workspace sim for simulated data)
"""
import argparse
import json

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import (ConfusionMatrixDisplay, accuracy_score, confusion_matrix,
                             precision_recall_fscore_support)

from src import config, decision
from src.features import ID_COLUMNS
from src.train import MODEL_NAMES, genuine_scores


def fmt(c):
    return f"{c['count']}/{c['total']} ({100 * c['rate']:.1f}%)"


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    config.add_workspace_argument(parser)
    parser.add_argument("--force", action="store_true", help="overwrite existing test results")
    args = parser.parse_args()
    ws = config.Workspace(args.workspace)

    if ws.test_metrics_file.exists() and not args.force:
        raise SystemExit(
            "Test results already exist. The test data should be used only once, after the\n"
            "models and thresholds are final. Use --force only if you have a good reason\n"
            "(and say so in the report).")
    if not ws.thresholds_file.exists():
        raise SystemExit("No trained models: run  python -m src.train first.")
    info = json.loads(ws.thresholds_file.read_text())

    test = {}
    for uid in info["users"]:
        df = pd.read_csv(ws.features_file(uid), dtype={"typist_id": str, "target_id": str,
                                                       "role": str})
        test[uid] = df[df["session"] == 2]
    n_test = sum(len(d) for d in test.values())
    print(f"Session 2 test attempts: {n_test}"
          + (f"  [workspace: {ws.name}]" if ws.name != "main" else ""))
    if n_test == 0:
        raise SystemExit("No Session 2 data yet.")

    results = {}
    for name, label in MODEL_NAMES.items():
        t = info["models"][name]["threshold"]
        y_all, s_all, per_user = [], [], {}
        for uid, df in test.items():
            model = joblib.load(ws.model_file(name, uid))
            y = (df["role"] == "genuine").astype(int).to_numpy()
            s = genuine_scores(model, df.drop(columns=ID_COLUMNS).to_numpy())
            y_all.extend(y)
            s_all.extend(s)
            per_user[uid] = {"frr": decision.frr(s[y == 1], t),
                             "far": decision.far(s[y == 0], t)}
        y_all, s_all = np.array(y_all), np.array(s_all)
        pred = (s_all >= t).astype(int)
        p, r, f1, _ = precision_recall_fscore_support(y_all, pred, pos_label=1,
                                                      average="binary", zero_division=0)
        cm = confusion_matrix(y_all, pred, labels=[1, 0])
        res = {"threshold": t,
               "frr": decision.frr(s_all[y_all == 1], t),
               "far": decision.far(s_all[y_all == 0], t),
               "accuracy": float(accuracy_score(y_all, pred)),
               "correct": int((pred == y_all).sum()), "total": int(len(y_all)),
               "precision_genuine": float(p), "recall_genuine": float(r), "f1_genuine": float(f1),
               "confusion_matrix": {"labels": ["genuine", "impostor"], "matrix": cm.tolist()},
               "per_user": per_user}
        results[name] = res

        disp = ConfusionMatrixDisplay(cm, display_labels=["genuine", "impostor"])
        fig, ax = plt.subplots(figsize=(3.8, 3.4))
        disp.plot(ax=ax, cmap="Blues", colorbar=False)
        ax.set_xticklabels(["accepted", "rejected"])
        ax.set_xlabel("Decision")
        ax.set_ylabel("Actual typist")
        ax.set_title(f"{label}: Session 2", fontsize=10)
        fig.tight_layout()
        fig.savefig(ws.figures_dir / f"test_confusion_{name}.png", dpi=150)
        plt.close(fig)

        print(f"\n{label}  (threshold {t:.2f})")
        print(f"  accuracy   {res['correct']}/{res['total']} ({100 * res['accuracy']:.1f}%)")
        print(f"  precision / recall / F1 (genuine)  {p:.3f} / {r:.3f} / {f1:.3f}")
        print(f"  FRR (owners rejected)     {fmt(res['frr'])}")
        print(f"  FAR (impostors accepted)  {fmt(res['far'])}")
        for uid, pu in per_user.items():
            print(f"    {uid}: FRR {pu['frr']['count']}/{pu['frr']['total']}, "
                  f"FAR {pu['far']['count']}/{pu['far']['total']}")

    ws.test_metrics_file.write_text(json.dumps(
        {"note": "Final test on Session 2. Impostor attempts come from the same people who "
                 "provided impostor attempts in Session 1.",
         "workspace": ws.name, "models": results}, indent=2))
    print(f"\nSaved {ws.test_metrics_file} and confusion matrix figures.")


if __name__ == "__main__":
    main()
