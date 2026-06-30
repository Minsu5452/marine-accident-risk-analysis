import numpy as np
import pandas as pd

from marine_accident_risk.stats.conditional import (
    conditional_logit_adjusted,
    conditional_logit_or,
    standardize,
    time_stratified_referents,
)


def test_referents_same_month_weekday_hour_excluding_case():
    # 2024-01-17은 수요일 09:00. 같은 1월의 다른 수요일(3·10·24·31일)이 대조여야 한다.
    s = pd.Series([pd.Timestamp(2024, 1, 17, 9, 0)])
    ref = time_stratified_referents(s)
    assert sorted(ref["occurred_at"].dt.day.tolist()) == [3, 10, 24, 31]
    assert (ref["occurred_at"].dt.hour == 9).all()
    assert (ref["occurred_at"].dt.weekday == 2).all()  # 수요일
    assert (ref["case_id"] == 0).all()


def test_referents_skip_nat():
    assert time_stratified_referents(pd.Series([pd.NaT])).empty


def _strata(n: int, effect: float, *, n_ctrl: int = 3, seed: int = 0) -> pd.DataFrame:
    """묶음마다 case 1건 + 대조 n_ctrl건. case 노출은 N(effect,1), 대조는 N(0,1).

    겹침이 있는 정규 노출이라 완전 분리가 생기지 않아 최대우도가 수렴한다.
    """
    rng = np.random.default_rng(seed)
    rows = []
    for cid in range(n):
        rows.append((cid, 1, float(rng.normal(effect, 1.0))))
        for _ in range(n_ctrl):
            rows.append((cid, 0, float(rng.normal(0.0, 1.0))))
    return pd.DataFrame(rows, columns=["case_id", "is_case", "x"])


def test_conditional_logit_detects_positive_association():
    # case 노출이 평균적으로 높으면(effect>0) OR>1·신뢰구간 하한>1·유의.
    r = conditional_logit_or(_strata(300, effect=0.8), "x")
    assert r is not None
    assert r.odds_ratio > 1.0
    assert r.ci_low > 1.0
    assert r.pvalue < 0.01
    assert r.n_strata == 300


def test_conditional_logit_null_when_no_effect():
    # 차이가 없으면(effect=0) 신뢰구간이 1을 포함한다.
    r = conditional_logit_or(_strata(300, effect=0.0), "x")
    assert r is not None
    assert r.ci_low < 1.0 < r.ci_high


def test_conditional_logit_returns_none_below_min_strata():
    assert conditional_logit_or(_strata(10, effect=0.8), "x") is None


def test_adjusted_returns_one_row_per_variable_with_signal_on_first():
    long = _strata(300, effect=0.8, seed=1).rename(columns={"x": "a"})
    rng = np.random.default_rng(2)
    long["b"] = rng.normal(0.0, 1.0, len(long))  # 신호 없는 변수
    out = conditional_logit_adjusted(long, ["a", "b"])
    assert [r.variable for r in out] == ["a", "b"]
    by = {r.variable: r for r in out}
    assert by["a"].odds_ratio > 1.0 and by["a"].pvalue < 0.01
    assert by["b"].ci_low < 1.0 < by["b"].ci_high


def test_standardize_zero_mean_unit_sd():
    out = standardize(pd.DataFrame({"x": [1.0, 2.0, 3.0, 4.0, 5.0]}), ["x"])
    assert abs(float(out["x"].mean())) < 1e-9
    assert abs(float(out["x"].std(ddof=0)) - 1.0) < 1e-9
