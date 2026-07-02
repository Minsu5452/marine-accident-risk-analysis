"""정적 데모 데이터 캡처 — 실제 실행 결과를 프론트가 키 없이 재생하도록 JSON으로 저장한다.

격자 위험(해상도 3종)·셀 상세(0.1°: 위험·순위·해역·최근접 지점·과거 사고)·통계·XAI를
web/public/demo/ 아래에 쓴다. 값은 모두 실제 모델/리포트 산출이며 손으로 고치지 않는다
(고치면 '실제 실행 재생' 고지가 거짓이 된다). 다시 만들려면 이 스크립트를 재실행한다.

실행: uv run python scripts/capture_demo.py
"""

from __future__ import annotations

import bisect
import json
from pathlib import Path
from typing import cast

import pandas as pd

from marine_accident_risk.config import load_settings
from marine_accident_risk.data.clean import clean_coordinates
from marine_accident_risk.data.mtis import load_mtis_accidents
from marine_accident_risk.grid.grid import assign_grid
from marine_accident_risk.serving.service import RiskService

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "configs" / "default.yaml"
CACHE = ROOT / "data" / "cache"
REPORTS = ROOT / "reports"
OUT = ROOT / "web" / "public" / "demo"
TOP_PCT = 0.90  # 고위험 = 위험도 상위 10%


def _level_by_pct(pct: float) -> str:
    """셀 위험도의 상대 백분위로 단계를 매긴다(모델 점수가 압축돼 있어 상대 단계로 표시)."""
    if pct >= 0.95:
        return "veryhigh"
    if pct >= 0.85:
        return "high"
    if pct >= 0.60:
        return "mid"
    if pct >= 0.30:
        return "low"
    return "verylow"


def main() -> None:
    settings = load_settings(CONFIG if CONFIG.exists() else None)
    OUT.mkdir(parents=True, exist_ok=True)

    acc = load_mtis_accidents(settings.mtis_xlsx)
    lat_min, lat_max, lon_min, lon_max = settings.eez_bbox
    acc, _ = clean_coordinates(acc, lat_min=lat_min, lat_max=lat_max, lon_min=lon_min, lon_max=lon_max)
    acc["year"] = pd.to_datetime(acc["occurred_at"]).dt.year
    acc["casualties"] = acc["deaths"] + acc["missing"] + acc["injuries"]

    grids: dict[float, list[dict]] = {}
    for res in settings.grid_resolutions:
        cells = RiskService(CACHE, REPORTS, res).grid()
        risks = sorted(cast(float, c["risk"]) for c in cells)
        n = len(risks)
        for c in cells:
            pct = bisect.bisect_right(risks, cast(float, c["risk"])) / n
            c["pct"] = round(pct, 4)
            c["level"] = _level_by_pct(pct)
        grids[res] = cells
        (OUT / f"grid_{res}.json").write_text(
            json.dumps({"resolution": res, "cells": cells}, ensure_ascii=False), encoding="utf-8"
        )

    high_counts = {
        str(res): sum(1 for c in grids[res] if cast(float, c["pct"]) >= TOP_PCT)
        for res in settings.grid_resolutions
    }
    (OUT / "meta.json").write_text(
        json.dumps(
            {
                "period": "2018–2025",
                "accidents": int(len(acc)),
                "stations": 76,
                "resolutions": [str(r) for r in settings.grid_resolutions],
                "high_risk_def": "위험도 상위 10%",
                "high_risk_count": high_counts,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    # 0.1° 셀 상세(과거 사고·해역은 정제 사고에서, 최근접 지점은 학습셋에서)
    res0 = 0.1 if 0.1 in settings.grid_resolutions else settings.grid_resolutions[0]
    ag = assign_grid(acc, res0).dropna(subset=["grid_id"])
    ds = pd.read_csv(CACHE / f"dataset_{res0}.csv")
    nearest: dict = {}
    if "nearest_station" in ds.columns:
        grouped = ds.dropna(subset=["nearest_station"]).groupby("grid_id")
        for gid, g in grouped:
            mode = g["nearest_station"].mode()
            nearest[gid] = {
                "nearest_station": str(mode.iloc[0]) if not mode.empty else None,
                "dist_km": round(float(g["station_dist_km"].median()), 1),
            }

    xai = json.loads((REPORTS / "xai" / "odds_ratios.json").read_text(encoding="utf-8"))
    factors = sorted(
        (o for o in xai["odds_ratios"] if o["feature"] != "(상수)"),
        key=lambda o: o["odds_ratio"],
        reverse=True,
    )[:5]

    by_id = {cast(str, c["grid_id"]): c for c in grids[res0]}
    ranked = sorted(by_id.values(), key=lambda c: cast(float, c["risk"]), reverse=True)
    rank_of = {cast(str, c["grid_id"]): i + 1 for i, c in enumerate(ranked)}

    details: dict[str, dict] = {}
    for gid, g in ag.groupby("grid_id"):
        gid = cast(str, gid)
        if gid not in by_id:
            continue
        base = by_id[gid]
        sea_mode = g["sea_area"].mode()
        past = (
            g.sort_values("occurred_at", ascending=False)
            .head(6)[["year", "accident_type", "vessel_use", "casualties"]]
            .to_dict("records")
        )
        details[gid] = {
            "grid_id": gid,
            "risk": base["risk"],
            "percentile": base.get("pct"),
            "rank": rank_of.get(gid),
            "total_cells": len(by_id),
            "lat": base["lat"],
            "lon": base["lon"],
            "sea_area": str(sea_mode.iloc[0]) if not sea_mode.empty else "",
            "nearest_station": nearest.get(gid, {}).get("nearest_station"),
            "dist_km": nearest.get(gid, {}).get("dist_km"),
            "accidents": int(len(g)),
            "contributing_factors": factors,
            "past": past,
        }
    (OUT / f"cells_{res0}.json").write_text(json.dumps(details, ensure_ascii=False), encoding="utf-8")

    for src, dst in [
        ("stats/case_crossover.json", "stats.json"),
        ("xai/odds_ratios.json", "xai.json"),
        ("model/metrics.json", "model.json"),
    ]:
        (OUT / dst).write_text((REPORTS / src).read_text(encoding="utf-8"), encoding="utf-8")

    print(f"데모 데이터 캡처 완료 → {OUT}")
    print(f"  격자 {[len(grids[r]) for r in settings.grid_resolutions]}셀 · 0.1° 상세 {len(details)}셀 · 고위험 {high_counts}")


if __name__ == "__main__":
    main()
