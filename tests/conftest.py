"""Shared Phase 9 replay with runtime checks for estimator/row isolation."""

from pathlib import Path

import pytest
from sklearn.ensemble import RandomForestClassifier

from quality_ml.evaluation.__main__ import analyze
from quality_ml.evaluation.protocol import FEATURES, assert_frozen

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def phase9_run():
    original_fit = RandomForestClassifier.fit
    original_predict = RandomForestClassifier.predict_proba
    trained, fits, predictions = {}, [], []

    def fit(model, X, y, **kwargs):
        assert_frozen(model, X.columns)
        assert tuple(X.columns) == FEATURES
        assert len(X) in (1241, 1242, 1552)
        trained[id(model)] = set(X.index)
        fits.append(len(X))
        return original_fit(model, X, y, **kwargs)

    def predict(model, X, **kwargs):
        assert len(X) in (310, 311)  # No full-training or 389-row holdout inference.
        assert trained[id(model)].isdisjoint(set(X.index))
        predictions.append(len(X))
        return original_predict(model, X, **kwargs)

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(RandomForestClassifier, "fit", fit)
        patch.setattr(RandomForestClassifier, "predict_proba", predict)
        frames, documents, matrix = analyze(ROOT)
    assert sorted(fits) == [1241, 1241, 1242, 1242, 1242, 1552]
    assert len(predictions) > 5
    return frames, documents, matrix
