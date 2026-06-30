"""시간층화 case-crossover — 조건부 로지스틱 회귀.

각 사고를 그 위치의 최근접 관측 지점에 묶고, 사고가 난 시각(case)을 **같은 달·같은
요일·같은 시각의 다른 날들**(control)과 한 묶음(stratum)으로 본다. 묶음 안에서 조건부
로지스틱 회귀로 기상 1표준편차 증가당 사고 오즈비를 추정한다. 위치·계절·요일·시각은
묶음이 통제하므로, 조업이 몰리는 시간대나 계절 추세가 결과에 섞이지 않는다.

설계 근거: 사고 전 한 시점만 대조로 쓰는 단방향 방식은 시간 추세에 치우칠 수 있어
(Janes 2005), 같은 달 안에서 같은 요일을 대조로 잡는 시간층화 방식을 따랐다
(Lumley & Levy 2000). 짝지은 비교(짝 t·Wilcoxon)는 효과의 방향만 보지만, 조건부
로지스틱은 묶음을 통제한 오즈비와 신뢰구간을 직접 준다.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from statsmodels.discrete.conditional_models import ConditionalLogit

# 사고 유형군(사고종류 기준): 해상상태·항행에 민감한 유형 vs 설비 고장 등 비기상 유형.
WEATHER_SENSITIVE: tuple[str, ...] = ("충돌", "좌초", "전복", "접촉", "침몰", "침수")
MECHANICAL: tuple[str, ...] = ("기관손상", "부유물감김", "추진축계손상", "조타장치손상", "운항저해")

MIN_STRATA = 50  # 조건부 로지스틱을 돌릴 최소 묶음 수.


@dataclass
class ORResult:
    variable: str
    odds_ratio: float       # 1표준편차 증가당 사고 오즈 배수(>1이면 위험↑).
    ci_low: float
    ci_high: float
    pvalue: float
    n_strata: int           # 추정에 쓰인 묶음(=사고) 수.


def time_stratified_referents(occurred_at: pd.Series) -> pd.DataFrame:
    """사고 시각마다 같은 달·같은 요일·같은 시각의 다른 날들을 대조 시각으로 만든다.

    입력 인덱스를 case_id로 보고, [case_id, occurred_at](대조 시각만)을 돌려준다.
    그 달에 같은 요일이 사고일 하루뿐이면 대조가 없어 그 사고는 빠진다.
    """
    ot = pd.to_datetime(occurred_at)
    rows: list[tuple[object, pd.Timestamp]] = []
    for cid, t in ot.items():
        if pd.isna(t):
            continue
        first = pd.Timestamp(t.year, t.month, 1)
        last = first + pd.offsets.MonthEnd(0)
        for d in pd.date_range(first, last, freq="D"):
            if d.weekday() == t.weekday() and d.date() != t.date():
                rows.append((cid, pd.Timestamp(d.year, d.month, d.day, t.hour, t.minute)))
    return pd.DataFrame(rows, columns=["case_id", "occurred_at"])


def standardize(long: pd.DataFrame, variables: list[str]) -> pd.DataFrame:
    """변수들을 전체 표준편차로 표준화한다(per-SD 오즈비 해석·유형군 간 비교를 위해).

    유형군별 추정도 같은 척도로 비교하려면 군을 나누기 전에 전체에서 한 번 표준화한다.
    """
    out = long.copy()
    for v in variables:
        col = out[v].astype(float)
        sd = float(col.std(ddof=0))
        out[v] = (col - col.mean()) / sd if sd > 0 else 0.0
    return out


def _informative(d: pd.DataFrame, group: str, case: str) -> pd.DataFrame:
    """case와 대조가 모두 있는 묶음만 남긴다(한쪽만 있으면 조건부 우도에 기여하지 않음)."""
    g = d.groupby(group)[case].agg(["sum", "count"])
    keep = g[(g["sum"] >= 1) & (g["count"] > g["sum"])].index
    return d[d[group].isin(keep)]


def _fit(
    y: pd.Series, x: pd.DataFrame, groups: pd.Series
) -> list[tuple[float, float, float]] | None:
    """조건부 로지스틱을 적합해 (계수, 표준오차, p)를 변수 순서대로 돌려준다.

    완전 분리 등으로 헤시안 역행렬·표준오차가 안 나오면 None(추정 불가).
    """
    try:
        res = ConditionalLogit(
            y.to_numpy(dtype=float), x.to_numpy(dtype=float), groups=groups.to_numpy()
        ).fit(disp=0)
        coefs = np.asarray(res.params, dtype=float)
        ses = np.asarray(res.bse, dtype=float)
        pvals = np.asarray(res.pvalues, dtype=float)
    except (ValueError, np.linalg.LinAlgError):
        return None
    if not (np.all(np.isfinite(ses)) and np.all(np.isfinite(coefs))):
        return None
    return [(float(coefs[i]), float(ses[i]), float(pvals[i])) for i in range(len(coefs))]


def conditional_logit_or(
    long: pd.DataFrame,
    variable: str,
    *,
    group: str = "case_id",
    case: str = "is_case",
) -> ORResult | None:
    """한 변수의 단변량 조건부 로지스틱 오즈비. 묶음이 너무 적으면 None."""
    d = _informative(long[[group, case, variable]].dropna(), group, case)
    n = int(d[group].nunique())
    if n < MIN_STRATA:
        return None
    fit = _fit(d[case], d[[variable]], d[group])
    if fit is None:
        return None
    coef, se, p = fit[0]
    return ORResult(
        variable, float(np.exp(coef)), float(np.exp(coef - 1.96 * se)),
        float(np.exp(coef + 1.96 * se)), p, n,
    )


def conditional_logit_adjusted(
    long: pd.DataFrame,
    variables: list[str],
    *,
    group: str = "case_id",
    case: str = "is_case",
) -> list[ORResult]:
    """여러 변수를 한 모델에 넣은 다변량(서로 보정한) 조건부 로지스틱 오즈비."""
    d = _informative(long[[group, case, *variables]].dropna(), group, case)
    n = int(d[group].nunique())
    if n < MIN_STRATA:
        return []
    fit = _fit(d[case], d[list(variables)], d[group])
    if fit is None:
        return []
    out = []
    for i, v in enumerate(variables):
        coef, se, p = fit[i]
        out.append(ORResult(
            v, float(np.exp(coef)), float(np.exp(coef - 1.96 * se)),
            float(np.exp(coef + 1.96 * se)), p, n,
        ))
    return out
