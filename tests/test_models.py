"""Tests for the nearest-neighbour distance scorer."""
import numpy as np
from sklearn.model_selection import GridSearchCV, StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.models import NearestNeighbourScorer


def data():
    rng = np.random.default_rng(0)
    owner = rng.normal(100, 5, (30, 4))
    others = rng.normal(140, 5, (5, 4))
    X = np.vstack([owner, others])
    y = np.array([1] * 30 + [0] * 5)
    return X, y


def test_owner_scores_higher_than_others():
    X, y = data()
    m = NearestNeighbourScorer(n_neighbors=3).fit(X, y)
    s = m.predict_proba(X)[:, 1]
    assert s[y == 1].min() > s[y == 0].max()
    assert np.allclose(m.predict_proba(X).sum(axis=1), 1)


def test_impostor_rows_do_not_change_the_model():
    X, y = data()
    a = NearestNeighbourScorer(3).fit(X, y)
    b = NearestNeighbourScorer(3).fit(X[y == 1], y[y == 1])
    assert np.allclose(a.predict_proba(X), b.predict_proba(X))


def test_works_in_grid_search():
    X, y = data()
    gs = GridSearchCV(Pipeline([("scale", StandardScaler()), ("knn", NearestNeighbourScorer())]),
                      {"knn__n_neighbors": [1, 3]}, scoring="roc_auc",
                      cv=StratifiedKFold(5, shuffle=True, random_state=0))
    gs.fit(X, y)
    assert gs.best_score_ > 0.9
