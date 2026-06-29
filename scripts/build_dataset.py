"""학습 데이터셋 빌드 — 격자×시간 셀의 사고 발생 여부(이진)에 기상을 붙인다.

모델 단위는 (격자, 시간) 셀이다. 양성 = 사고가 난 셀, 음성 = negative sampling으로 뽑은
무사고 셀. 두 클래스 모두 셀 중심 좌표를 가장 가까운 관측 지점에 매칭해 같은 규칙으로
기상을 붙인다(할당 방식 일관). 해상도 3종을 각각 만든다.

입력: data/raw MTIS 엑셀, data/cache/weather_hourly/*.csv(collect_weather_bulk.py 결과).
출력: data/cache/dataset_{res}.csv, reports/dataset/summary.md
실행: uv run python scripts/build_dataset.py [--ratio 3] [--seed 0]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

from marine_accident_risk.config import load_settings
from marine_accident_risk.data.clean import clean_coordinates
from marine_accident_risk.data.mtis import load_mtis_accidents
from marine_accident_risk.grid.grid import assign_grid
from marine_accident_risk.grid.sampling import sample_negative_cells
from marine_accident_risk.matching.matching import match_accidents_to_weather

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "configs" / "default.yaml"
WEATHER_DIR = ROOT / "data" / "cache" / "weather_hourly"
OUT_CACHE = ROOT / "data" / "cache"
OUT_REPORT = ROOT / "reports" / "dataset"


def _load_weather() -> pd.DataFrame:
    files = sorted(WEATHER_DIR.glob("*.csv"))
    frames = [
        pd.read_csv(f, parse_dates=["observed_hour"]) for f in files if f.stat().st_size > 0
    ]
    if not frames:
        sys.exit("수집된 기상이 없습니다. 먼저 scripts/collect_weather_bulk.py를 실행하세요.")
    w = pd.concat(frames, ignore_index=True)
    w["station_code"] = w["station_code"].astype(str)
    return w


def _station_coords(weather: pd.DataFrame) -> pd.DataFrame:
    """지점 좌표 — 기상 레코드에 실린 lat/lon의 지점별 대표값(중앙값)."""
    g = weather.dropna(subset=["lat", "lon"]).groupby("station_code")[["lat", "lon"]].median()
    return g.reset_index()


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="학습 데이터셋 빌드")
    p.add_argument("--ratio", type=int, default=3, help="양성당 음성 배수")
    p.add_argument("--seed", type=int, default=0, help="negative sampling 시드")
    return p.parse_args()


def main() -> None:
    args = _parse_args()
    settings = load_settings(CONFIG if CONFIG.exists() else None)

    acc = load_mtis_accidents(settings.mtis_xlsx)
    lat_min, lat_max, lon_min, lon_max = settings.eez_bbox
    acc, _ = clean_coordinates(acc, lat_min=lat_min, lat_max=lat_max, lon_min=lon_min, lon_max=lon_max)
    acc["occurred_hour"] = pd.to_datetime(acc["occurred_at"]).dt.floor("h")

    weather = _load_weather()
    stations = _station_coords(weather)
    hours = pd.Series(sorted(pd.Series(weather["observed_hour"].unique())))

    summary: dict = {
        "accidents_clean": len(acc),
        "weather_days": int(sum(1 for f in WEATHER_DIR.glob("*.csv") if f.stat().st_size > 0)),
        "weather_hours": int(len(hours)),
        "stations": int(len(stations)),
        "ratio": args.ratio,
        "by_resolution": {},
    }

    OUT_CACHE.mkdir(parents=True, exist_ok=True)
    for res in settings.grid_resolutions:
        a = assign_grid(acc, res).dropna(subset=["grid_id"])
        pos_cells = a.drop_duplicates(["grid_id", "occurred_hour"])[
            ["grid_id", "occurred_hour", "grid_lat_center", "grid_lon_center"]
        ].copy()
        pos_cells["label"] = 1
        coastal = a.drop_duplicates("grid_id")[["grid_id", "grid_lat_center", "grid_lon_center"]]

        neg = sample_negative_cells(
            pos_cells.rename(columns={"occurred_hour": "hour"})[["grid_id", "hour"]],
            coastal,
            hours,
            ratio=args.ratio,
            seed=args.seed,
        )
        neg = neg.rename(columns={"hour": "occurred_hour"})
        neg["label"] = 0

        cells = pd.concat(
            [pos_cells, neg[["grid_id", "occurred_hour", "grid_lat_center", "grid_lon_center", "label"]]],
            ignore_index=True,
        )
        # 셀 중심 좌표를 최근접 지점에 매칭해 기상을 붙인다(양성·음성 동일 규칙).
        pts = cells.rename(
            columns={"grid_lat_center": "lat", "grid_lon_center": "lon", "occurred_hour": "occurred_at"}
        )
        matched = match_accidents_to_weather(pts, weather, stations, max_km=settings.match_max_km)
        kept = matched[matched["match_status"] == "matched"].copy()
        kept.to_csv(OUT_CACHE / f"dataset_{res}.csv", index=False)

        summary["by_resolution"][str(res)] = {
            "positive_cells": int((cells["label"] == 1).sum()),
            "negative_cells": int((cells["label"] == 0).sum()),
            "with_weather": int(len(kept)),
            "positive_with_weather": int((kept["label"] == 1).sum()),
            "negative_with_weather": int((kept["label"] == 0).sum()),
        }

    OUT_REPORT.mkdir(parents=True, exist_ok=True)
    (OUT_REPORT / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    lines = [
        "# 학습 데이터셋 요약",
        "",
        f"- 정제 사고: {summary['accidents_clean']:,}건",
        f"- 기상 수집: {summary['weather_days']:,}일 · {summary['weather_hours']:,}시간 · {summary['stations']}개 지점",
        f"- negative sampling 비율: 양성당 {summary['ratio']}배",
        "",
        "| 해상도(°) | 양성 셀 | 음성 셀 | 기상 매칭 | 양성(기상) | 음성(기상) |",
        "|---|---|---|---|---|---|",
    ]
    for res, r in summary["by_resolution"].items():
        lines.append(
            f"| {res} | {r['positive_cells']:,} | {r['negative_cells']:,} | {r['with_weather']:,} "
            f"| {r['positive_with_weather']:,} | {r['negative_with_weather']:,} |"
        )
    lines += ["", "재현: `uv run python scripts/build_dataset.py`", ""]
    (OUT_REPORT / "summary.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
