"""NMPNT 관측 지점의 변수별 커버리지 리포트.

지점 목록(getStationInfo)의 관측항목을 변수별로 집계한다. 인증키는 필요 없다.
실행: uv run python scripts/station_coverage.py
출력: reports/weather/station_coverage.{md,json}
"""

from __future__ import annotations

import json
from pathlib import Path

from marine_accident_risk.data.nmpnt import fetch_stations, make_client

VARS = ["풍향", "풍속", "기온", "습도", "기압", "시정", "수온", "염분", "유향", "유속", "파향", "파고"]
OUT = Path("reports/weather")


def main() -> None:
    with make_client(verify=False) as client:
        stations = fetch_stations(client)
    n = len(stations)
    joined = [",".join(s.observe_items) for s in stations]
    counts = {v: sum(1 for j in joined if v in j) for v in VARS}

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "station_coverage.json").write_text(
        json.dumps({"total_stations": n, "coverage": counts}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    lines = [
        "# NMPNT 관측 지점 변수 커버리지",
        "",
        f"국립해양측위정보원 전국 {n}개 연안 관측 지점에서 변수별로 몇 개 지점이 관측하는지 집계했습니다.",
        "",
        "| 변수 | 관측 지점 수 |",
        "|---|---|",
    ]
    lines += [f"| {v} | {counts[v]} / {n} |" for v in VARS]
    lines += [
        "",
        "파고·파향은 모든 지점에서 미제공이라 분석에서 제외하고, 거친 바다의 영향은 풍속으로 부분 대리합니다.",
        "수온·염분·유속은 관측 지점이 적어 결측이 늘어납니다.",
        "",
        "재현: `uv run python scripts/station_coverage.py`",
        "",
    ]
    md = "\n".join(lines)
    (OUT / "station_coverage.md").write_text(md, encoding="utf-8")
    print(md)


if __name__ == "__main__":
    main()
