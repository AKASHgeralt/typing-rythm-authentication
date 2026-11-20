"""Stage 5b: final evaluation on held-out data. Run this ONCE.

Test data:
  - Session 2 attempts of the 5 enrolled participants (50 attempts)
  - Attempts by the 2 external impostors (20 attempts)

Reported for each model, always with raw counts:
  - accuracy, macro precision/recall/F1 and the confusion matrix (Session 2)
  - FRR:  Session 2 attempts claimed as their own ID           (50 decisions)
  - FAR, enrolled false claims: Session 2 attempts claimed as
    each of the other four IDs                                  (200 decisions from 50 attempts)
  - FAR, external impostors: impostor attempts claimed as
    each enrolled ID                                            (100 decisions from 20 attempts)
  - impostor attempts accepted for at least one ID              (out of 20)

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
from sklearn.metrics import ConfusionMatrixDisplay, confusion_matrix

from src import config, decision
from src.features import FEATURE_COLUMNS
from src.train import MODEL_NAMES, classification_metrics


def fmt(c):
    return f"{c['count']}/{c['total']} ({100 * c['rate']:.1f}%)"


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    config.add_workspace_argument(parser)
    parser.add_argument("--force", action="store_true",
                        help="overwrite existing test results")
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
    classes = info["classes"]
    df = pd.read_csv(ws.features_file, dtype={"participant_id": str, "role": str})
    s2 = df[(df["role"] == "enrolled") & (df["session"] == 2)]
    imp = df[df["role"] == "impostor"]
    print(f"Test data: {len(s2)} Session 2 attempts, {len(imp)} impostor attempts"
          + (f"  [workspace: {ws.name}]" if ws.name != "main" else ""))
    if len(s2) == 0:
        raise SystemExit("No Session 2 data yet.")

    results = {}
    for name, label in MODEL_NAMES.items():
        model = joblib.load(ws.model_file(name))
        t = info["models"][name]["threshold"]
        assert list(model.classes_) == classes

        scores = model.predict_proba(s2[FEATURE_COLUMNS].to_numpy())
        y = s2["participant_id"].to_numpy()
        pred = np.array(classes)[scores.argmax(axis=1)]
        genuine, false_claims = decision.split_scores(scores, classes, y)

        r = {"threshold": t,
             "classification": classification_metrics(y, pred),
             "confusion_matrix": {"labels": classes,
                                  "matrix": confusion_matrix(y, pred, labels=classes).tolist()},
             "frr": decision.frr(genuine, t),
             "far_enrolled_false_claims": decision.far(false_claims, t)}

        if len(imp):
            imp_scores = model.predict_proba(imp[FEATURE_COLUMNS].to_numpy())
            r["far_external_impostors"] = decision.far(imp_scores.ravel(), t)
            accepted_any = (imp_scores >= t).any(axis=1)
            r["impostor_attempts_accepted_any_id"] = decision.count(accepted_any, accepted_any)
        results[name] = r

        disp = ConfusionMatrixDisplay(np.array(r["confusion_matrix"]["matrix"]),
                                      display_labels=classes)
        fig, ax = plt.subplots(figsize=(4.2, 3.8))
        disp.plot(ax=ax, cmap="Blues", colorbar=False)
        ax.set_title(f"{label}: Session 2", fontsize=10)
        fig.tight_layout()
        fig.savefig(ws.figures_dir / f"test_confusion_{name}.png", dpi=150)
        plt.close(fig)

        c = r["classification"]
        print(f"\n{label}  (threshold {t:.2f})")
        print(f"  accuracy        {c['correct']}/{c['total']} ({100 * c['accuracy']:.1f}%)")
        print(f"  macro P / R / F1  {c['precision_macro']:.3f} / {c['recall_macro']:.3f}"
              f" / {c['f1_macro']:.3f}")
        print(f"  FRR             {fmt(r['frr'])}")
        print(f"  FAR enrolled    {fmt(r['far_enrolled_false_claims'])}")
        if len(imp):
            print(f"  FAR external    {fmt(r['far_external_impostors'])}")
            print(f"  impostor attempts accepted for any ID: "
                  f"{fmt(r['impostor_attempts_accepted_any_id'])}")

    ws.test_metrics_file.write_text(json.dumps(
        {"note": "Final test on Session 2 and external impostors. Each false-claim "
                 "decision comes from an attempt that is also used for other claims, "
                 "so the decisions are not independent.",
         "workspace": ws.name, "models": results}, indent=2))
    print(f"\nSaved {ws.test_metrics_file} and confusion matrix figures.")


if __name__ == "__main__":
    main()
