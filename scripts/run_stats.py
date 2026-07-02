"""case-crossover 통계 분석 — 시간층화 대조 + 조건부 로지스틱 회귀.

각 사고를 그 위치의 최근접 관측 지점에 묶고, 사고가 난 시각(case)을 같은 달·같은 요일·
같은 시각의 다른 날들(control)과 한 묶음으로 본다. 묶음 안에서 조건부 로지스틱으로 기상
1표준편차 증가당 사고 오즈비를 추정하고(전체·서로 보정한 다변량), 사고종류를 기상 민감형과
기계·비기상형으로 나눠 같은 분석을 다시 한다. 사고종류 구성도 함께 집계한다.

출력: reports/stats/case_crossover.{md,json}, reports/stats/accident_types.{md,json}
실행: uv run python scripts/run_stats.py
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from marine_accident_risk.config import load_settings
from marine_accident_risk.data.clean import clean_coordinates
from marine_accident_risk.data.mtis import load_mtis_accidents
from marine_accident_risk.data.weather_cache import load_weather_hourly, station_coords
from marine_accident_risk.matching.matching import match_accidents_to_weather
from marine_accident_risk.stats.conditional import (
    MECHANICAL,
    WEATHER_SENSITIVE,
    ORResult,
    conditional_logit_adjusted,
    conditional_logit_or,
    standardize,
    time_stratified_referents,
)
from marine_accident_risk.stats.significance import benjamini_hochberg

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "configs" / "default.yaml"
WEATHER_DIR = ROOT / "data" / "cache" / "weather_hourly"
OUT = ROOT / "reports" / "stats"

# 매칭 coverage가 충분한 스칼라 기상 변수(각도형 풍향·유향, 희소 변수는 제외).
VARS = {
    "wind_speed": "풍속(m/s)",
    "air_temp": "기온(℃)",
    "air_pressure": "기압(hPa)",
    "humidity": "습도(%)",
}


def _matched(df: pd.DataFrame, weather: pd.DataFrame, stations: pd.DataFrame, max_km: float) -> pd.DataFrame:
    m = match_accidents_to_weather(df, weather, stations, max_km=max_km)
    return m[m["match_status"] == "matched"].copy()


def _or_row(r: ORResult) -> dict:
    return {
        "variable": r.variable,
        "odds_ratio": round(r.odds_ratio, 4),
        "ci_low": round(r.ci_low, 4),
        "ci_high": round(r.ci_high, 4),
        "pvalue": r.pvalue,
        "n_strata": r.n_strata,
    }


def _fmt_or(r: ORResult | None) -> str:
    if r is None:
        return "— (표본 부족)"
    return f"{r.odds_ratio:.3f} ({r.ci_low:.3f}–{r.ci_high:.3f})"


def build_long(settings) -> pd.DataFrame:
    """case + 시간층화 대조를 기상에 매칭해 조건부 로지스틱용 long frame을 만든다."""
    acc = load_mtis_accidents(settings.mtis_xlsx)
    lat_min, lat_max, lon_min, lon_max = settings.eez_bbox
    acc, _ = clean_coordinates(acc, lat_min=lat_min, lat_max=lat_max, lon_min=lon_min, lon_max=lon_max)
    acc = acc.reset_index(drop=True)
    acc["case_id"] = acc.index

    weather = load_weather_hourly(WEATHER_DIR)
    stations = station_coords(weather)
    cols = ["case_id", "is_case", "accident_type", *VARS]

    case = _matched(acc, weather, stations, settings.match_max_km)
    case["is_case"] = 1
    base = acc[acc["case_id"].isin(case["case_id"])]

    ref_times = time_stratified_referents(base.set_index("case_id")["occurred_at"])
    ref = ref_times.merge(base[["case_id", "lat", "lon", "accident_type"]], on="case_id")
    ref = _matched(ref, weather, stations, settings.match_max_km)
    ref["is_case"] = 0

    long = pd.concat([case[cols], ref[cols]], ignore_index=True).dropna(subset=list(VARS))
    # case와 대조가 모두 있는 묶음만(완전 분리·외톨이 묶음 제거).
    g = long.groupby("case_id")["is_case"].agg(["sum", "count"])
    keep = g[(g["sum"] == 1) & (g["count"] >= 2)].index
    return long[long["case_id"].isin(keep)].copy(), acc


def main() -> None:
    settings = load_settings(CONFIG if CONFIG.exists() else None)
    long, acc = build_long(settings)
    long_std = standardize(long, list(VARS))

    n_strata = int(long["case_id"].nunique())
    mean_ref = (len(long) - n_strata) / n_strata if n_strata else 0.0

    # 전체 단변량 + BH 보정
    overall = [(v, conditional_logit_or(long_std, v)) for v in VARS]
    valid = [(v, r) for v, r in overall if r is not None]
    pvals = [r.pvalue for _, r in valid]
    rejected, q = (
        benjamini_hochberg(pvals) if pvals else (np.array([], bool), np.array([], float))
    )

    adjusted = conditional_logit_adjusted(long_std, list(VARS))
    ws = long_std[long_std["accident_type"].isin(WEATHER_SENSITIVE)]
    me = long_std[long_std["accident_type"].isin(MECHANICAL)]
    group = {
        v: {"weather": conditional_logit_or(ws, v), "mech": conditional_logit_or(me, v)}
        for v in VARS
    }

    OUT.mkdir(parents=True, exist_ok=True)
    summary = {
        "design": "time-stratified case-crossover, conditional logistic regression",
        "referents": "same calendar month, same weekday, same hour",
        "n_strata": n_strata,
        "mean_referents_per_case": round(mean_ref, 2),
        "or_unit": "per 1 SD increase",
        "fdr_alpha": 0.05,
        "overall_univariate": [
            {**_or_row(r), "q_value": float(q[i]), "significant": bool(rejected[i])}
            for i, (_, r) in enumerate(valid)
        ],
        "overall_adjusted": [_or_row(r) for r in adjusted],
        "by_type_group": {
            "weather_sensitive": {"types": list(WEATHER_SENSITIVE), "n_strata": int(ws["case_id"].nunique())},
            "mechanical": {"types": list(MECHANICAL), "n_strata": int(me["case_id"].nunique())},
            "odds_ratios": {
                v: {
                    "weather_sensitive": _or_row(g["weather"]) if g["weather"] else None,
                    "mechanical": _or_row(g["mech"]) if g["mech"] else None,
                }
                for v, g in group.items()
            },
        },
    }
    (OUT / "case_crossover.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    _write_crossover_md(summary, valid, q, rejected, adjusted, group, ws, me)
    _write_types_report(acc)


def _write_crossover_md(summary, valid, q, rejected, adjusted, group, ws, me) -> None:
    lines = [
        "# case-crossover 통계 분석 — 시간층화 조건부 로지스틱",
        "",
        "사고가 난 시각(case)을 **같은 달·같은 요일·같은 시각의 다른 날들**(대조)과 한 묶음으로 구성해,",
        "조건부 로지스틱 회귀로 기상 1표준편차 증가당 사고 오즈비를 추정했습니다. 위치·계절·요일·시각은",
        "묶음이 통제하므로, 조업이 집중되는 시간대나 계절 추세가 결과에 섞이지 않습니다. 사고 전 한 시점만",
        "대조로 쓰는 단방향 방식은 시간 추세에 편향될 수 있어, 같은 달 안에서 같은 요일을 대조로 잡는",
        "시간층화 방식을 따랐습니다(Lumley & Levy 2000; Janes 2005). 여러 변수를 함께 보므로 p값은",
        "Benjamini–Hochberg(FDR)로 보정했습니다.",
        "",
        f"- 분석 묶음(사고): {summary['n_strata']:,}건 · 사고당 평균 대조 {summary['mean_referents_per_case']:.1f}건",
        "- 오즈비: 1표준편차 증가당 사고 오즈 배수(1보다 크면 위험 증가). 전체 표준편차로 표준화해 유형군 간 비교가 가능합니다.",
        "",
        "## 전체 — 단변량 오즈비",
        "",
        "| 변수 | 오즈비 | 95% CI | p | q(BH) | 유의(q<0.05) |",
        "|---|---|---|---|---|---|",
    ]
    order = sorted(range(len(valid)), key=lambda i: float(q[i])) if valid else []
    for i in order:
        v, r = valid[i]
        sig = "○" if rejected[i] else "—"
        lines.append(
            f"| {VARS[v]} | {r.odds_ratio:.3f} | {r.ci_low:.2f}–{r.ci_high:.2f} "
            f"| {r.pvalue:.2e} | {float(q[i]):.2e} | {sig} |"
        )
    lines += [
        "",
        "## 전체 — 다변량(서로 보정) 오즈비",
        "",
        "네 변수를 한 모델에 함께 넣어 서로 보정한 오즈비입니다.",
        "",
        "| 변수 | 오즈비 | 95% CI | p |",
        "|---|---|---|---|",
    ]
    for r in adjusted:
        lines.append(f"| {VARS[r.variable]} | {r.odds_ratio:.3f} | {r.ci_low:.2f}–{r.ci_high:.2f} | {r.pvalue:.2e} |")
    lines += [
        "",
        "## 사고 유형군별 — 단변량 오즈비",
        "",
        f"사고종류를 **기상 민감형**(충돌·좌초·전복·접촉·침몰·침수, {int(ws['case_id'].nunique()):,}건)과 "
        f"**기계·비기상형**(기관손상·부유물감김·추진축계손상·조타장치손상·운항저해, {int(me['case_id'].nunique()):,}건)으로",
        "나눠 같은 분석을 다시 했습니다.",
        "",
        "| 변수 | 기상 민감형 오즈비(95% CI) | 기계·비기상형 오즈비(95% CI) |",
        "|---|---|---|",
    ]
    for v in VARS:
        g = group[v]
        lines.append(f"| {VARS[v]} | {_fmt_or(g['weather'])} | {_fmt_or(g['mech'])} |")
    lines += [
        "",
        "강한 기상 연관(풍속 오즈비 1 미만·기온 오즈비 1 초과)은 **기계·비기상형 사고에 집중되어** 있고, 기상 민감형",
        "사고에서는 풍속이 유의하지 않았습니다. 기계 고장형 사고는 위험한 기상 때문이라기보다, 출항과 조업이 늘어나는",
        "**잔잔하고 따뜻한 날**에 더 많이 발생합니다. 즉 사고 시점 기상과의 연관은 위험 신호라기보다 활동·노출",
        "패턴이 반영된 결과로 해석했습니다. 사고종류 구성은 [accident_types.md](accident_types.md)를 참고하세요.",
        "",
        "재현: `uv run python scripts/run_stats.py`",
        "",
    ]
    (OUT / "case_crossover.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


def _write_types_report(acc: pd.DataFrame) -> None:
    n = int(len(acc))
    vc = acc["accident_type"].value_counts()
    mech_total = int(vc.reindex(MECHANICAL).fillna(0).sum())
    weather_total = int(vc.reindex(WEATHER_SENSITIVE).fillna(0).sum())
    payload = {
        "n_accidents": n,
        "counts": {str(k): int(v) for k, v in vc.items()},
        "mechanical_subtotal": mech_total,
        "weather_sensitive_subtotal": weather_total,
    }
    (OUT / "accident_types.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    lines = [
        "# 사고종류 구성",
        "",
        f"정제 사고 {n:,}건을 사고종류(MTIS 분류)로 집계했습니다. 이 분포는 공공데이터포털(data.go.kr)에",
        "공개된 한국해양교통안전공단(KOMSA)의 '사고종류별 통계'와 같은 성격의 집계입니다.",
        "",
        "| 사고종류 | 건수 | 비율 |",
        "|---|---|---|",
    ]
    for k, v in vc.items():
        lines.append(f"| {k} | {int(v):,} | {v / n * 100:.1f}% |")
    lines += [
        "",
        f"- 기계·비기상형 소계(기관손상·부유물감김·추진축계손상·조타장치손상·운항저해): "
        f"**{mech_total:,}건 ({mech_total / n * 100:.1f}%)**",
        f"- 기상 민감형 소계(충돌·좌초·전복·접촉·침몰·침수): {weather_total:,}건 ({weather_total / n * 100:.1f}%)",
        "",
        "설비 고장형(기관손상·부유물감김 등)이 가장 큰 비중을 차지합니다. 이 구성은 위험도 분석에서 기상",
        "신호가 약하게 나오는 이유 중 하나이며, 시간층화 case-crossover에서 강한 기상 연관이 기계·비기상형",
        "사고에 집중된 결과와도 일치합니다([case_crossover.md](case_crossover.md)).",
        "",
        "재현: `uv run python scripts/run_stats.py`",
        "",
    ]
    (OUT / "accident_types.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
