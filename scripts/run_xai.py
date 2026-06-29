"""XAI 실행 — 어떤 조건이 위험을 끌어올리는지 설명한다.

해석 모델(로지스틱)의 표준화 오즈비(변수 1 표준편차 변화당 사고 오즈 배수)를 신뢰구간과 함께
내고, 순열 중요도(섞었을 때 AUC가 얼마나 떨어지는가)로 변수 기여를 순위화한다.
오즈비는 대시보드의 '모델 기여 요인' 패널 근거로 쓴다.

출력: reports/xai/odds_ratios.{md,json}
실행: uv run python scripts/run_xai.py
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import numpy as np
import pandas as pd
import statsmodels.api as sm
from sklearn.inspection import permutation_importance
from sklearn.preprocessing import StandardScaler

from marine_accident_risk.config import load_settings
from marine_accident_risk.modeling.features import add_time_features, build_xy
from marine_accident_risk.modeling.models import logistic_factory

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "configs" / "default.yaml"
CACHE = ROOT / "data" / "cache"
OUT = ROOT / "reports" / "xai"

WEATHER_CANDIDATES = ["wind_speed", "air_temp", "air_pressure", "humidity", "visibility"]
SPATIAL = ["lat", "lon"]
TIME_NUMERIC = ["hour", "is_night", "month"]
LABELS = {
    "wind_speed": "풍속", "air_temp": "기온", "air_pressure": "기압", "humidity": "습도",
    "visibility": "시정", "lat": "위도", "lon": "경도", "hour": "시각", "is_night": "야간",
    "month": "월", "const": "(상수)",
}


def _label(name: str) -> str:
    if name.startswith("season_"):
        return f"계절:{name.split('_', 1)[1]}"
    return LABELS.get(name, name)


def _select_numeric(df: pd.DataFrame) -> list[str]:
    return [
        c for c in [*WEATHER_CANDIDATES, *SPATIAL, *TIME_NUMERIC]
        if c in df.columns and df[c].notna().mean() > 0.5
    ]


def main() -> None:
    settings = load_settings(CONFIG if CONFIG.exists() else None)
    res = 0.1 if 0.1 in settings.grid_resolutions else settings.grid_resolutions[0]
    df = add_time_features(pd.read_csv(CACHE / f"dataset_{res}.csv", parse_dates=["occurred_hour"]))
    numeric = _select_numeric(df)
    x, y, names = build_xy(df, numeric=numeric, categorical=["season"], label_col="label")

    # 수치 특징만 표준화 → 오즈비를 변수 간 비교 가능한 '1 표준편차당' 단위로.
    xs = x.copy()
    xs[numeric] = StandardScaler().fit_transform(xs[numeric])
    # 더미 변수 함정 회피: 계절 one-hot 중 하나를 기준(baseline)으로 빼고 상수와 함께 적합.
    season_cols = [c for c in xs.columns if c.startswith("season_")]
    baseline = _label(season_cols[0]) if season_cols else "기준"
    xr = xs.drop(columns=season_cols[:1]) if season_cols else xs

    odds = []
    try:
        model = sm.Logit(y.astype(int).to_numpy(), sm.add_constant(xr.astype(float))).fit(disp=0, maxiter=300)
        params = np.asarray(model.params, dtype=float)
        pvals = np.asarray(model.pvalues, dtype=float)
        ci = np.exp(np.asarray(model.conf_int(), dtype=float))  # (n,2), const 먼저
        for i, name in enumerate(["const", *xr.columns]):
            odds.append(
                {
                    "feature": _label(name),
                    "odds_ratio": float(np.exp(params[i])),
                    "ci_low": float(ci[i, 0]),
                    "ci_high": float(ci[i, 1]),
                    "pvalue": float(pvals[i]),
                }
            )
    except Exception as exc:  # 수렴 실패 시 신뢰구간 없이 sklearn 계수로 대체
        clf = logistic_factory().fit(xs, y)
        coef = clf.named_steps["clf"].coef_[0]
        for name, c in zip(xs.columns, coef, strict=True):
            odds.append({"feature": _label(name), "odds_ratio": float(np.exp(c)), "ci_low": None, "ci_high": None, "pvalue": None})
        print(f"(statsmodels 수렴 실패 → sklearn 계수 사용: {type(exc).__name__})")

    # 순열 중요도(로지스틱, AUC 기준)
    clf = logistic_factory().fit(x, y)
    pi = permutation_importance(clf, x, y, scoring="roc_auc", n_repeats=5, random_state=0, n_jobs=2)
    importance = sorted(
        ({"feature": _label(n), "auc_drop": float(m)} for n, m in zip(names, pi.importances_mean, strict=True)),
        key=lambda d: cast(float, d["auc_drop"]),
        reverse=True,
    )

    OUT.mkdir(parents=True, exist_ok=True)
    payload = {"resolution": res, "n": int(len(y)), "odds_ratios": odds, "permutation_importance": importance}
    (OUT / "odds_ratios.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# XAI — 위험을 끌어올리는 조건",
        "",
        f"격자 {res}° 학습셋(표본 {len(y):,})에서 해석 모델의 표준화 오즈비와 순열 중요도를 냈습니다.",
        f"오즈비는 변수 1 표준편차 증가당 사고 오즈 배수(>1이면 위험↑). 계절 오즈비는 {baseline} 대비.",
        "",
        "## 표준화 오즈비 (로지스틱)",
        "",
        "| 변수 | 오즈비 | 95% CI | p |",
        "|---|---|---|---|",
    ]
    ranked = sorted(
        (d for d in odds if d["feature"] != "(상수)"),
        key=lambda d: abs(np.log(cast(float, d["odds_ratio"]))),
        reverse=True,
    )
    for o in ranked:
        ci_txt = f"{o['ci_low']:.2f}~{o['ci_high']:.2f}" if o["ci_low"] is not None else "—"
        p_txt = f"{o['pvalue']:.2e}" if o["pvalue"] is not None else "—"
        lines.append(f"| {o['feature']} | {o['odds_ratio']:.3f} | {ci_txt} | {p_txt} |")
    lines += ["", "## 순열 중요도 (AUC 하락폭)", "", "| 변수 | AUC 하락 |", "|---|---|"]
    for d in importance:
        lines.append(f"| {d['feature']} | {d['auc_drop']:.4f} |")
    lines += ["", "재현: `uv run python scripts/run_xai.py`", ""]
    (OUT / "odds_ratios.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
