"""Stage 5a: train KNN and Random Forest on Session 1 and choose thresholds.

Steps (Session 1 enrolled attempts only; Session 2 and impostors are not read):
  1. Nested cross-validation. The outer 5 folds give each attempt a score from a
     model that never saw it. Inside each outer training part, a 4-fold grid
     search picks the hyperparameters.
  2. The out-of-fold scores give 100 genuine and 400 false-claim scores per
     model. The threshold is set where FAR and FRR are closest.
  3. Each model is tuned and trained again on all of Session 1 and saved.
  4. The demo model is the one with the lower cross-validation error rate.

Run:  python -m src.train            (add --workspace sim for simulated data)
      python -m src.train --shuffle-check   (sanity check with shuffled labels)
"""
import argparse
import json
import warnings

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_recall_fscore_support
from sklearn.model_selection import GridSearchCV, StratifiedKFold
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src import config, decision
from src.features import FEATURE_COLUMNS

SEED = config.RANDOM_SEED

MODEL_NAMES = {"knn": "K-Nearest Neighbors", "rf": "Random Forest"}


def make_model(name):
    """Return (estimator, hyperparameter grid)."""
    if name == "knn":
        # The scaler sits inside the pipeline, so it is fitted on training folds only.
        # k = 1 is left out because it gives only 0/1 scores, which cannot be thresholded.
        est = Pipeline([("scale", StandardScaler()),
                        ("knn", KNeighborsClassifier(weights="distance"))])
        grid = {"knn__n_neighbors": [3, 5, 7, 9]}
    elif name == "rf":
        est = RandomForestClassifier(random_state=SEED)
        grid = {"n_estimators": [100, 300], "max_depth": [None, 5, 10]}
    else:
        raise ValueError(name)
    return est, grid


def grid_search(name, n_splits):
    est, grid = make_model(name)
    cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=SEED)
    return GridSearchCV(clone(est), grid, cv=cv, scoring="accuracy", n_jobs=-1)


def nested_cv(name, X, y, classes):
    """Out-of-fold scores (n_attempts x n_classes) and the chosen parameters per fold."""
    outer = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)
    scores = np.zeros((len(y), len(classes)))
    folds = []
    for k, (train_idx, test_idx) in enumerate(outer.split(X, y), start=1):
        gs = grid_search(name, n_splits=4)
        gs.fit(X[train_idx], y[train_idx])
        assert list(gs.classes_) == classes
        scores[test_idx] = gs.predict_proba(X[test_idx])
        folds.append({"fold": k, "best_params": gs.best_params_,
                      "inner_accuracy": round(float(gs.best_score_), 4)})
    return scores, folds


def classification_metrics(y_true, y_pred):
    p, r, f1, _ = precision_recall_fscore_support(y_true, y_pred, average="macro",
                                                  zero_division=0)
    correct = int(np.sum(np.array(y_true) == np.array(y_pred)))
    return {"accuracy": float(accuracy_score(y_true, y_pred)),
            "correct": correct, "total": int(len(y_true)),
            "precision_macro": float(p), "recall_macro": float(r), "f1_macro": float(f1)}


def plot_curve(curve, threshold, title, path):
    t = [c["threshold"] for c in curve]
    fig, ax = plt.subplots(figsize=(5, 3.4))
    ax.plot(t, [c["far"] for c in curve], label="FAR (false claims accepted)")
    ax.plot(t, [c["frr"] for c in curve], label="FRR (genuine claims rejected)")
    ax.axvline(threshold, color="grey", linestyle="--", linewidth=1)
    ax.text(threshold, 0.95, f" t = {threshold:.2f}", va="top", fontsize=8)
    ax.set_xlabel("Threshold on the claimed-ID score")
    ax.set_ylabel("Rate")
    ax.set_title(title, fontsize=10)
    ax.set_ylim(0, 1)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def load_session1(ws):
    if not ws.features_file.exists():
        raise SystemExit(f"No features yet: run  python -m src.features"
                         + (f" --workspace {ws.name}" if ws.name != "main" else ""))
    df = pd.read_csv(ws.features_file, dtype={"participant_id": str, "role": str})
    train = df[(df["role"] == "enrolled") & (df["session"] == 1)]
    counts = train["participant_id"].value_counts().reindex(config.ENROLLED_IDS, fill_value=0)
    if counts.min() < 5:
        raise SystemExit("Not enough Session 1 data for 5-fold cross-validation:\n"
                         + counts.to_string())
    if counts.min() != counts.max():
        print("Warning: participants have different numbers of attempts:\n" + counts.to_string())
    return train[FEATURE_COLUMNS].to_numpy(), train["participant_id"].to_numpy()


