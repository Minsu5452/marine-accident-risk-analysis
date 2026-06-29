"""모델 입력 특징 구성 — 시간 파생 + 특징 행렬 조립."""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

_SEASON = {
    12: "겨울", 1: "겨울", 2: "겨울",
    3: "봄", 4: "봄", 5: "봄",
    6: "여름", 7: "여름", 8: "여름",
    9: "가을", 10: "가을", 11: "가을",
}


def add_time_features(df: pd.DataFrame, time_col: str = "occurred_hour") -> pd.DataFrame:
    """occurred_hour에서 month·hour·dow·is_night·season을 파생한다.

    is_night = 20시~06시(야간), season = 월 기반 사계절(봄/여름/가을/겨울).
    """
    t = pd.to_datetime(df[time_col])
    out = df.copy()
    out["month"] = t.dt.month
    out["hour"] = t.dt.hour
    out["dow"] = t.dt.dayofweek
    out["is_night"] = ((t.dt.hour >= 20) | (t.dt.hour < 6)).astype(int)
    out["season"] = t.dt.month.map(_SEASON)
    return out


def build_xy(
    df: pd.DataFrame,
    *,
    numeric: Sequence[str],
    categorical: Sequence[str] = (),
    label_col: str = "label",
) -> tuple[pd.DataFrame, pd.Series, list[str]]:
    """결측 없는 행으로 (X, y, feature_names)를 만든다. categorical은 one-hot 인코딩한다."""
    num = list(numeric)
    cat = list(categorical)
    sub = df.dropna(subset=[*num, label_col]).reset_index(drop=True)
    parts = [sub[num].astype(float)]
    if cat:
        parts.append(pd.get_dummies(sub[cat].astype(str), prefix=cat).astype(int))
    x = pd.concat(parts, axis=1)
    y = sub[label_col].astype(int).reset_index(drop=True)
    return x, y, list(x.columns)
