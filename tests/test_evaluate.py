import numpy as np
import pandas as pd

from marine_accident_risk.modeling.evaluate import binary_metrics, oof_predict, threshold_table
from marine_accident_risk.modeling.models import logistic_factory


def test_binary_metrics_perfect_separation():
    m = binary_metrics([0, 0, 1, 1], [0.1, 0.2, 0.8, 0.9])
    assert m["auc"] == 1.0
    assert m["pr_auc"] > 0.9
    assert m["brier"] < 0.1


def test_oof_predict_recovers_signal():
    rng = np.random.default_rng(0)
    n = 600
    x = rng.normal(0, 1, n)
    y = (x + rng.normal(0, 0.5, n) > 0).astype(int)
    X = pd.DataFrame({"feat": x})
    groups = np.arange(n) % 3  # 3겹
    oof = oof_predict(X, pd.Series(y), groups, logistic_factory)
    assert not np.isnan(oof).any()  # 모든 행이 한 번씩 폴드 밖 예측됨
    assert binary_metrics(y, oof)["auc"] > 0.8  # 신호 복원


def test_threshold_table_recall_monotone():
    t = threshold_table([0, 0, 1, 1, 1], [0.1, 0.4, 0.5, 0.7, 0.9], thresholds=[0.0, 0.45, 0.6, 0.8, 1.01])
    assert {"threshold", "precision", "recall", "f1"}.issubset(t.columns)
    assert (t["recall"].diff().dropna() <= 1e-9).all()  # 임계값↑ → recall 비증가
    assert t.iloc[0]["recall"] == 1.0  # 임계값 0 → 모두 양성 예측
