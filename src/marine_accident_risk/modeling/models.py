"""모델 팩토리 — 폴드마다 새 추정기를 만든다(상태 누수 방지).

해석 모델인 로지스틱 회귀를 기본 추정기로 둔다. 성능 상한 비교용 LightGBM은
같은 인터페이스(fit/predict_proba)로 run_model.py에서 함께 평가한다.
"""

from __future__ import annotations

from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


def logistic_factory() -> Pipeline:
    """표준화 + 로지스틱 회귀(클래스 불균형 보정) 파이프라인을 새로 만든다."""
    return Pipeline(
        [
            ("scale", StandardScaler()),
            ("clf", LogisticRegression(max_iter=1000, class_weight="balanced")),
        ]
    )
