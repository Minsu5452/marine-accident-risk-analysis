"""case-crossover 통계 분석 — 사고 시점 기상 vs 사고 전 7일 동시간 대조.

각 사고를 그 위치의 최근접 관측 지점에 매칭해 사고 시점(case)과 7일 전 동시간(control)의
기상을 붙이고, 변수별로 정규성에 따라 검정을 골라 비교한 뒤 BH(FDR)로 보정한다.
같은 위치·같은 지점을 쓰므로 계절·지점 같은 고정 요인이 통제된다(짝지은 비교).

출력: reports/stats/case_crossover.{md,json}
실행: uv run python scripts/run_stats.py
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from marine_accident_risk.config import load_settings
from marine_accident_risk.data.clean import clean_coordinates
from marine_accident_risk.data.mtis import load_mtis_accidents
from marine_accident_risk.data.weather_cache import load_weather_hourly, station_coords
from marine_accident_risk.matching.matching import match_accidents_to_weather
from marine_accident_risk.stats.crossover import control_times
from marine_accident_risk.stats.significance import benjamini_hochberg, compare_paired

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "configs" / "default.yaml"
WEATHER_DIR = ROOT / "data" / "cache" / "weather_hourly"
OUT = ROOT / "reports" / "stats"

# 비교할 스칼라 기상 변수(각도형 풍향·유향은 짝 t/Wilcoxon에 부적합해 제외).
VARS = {
    "wind_speed": "풍속(m/s)",
    "air_temp": "기온(℃)",
    "air_pressure": "기압(hPa)",
    "humidity": "습도(%)",
    "visibility": "시정(m)",
    "water_temp": "수온(℃)",
    "current_speed": "유속",
}
MIN_PAIRS = 30


def main() -> None:
    settings = load_settings(CONFIG if CONFIG.exists() else None)
    acc = load_mtis_accidents(settings.mtis_xlsx)
    lat_min, lat_max, lon_min, lon_max = settings.eez_bbox
    acc, _ = clean_coordinates(acc, lat_min=lat_min, lat_max=lat_max, lon_min=lon_min, lon_max=lon_max)

    weather = load_weather_hourly(WEATHER_DIR)
    stations = station_coords(weather)

    case = match_accidents_to_weather(acc, weather, stations, max_km=settings.match_max_km)
    ctrl_acc = acc.copy()
    ctrl_acc["occurred_at"] = control_times(acc["occurred_at"], lag_days=7)
    control = match_accidents_to_weather(ctrl_acc, weather, stations, max_km=settings.match_max_km)

    results = []
    for col, label in VARS.items():
        if col not in case.columns or col not in control.columns:
            continue
        r = compare_paired(label, case[col].to_numpy(dtype=float), control[col].to_numpy(dtype=float))
        if r.n >= MIN_PAIRS:
            results.append(r)

    pvals = [r.pvalue for r in results]
    rejected, q = (
        benjamini_hochberg(pvals)
        if pvals
        else (np.array([], dtype=bool), np.array([], dtype=float))
    )

    rows = [
        {
            "variable": r.variable,
            "n_pairs": r.n,
            "test": r.test,
            "effect_size": round(r.effect_size, 4),
            "effect_name": r.effect_name,
            "pvalue": r.pvalue,
            "q_value": float(q[i]),
            "significant": bool(rejected[i]),
        }
        for i, r in enumerate(results)
    ]

    OUT.mkdir(parents=True, exist_ok=True)
    summary = {
        "accidents": int(len(acc)),
        "case_matched": int((case["match_status"] == "matched").sum()),
        "control_matched": int((control["match_status"] == "matched").sum()),
        "lag_days": 7,
        "fdr_alpha": 0.05,
        "results": rows,
    }
    (OUT / "case_crossover.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# case-crossover 통계 분석",
        "",
        "사고 시점 기상과 **사고 전 7일 동시간**(같은 위치·같은 관측 지점) 대조를 짝지어 비교했다.",
        "변수별로 차이의 정규성을 확인해 짝 t검정 또는 Wilcoxon 부호순위 검정을 자동 선택하고,",
        "여러 변수를 함께 검정하므로 Benjamini–Hochberg(FDR)로 p값을 보정했다.",
        "",
        f"- 정제 사고: {summary['accidents']:,}건 · 사고 시점 기상 매칭 {summary['case_matched']:,} · 대조 매칭 {summary['control_matched']:,}",
        "- 효과크기: 짝 t는 Cohen's d, Wilcoxon은 rank-biserial (양수면 사고 시점이 더 큼)",
        "",
        "| 변수 | 짝수 | 검정 | 효과크기 | p | q(BH) | 유의(q<0.05) |",
        "|---|---|---|---|---|---|---|",
    ]
    order = sorted(range(len(results)), key=lambda i: float(q[i])) if results else []
    for i in order:
        row = rows[i]
        sig = "○" if row["significant"] else "—"
        lines.append(
            f"| {row['variable']} | {row['n_pairs']:,} | {row['test']} | {row['effect_size']:+.3f} "
            f"| {row['pvalue']:.2e} | {row['q_value']:.2e} | {sig} |"
        )
    lines += ["", "재현: `uv run python scripts/run_stats.py`", ""]
    (OUT / "case_crossover.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
