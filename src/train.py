"""Train one KNN and one Random Forest per account, and choose thresholds.

For each account (target) the Session 1 data has two classes:
    genuine  (label 1): the owner typing their own password      (30 attempts)
    impostor (label 0): other people typing that password        (5 attempts)
Session 2 is not read here.

Models:
  knn  nearest-neighbour distance to the owner's attempts (src/models.py);
       learns from the owner's attempts only.
  rf   Random Forest classifier, owner vs others, class_weight="balanced".

Steps for each model type:
  1. Nested cross-validation per account. The outer 5 folds give every
     attempt a genuine score from a model that never saw it. Inside each
     outer training part, a 4-fold grid search picks the hyperparameters
     (scoring: ROC AUC, because the classes are unbalanced).
  2. The out-of-fold scores of all accounts are pooled (150 genuine and 25
     impostor scores) and ONE threshold per model type is chosen where FAR
     and FRR are closest. With only 5 impostor attempts per account, a
     separate threshold per account would be too unreliable.
  3. Each account's model is tuned and trained again on all its Session 1
     data and saved.
  4. The demo model type is the one with the lower pooled CV error.

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
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GridSearchCV, StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src import config, decision, users
from src.features import ID_COLUMNS
from src.models import NearestNeighbourScorer

SEED = config.RANDOM_SEED
MODEL_NAMES = {"knn": "K-Nearest Neighbours (distance)", "rf": "Random Forest"}
MIN_IMPOSTOR = 5      # needed for 5 outer folds


def make_model(name):
    """Return (estimator, hyperparameter grid)."""
    if name == "knn":
        # Nearest-neighbour distance to the owner's attempts (see src/models.py).
        # Scaler inside the pipeline: fitted on training folds only.
        est = Pipeline([("scale", StandardScaler()),
                        ("knn", NearestNeighbourScorer())])
        grid = {"knn__n_neighbors": [1, 3, 5]}
    elif name == "rf":
        # class_weight="balanced" because there are 6x more genuine than impostor attempts.
        est = RandomForestClassifier(random_state=SEED, class_weight="balanced")
        grid = {"n_estimators": [100, 300], "max_depth": [None, 5]}
    else:
        raise ValueError(name)
    return est, grid


def grid_search(name, n_splits):
    est, grid = make_model(name)
    cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=SEED)
    return GridSearchCV(clone(est), grid, cv=cv, scoring="roc_auc", n_jobs=-1)


def genuine_scores(model, X):
    """Score of the 'genuine' class (label 1)."""
    return model.predict_proba(X)[:, list(model.classes_).index(1)]


def nested_cv(name, X, y):
    outer = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)
    scores = np.zeros(len(y))
    folds = []
    for k, (tr, te) in enumerate(outer.split(X, y), start=1):
        gs = grid_search(name, n_splits=4)
        gs.fit(X[tr], y[tr])
        scores[te] = genuine_scores(gs, X[te])
        folds.append({"fold": k, "best_params": gs.best_params_})
    return scores, folds


def load_session1(ws, user):
    path = ws.features_file(user["user_id"])
    if not path.exists():
        raise SystemExit(f"No features for {user['user_id']}: run python -m src.features first.")
    df = pd.read_csv(path, dtype={"typist_id": str, "target_id": str, "role": str})
    s1 = df[df["session"] == 1]
    X = s1.drop(columns=ID_COLUMNS).to_numpy()
    y = (s1["role"] == "genuine").astype(int).to_numpy()
    n_gen, n_imp = int(y.sum()), int((1 - y).sum())
    if n_imp < MIN_IMPOSTOR or n_gen < MIN_IMPOSTOR:
        raise SystemExit(f"{user['user_id']}: need at least {MIN_IMPOSTOR} genuine and "
                         f"{MIN_IMPOSTOR} impostor Session 1 attempts (have {n_gen} and {n_imp}).")
    return X, y


def plot_curve(curve, threshold, title, path):
    t = [c["threshold"] for c in curve]
    fig, ax = plt.subplots(figsize=(5, 3.4))
    ax.plot(t, [c["far"] for c in curve], label="FAR (impostors accepted)")
    ax.plot(t, [c["frr"] for c in curve], label="FRR (owners rejected)")
    ax.axvline(threshold, color="grey", linestyle="--", linewidth=1)
    ax.text(threshold, 0.95, f" t = {threshold:.2f}", va="top", fontsize=8)
    ax.set_xlabel("Threshold on the genuine score")
    ax.set_ylabel("Rate")
    ax.set_ylim(0, 1)
    ax.set_title(title, fontsize=10)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


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

    all_users = users.load_users(ws)
    data = {u["user_id"]: load_session1(ws, u) for u in all_users}
    print("Session 1 training data per account (genuine / impostor attempts, features):"
          + (f"  [workspace: {ws.name}]" if ws.name != "main" else ""))
    for uid, (X, y) in data.items():
        print(f"  {uid}: {int(y.sum())} / {int((1 - y).sum())}, {X.shape[1]} features")

    if args.shuffle_check:
        rng = np.random.default_rng(SEED)
        print("\nShuffled-label check (ROC AUC should be close to 0.5):")
        for name in MODEL_NAMES:
            aucs = []
            for uid, (X, y) in data.items():
                y_s = rng.permutation(y)
                s, _ = nested_cv(name, X, y_s)
                aucs.append(roc_auc_score(y_s, s))
            print(f"  {name}: mean AUC {np.mean(aucs):.2f}")
        return

    cv_report, info_models = {}, {}
    for name, label in MODEL_NAMES.items():
        print(f"\n{label}: nested cross-validation per account...")
        all_gen, all_imp, per_user, final_params = [], [], {}, {}
        for uid, (X, y) in data.items():
            scores, folds = nested_cv(name, X, y)
            gen, imp = scores[y == 1], scores[y == 0]
            all_gen.extend(gen)
            all_imp.extend(imp)
            per_user[uid] = {"auc": float(roc_auc_score(y, scores)), "folds": folds,
                             "genuine_scores": gen.round(4).tolist(),
                             "impostor_scores": imp.round(4).tolist()}
        t = decision.choose_threshold(all_gen, all_imp)
        for uid in per_user:
            per_user[uid]["frr"] = decision.frr(per_user[uid]["genuine_scores"], t)
            per_user[uid]["far"] = decision.far(per_user[uid]["impostor_scores"], t)
        result = {"threshold": t,
                  "frr": decision.frr(all_gen, t),
                  "far": decision.far(all_imp, t),
                  "mean_auc": float(np.mean([p["auc"] for p in per_user.values()])),
                  "per_user": per_user}
        result["error_rate"] = (result["frr"]["rate"] + result["far"]["rate"]) / 2
        cv_report[name] = result
        plot_curve(decision.far_frr_curve(all_gen, all_imp), t,
                   f"{label}: FAR and FRR (Session 1, out-of-fold, all accounts)",
                   ws.figures_dir / f"cv_far_frr_{name}.png")
        print(f"  threshold {t:.2f} | FRR {result['frr']['count']}/{result['frr']['total']}"
              f" | FAR {result['far']['count']}/{result['far']['total']}"
              f" | mean AUC {result['mean_auc']:.2f}")

        for uid, (X, y) in data.items():
            final = grid_search(name, n_splits=5)
            final.fit(X, y)
            joblib.dump(final.best_estimator_, ws.model_file(name, uid))
            final_params[uid] = final.best_params_
        info_models[name] = {"threshold": t, "best_params": final_params}
        print(f"  final models saved for {len(data)} accounts")

    demo = min(cv_report, key=lambda n: (cv_report[n]["error_rate"], -cv_report[n]["mean_auc"]))
    ws.thresholds_file.write_text(json.dumps(
        {"models": info_models, "demo_model": demo, "users": list(data),
         "workspace": ws.name}, indent=2))
    ws.cv_metrics_file.write_text(json.dumps(
        {"note": "Nested cross-validation on Session 1 only; scores pooled over accounts.",
         "models": cv_report, "demo_model": demo}, indent=2))
    print(f"\nDemo model (lower cross-validation error): {MODEL_NAMES[demo]}")
    print(f"Saved models to {ws.models_dir} and CV metrics to {ws.reports_dir}")


if __name__ == "__main__":
    main()
