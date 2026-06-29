"""NMPNT 해양기상 전기간 수집(재개 가능·동시성 제한·실패 격리).

날짜별로 전 지점(기관별 묶음) 10분 관측을 받아 시간 단위로 리샘플하고, 날짜마다
한 파일로 저장한다. 이미 있는 날짜는 건너뛰어 중단되어도 이어서 받는다. 개별 날짜의
호출이 재시도 후에도 실패하면 그 날짜만 건너뛰고 기록한다(전체 작업은 멈추지 않는다).

키는 환경변수 NMPNT_SERVICE_KEY로만 주입한다.
실행 예: uv run python scripts/collect_weather_bulk.py --start 20180101 --end 20251231 --workers 4
출력: data/cache/weather_hourly/<YYYYMMDD>.csv, data/cache/weather_hourly/_failed.json (둘 다 .gitignore)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

from marine_accident_risk.data.nmpnt import (
    Station,
    fetch_stations,
    fetch_weather_date,
    make_client,
    parse_weather,
    resample_hourly,
)

# 실행 cwd와 무관하게 프로젝트 루트 기준으로 캐시 경로를 잡는다.
CACHE = Path(__file__).resolve().parent.parent / "data" / "cache"
DEFAULT_OUT = CACHE / "weather_hourly"


def _daterange(start: str, end: str) -> list[str]:
    s = datetime.strptime(start, "%Y%m%d").date()
    e = datetime.strptime(end, "%Y%m%d").date()
    days, d = [], s
    while d <= e:
        days.append(d.strftime("%Y%m%d"))
        d += timedelta(days=1)
    return days


def _collect_day(day: str, by_mmaf: dict[str, list[str]], key: str, out_dir: Path) -> tuple[str, int, str | None]:
    """하루치를 받아 시간 리샘플해 한 파일로 저장한다. 반환: (날짜, 행수|-1=skip, 오류|None)."""
    out = out_dir / f"{day}.csv"
    if out.exists():
        return (day, -1, None)
    frames: list[pd.DataFrame] = []
    try:
        with make_client() as client:
            for mmaf, mmsis in by_mmaf.items():
                records = fetch_weather_date(client, service_key=key, date=day, mmaf=mmaf, mmsi=mmsis)
                df = parse_weather(records)
                if not df.empty:
                    frames.append(df)
    except Exception as exc:  # 재시도 후에도 실패한 날 → 파일을 쓰지 않아 재개 시 다시 시도
        return (day, 0, f"{type(exc).__name__}: {exc}")
    if not frames:
        out.write_text("", encoding="utf-8")  # 데이터 없는 날 → 빈 파일로 표시(재수집 방지)
        return (day, 0, None)
    hourly = resample_hourly(pd.concat(frames, ignore_index=True))
    hourly.to_csv(out, index=False)
    return (day, len(hourly), None)


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="NMPNT 전기간 수집(재개 가능)")
    p.add_argument("--start", default="20180101", help="시작일 YYYYMMDD")
    p.add_argument("--end", default="20251231", help="종료일 YYYYMMDD")
    p.add_argument("--workers", type=int, default=4, help="동시 수집 일자 수")
    p.add_argument("--limit-stations", type=int, default=None, help="지점 수 제한(스모크용)")
    p.add_argument("--out-dir", default=str(DEFAULT_OUT), help="출력 디렉터리")
    return p.parse_args()


def main() -> None:
    key = os.environ.get("NMPNT_SERVICE_KEY")
    if not key:
        sys.exit("NMPNT_SERVICE_KEY 환경변수가 필요합니다.")
    args = _parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)

    with make_client(verify=False) as client:
        stations: list[Station] = fetch_stations(client)
    (CACHE / "stations.json").write_text(
        json.dumps([s.model_dump() for s in stations], ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if args.limit_stations:
        stations = stations[: args.limit_stations]
    by_mmaf: dict[str, list[str]] = defaultdict(list)
    for s in stations:
        by_mmaf[s.mmaf_code].append(s.station_code)

    days = _daterange(args.start, args.end)
    print(f"지점 {len(stations)}개({len(by_mmaf)}개 기관) · 기간 {args.start}~{args.end} {len(days)}일 · 동시 {args.workers}")

    collected = skipped = empty = 0
    failed: list[dict[str, str]] = []
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures: list[Future[tuple[str, int, str | None]]] = [
            ex.submit(_collect_day, d, by_mmaf, key, out_dir) for d in days
        ]
        for i, fut in enumerate(as_completed(futures), 1):
            day, n, err = fut.result()
            if err:
                failed.append({"date": day, "error": err})
            elif n == -1:
                skipped += 1
            elif n == 0:
                empty += 1
            else:
                collected += 1
            if i % 50 == 0 or err:
                print(f"  [{i}/{len(days)}] 수집 {collected} · 건너뜀 {skipped} · 빈날 {empty} · 실패 {len(failed)}", flush=True)

    if failed:
        (out_dir / "_failed.json").write_text(
            json.dumps(failed, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    print(
        f"완료: 수집 {collected} · 건너뜀 {skipped} · 빈날 {empty} · 실패 {len(failed)}"
        + (f" → {out_dir}/_failed.json" if failed else "")
    )


if __name__ == "__main__":
    main()
