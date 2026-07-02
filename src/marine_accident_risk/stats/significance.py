"""변수별 집단 비교 — 정규성 검정 → 검정 선택 → 효과크기 → BH 보정.

사고 시점 기상이 평소(대조)와 유의하게 다른지를 변수마다 검정한다.
정규면 모수검정(짝 t / Welch), 비정규면 비모수검정(Wilcoxon 짝 / Mann–Whitney U)을 쓰고,
어떤 변수에 어떤 검정을 썼는지·효과크기·표본수를 함께 남긴다. 여러 변수를 동시에
검정하므로 p값은 Benjamini–Hochberg(FDR)로 보정한다.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import stats

NORMALITY_ALPHA = 0.05
NORMALITY_MAX_N = 5000  # scipy shapiro 한계. 초과 표본은 D'Agostino(normaltest)로.


@dataclass
class TestResult:
    variable: str
    test: str          # paired_t | wilcoxon | welch_t | mannwhitney
    statistic: float
    pvalue: float
    effect_size: float
    effect_name: str   # cohen_d | rank_biserial
    n: int
    normal: bool


def _cohen_d_paired(diff: np.ndarray) -> float:
    sd = float(np.std(diff, ddof=1)) if len(diff) > 1 else 0.0
    return float(np.mean(diff) / sd) if sd > 0 else 0.0


def _cohen_d_unpaired(x: np.ndarray, y: np.ndarray) -> float:
    nx, ny = len(x), len(y)
    if nx < 2 or ny < 2:
        return 0.0
    sp = np.sqrt(((nx - 1) * np.var(x, ddof=1) + (ny - 1) * np.var(y, ddof=1)) / (nx + ny - 2))
    return float((np.mean(x) - np.mean(y)) / sp) if sp > 0 else 0.0


def _rank_biserial_signed(diff: np.ndarray) -> float:
    """Wilcoxon 짝 비교의 rank-biserial 효과크기(양수면 case가 큼)."""
    d = diff[diff != 0]
    if len(d) == 0:
        return 0.0
    ranks = stats.rankdata(np.abs(d))
    r_plus = float(ranks[d > 0].sum())
    r_minus = float(ranks[d < 0].sum())
    total = r_plus + r_minus
    return (r_plus - r_minus) / total if total > 0 else 0.0


def is_normal(x: np.ndarray | list, alpha: float = NORMALITY_ALPHA) -> bool:
    """정규성 검정(표본이 크면 D'Agostino, 작으면 Shapiro–Wilk). p>alpha면 정규로 본다."""
    arr = np.asarray(x, dtype=float)
    arr = arr[~np.isnan(arr)]
    if len(arr) < 3:
        return False
    if len(arr) <= NORMALITY_MAX_N:
        p = float(stats.shapiro(arr).pvalue)
    else:
        p = float(stats.normaltest(arr).pvalue)
    return bool(p > alpha)


def compare_paired(variable: str, case: np.ndarray | list, control: np.ndarray | list) -> TestResult:
    """짝지은 두 표본 비교. 차이가 정규면 짝 t검정(Cohen's d), 아니면 Wilcoxon(rank-biserial)."""
    c = np.asarray(case, dtype=float)
    k = np.asarray(control, dtype=float)
    mask = ~(np.isnan(c) | np.isnan(k))
    c, k = c[mask], k[mask]
    diff = c - k
    n = int(len(diff))
    if is_normal(diff):
        res = stats.ttest_rel(c, k)
        return TestResult(
            variable, "paired_t", float(res.statistic), float(res.pvalue),
            _cohen_d_paired(diff), "cohen_d", n, True,
        )
    res = stats.wilcoxon(c, k)
    return TestResult(
        variable, "wilcoxon", float(res.statistic), float(res.pvalue),
        _rank_biserial_signed(diff), "rank_biserial", n, False,
    )


def compare_unpaired(variable: str, a: np.ndarray | list, b: np.ndarray | list) -> TestResult:
    """짝없는 두 표본 비교. 둘 다 정규면 Welch t(Cohen's d), 아니면 Mann–Whitney U(rank-biserial)."""
    x = np.asarray(a, dtype=float)
    y = np.asarray(b, dtype=float)
    x, y = x[~np.isnan(x)], y[~np.isnan(y)]
    n = int(len(x) + len(y))
    if is_normal(x) and is_normal(y):
        res = stats.ttest_ind(x, y, equal_var=False)
        return TestResult(
            variable, "welch_t", float(res.statistic), float(res.pvalue),
            _cohen_d_unpaired(x, y), "cohen_d", n, True,
        )
    res = stats.mannwhitneyu(x, y, alternative="two-sided")
    u1 = float(res.statistic)
    rb = 2.0 * u1 / (len(x) * len(y)) - 1.0 if len(x) and len(y) else 0.0
    return TestResult(
        variable, "mannwhitney", u1, float(res.pvalue), float(rb), "rank_biserial", n, False,
    )


def benjamini_hochberg(pvalues: np.ndarray | list, alpha: float = 0.05) -> tuple[np.ndarray, np.ndarray]:
    """BH(FDR) 보정. (기각 여부 bool 배열, 보정된 q값 배열)을 돌려준다."""
    p = np.asarray(pvalues, dtype=float)
    q = stats.false_discovery_control(p, method="bh")
    return q <= alpha, q