def shuffle_check(X, y, classes):
    rng = np.random.default_rng(SEED)
    y_shuffled = rng.permutation(y)
    print("Shuffled-label check (accuracy should be close to 1/5 = 0.20):")
    for name in MODEL_NAMES:
        scores, _ = nested_cv(name, X, y_shuffled, classes)
        pred = np.array(classes)[scores.argmax(axis=1)]
        print(f"  {name}: {accuracy_score(y_shuffled, pred):.2f}")


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    config.add_workspace_argument(parser)
    parser.add_argument("--shuffle-check", action="store_true",
                        help="run nested CV with shuffled labels instead of training")
    args = parser.parse_args()
    ws = config.Workspace(args.workspace)
    ws.ensure_dirs()
    warnings.filterwarnings("ignore", category=UserWarning)

    X, y = load_session1(ws)
    classes = sorted(config.ENROLLED_IDS)
    print(f"Session 1 training data: {len(y)} attempts, {X.shape[1]} features"
          + (f"  [workspace: {ws.name}]" if ws.name != "main" else ""))

    if args.shuffle_check:
        shuffle_check(X, y, classes)
        return

    cv_report, thresholds = {}, {}
    for name, label in MODEL_NAMES.items():
        print(f"\n{label}: nested cross-validation...")
        scores, folds = nested_cv(name, X, y, classes)
        pred = np.array(classes)[scores.argmax(axis=1)]
        genuine, false_claims = decision.split_scores(scores, classes, y)
        t = decision.choose_threshold(genuine, false_claims)
        curve = decision.far_frr_curve(genuine, false_claims)
        plot_curve(curve, t, f"{label}: FAR and FRR (Session 1, out-of-fold)",
                   ws.figures_dir / f"cv_far_frr_{name}.png")

        result = {
            "classification": classification_metrics(y, pred),
            "threshold": t,
            "frr": decision.frr(genuine, t),
            "far_enrolled_false_claims": decision.far(false_claims, t),
            "folds": folds,
        }
        result["error_rate"] = (result["frr"]["rate"]
                                + result["far_enrolled_false_claims"]["rate"]) / 2
        cv_report[name] = result

        print(f"  accuracy {result['classification']['correct']}/{len(y)}"
              f" | threshold {t:.2f}"
              f" | FRR {result['frr']['count']}/{result['frr']['total']}"
              f" | FAR {result['far_enrolled_false_claims']['count']}"
              f"/{result['far_enrolled_false_claims']['total']}")

        # Final model: tune and fit on all of Session 1.
        final = grid_search(name, n_splits=5)
        final.fit(X, y)
        joblib.dump(final.best_estimator_, ws.model_file(name))
        thresholds[name] = {"threshold": t, "best_params": final.best_params_}
        print(f"  final model saved with {final.best_params_}")

    demo = min(cv_report, key=lambda n: (cv_report[n]["error_rate"],
                                         -cv_report[n]["classification"]["accuracy"]))
    info = {"models": thresholds, "demo_model": demo, "classes": classes,
            "features": FEATURE_COLUMNS, "workspace": ws.name}
    ws.thresholds_file.write_text(json.dumps(info, indent=2))
    ws.cv_metrics_file.write_text(json.dumps(
        {"note": "Nested cross-validation on Session 1 only.", "models": cv_report,
         "demo_model": demo}, indent=2))
    print(f"\nDemo model (lower cross-validation error): {MODEL_NAMES[demo]}")
    print(f"Saved models and thresholds to {ws.models_dir}")
    print(f"Saved CV metrics and figures to {ws.reports_dir}")


if __name__ == "__main__":
    main()
