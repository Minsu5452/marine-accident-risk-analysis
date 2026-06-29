"""NMPNT 해양기상 수집 — 지점 목록 캐시 + 기간별 수집 + 시간 리샘플.

키는 환경변수 NMPNT_SERVICE_KEY로만 주입한다(레포엔 이름만).
실행 예(스모크): uv run python scripts/collect_weather.py --start 20240115 --end 20240115 --limit-stations 3
전 기간·전 지점 수집은 호출이 많아 오래 걸린다(데이터셋 빌드 단계에서 수행).
출력: data/cache/stations.json, data/cache/weather_hourly.csv (둘 다 .gitignore).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

from marine_accident_risk.data.nmpnt import (
    fetch_stations,
    fetch_weather_date,
    make_client,
    parse_weather,
    resample_hourly,
)

# 실행 cwd와 무관하게 프로젝트 루트 기준으로 캐시 경로를 잡는다.
CACHE = Path(__file__).resolve().parent.parent / "data" / "cache"


def _daterange(start: str, end: str) -> list[str]:
    s = datetime.strptime(start, "%Y%m%d").date()
    e = datetime.strptime(end, "%Y%m%d").date()
    days, d = [], s
    while d <= e:
        days.append(d.strftime("%Y%m%d"))
        d += timedelta(days=1)
    return days


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="NMPNT 해양기상 수집")
    p.add_argument("--start", required=True, help="시작일 YYYYMMDD")
    p.add_argument("--end", required=True, help="종료일 YYYYMMDD")
    p.add_argument("--limit-stations", type=int, default=None, help="수집 지점 수 제한(스모크용)")
    return p.parse_args()


def main() -> None:
    key = os.environ.get("NMPNT_SERVICE_KEY")
    if not key:
        sys.exit("NMPNT_SERVICE_KEY 환경변수가 필요합니다.")
    args = _parse_args()
    CACHE.mkdir(parents=True, exist_ok=True)

    # 지점 목록(좌표는 없음) → 캐시
    with make_client(verify=False) as client:
        stations = fetch_stations(client)
    (CACHE / "stations.json").write_text(
        json.dumps([s.model_dump() for s in stations], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"지점 {len(stations)}개 → data/cache/stations.json")

    if args.limit_stations:
        stations = stations[: args.limit_stations]
    by_mmaf: dict[str, list[str]] = defaultdict(list)
    for s in stations:
        by_mmaf[s.mmaf_code].append(s.station_code)

    frames: list[pd.DataFrame] = []
    with make_client() as client:
        for day in _daterange(args.start, args.end):
            for mmaf, mmsis in by_mmaf.items():
                records = fetch_weather_date(
                    client, service_key=key, date=day, mmaf=mmaf, mmsi=mmsis
                )
                df = parse_weather(records)
                if not df.empty:
                    frames.append(df)

    if not frames:
        sys.exit("수집된 기상 레코드가 없습니다(기간·지점을 확인하세요).")
    raw = pd.concat(frames, ignore_index=True)
    hourly = resample_hourly(raw)
    hourly.to_csv(CACHE / "weather_hourly.csv", index=False)
    print(
        f"10분 관측 {len(raw):,}건 → 시간 리샘플 {len(hourly):,}건 "
        f"({hourly['station_code'].nunique()}개 지점) → data/cache/weather_hourly.csv"
    )


if __name__ == "__main__":
    main()
