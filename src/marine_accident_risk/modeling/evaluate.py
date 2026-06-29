"""모델 평가 — OOF 교차검증, 이진 지표, 임계값 표.

격자×시간 셀의 사고 발생 확률을 평가한다. 시간·공간 누수를 막기 위해 group(예: 연도)
기준으로 분할하고, 폴드 밖(out-of-fold) 예측만 모아 지표를 낸다.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.model_selection import GroupKFold


def binary_metrics(y_true: Sequence[int], y_prob: Sequence[float]) -> dict[str, float]:
    """AUC, PR-AUC, Brier 점수."""
    yt = np.asarray(y_true, dtype=float)
    yp = np.asarray(y_prob, dtype=float)
    return {
        "auc": float(roc_auc_score(yt, yp)),
        "pr_auc": float(average_precision_score(yt, yp)),
        "brier": float(brier_score_loss(yt, yp)),
    }


def oof_predict(
    X: pd.DataFrame,
    y: pd.Series,
    groups: Sequence,
    model_factory: Callable[[], Any],
    n_splits: int | None = None,
) -> np.ndarray:
    """group 기준 K겹 교차검증의 out-of-fold 확률을 돌려준다(누수 방지)."""
    g = np.asarray(groups)
    n_groups = int(len(np.unique(g)))
    k = n_groups if n_splits is None else n_splits
    k = max(2, min(k, n_groups))
    xr = X.reset_index(drop=True)
    yr = pd.Series(np.asarray(y)).reset_index(drop=True)
    oof = np.full(len(yr), np.nan)
    for train_idx, test_idx in GroupKFold(n_splits=k).split(xr, yr, g):
        model = model_factory()
        model.fit(xr.iloc[train_idx], yr.iloc[train_idx])
        oof[test_idx] = model.predict_proba(xr.iloc[test_idx])[:, 1]
    return oof


def threshold_table(
    y_true: Sequence[int], y_prob: Sequence[float], thresholds: Sequence[float] | None = None
) -> pd.DataFrame:
    """임계값별 precision·recall·f1·예측 양성 비율 표(순찰 알림 정책 검토용)."""
    yt = np.asarray(y_true, dtype=int)
    yp = np.asarray(y_prob, dtype=float)
    ths = np.round(np.arange(0.05, 1.0, 0.05), 2) if thresholds is None else np.asarray(thresholds, dtype=float)
    positives = int(yt.sum())
    rows = []
    for th in ths:
        pred = (yp >= th).astype(int)
        tp = int(((pred == 1) & (yt == 1)).sum())
        fp = int(((pred == 1) & (yt == 0)).sum())
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / positives if positives > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        rows.append(
            {
                "threshold": float(th),
                "precision": precision,
                "recall": recall,
                "f1": f1,
                "pred_pos_rate": float(pred.mean()),
            }
        )
    return pd.DataFrame(rows)
