"""MTIS 사고 엑셀을 읽어 좌표를 정제하고 리포트를 남긴다.

실행: uv run python scripts/clean_accidents.py
출력: reports/clean/coordinate_cleaning.{md,json}
"""

from __future__ import annotations

import json
from pathlib import Path

from marine_accident_risk.config import load_settings
from marine_accident_risk.data.clean import CleaningReport, clean_coordinates
from marine_accident_risk.data.mtis import load_mtis_accidents

# 실행 cwd와 무관하게 프로젝트 루트의 설정을 찾도록 앵커링한다.
CONFIG = Path(__file__).resolve().parent.parent / "configs" / "default.yaml"


def _render_md(report: CleaningReport) -> str:
    d = report.as_dict()
    b = d["bbox"]
    return (
        "# 좌표 정제 리포트\n\n"
        f"- 원본 사고: {d['total']:,}건\n"
        f"- 정제 후: {d['kept']:,}건\n"
        f"- 제거: {d['removed']:,}건 "
        f"(범위 밖 {d['removed_out_of_bbox']:,} · 결측 {d['removed_missing']:,})\n\n"
        f"한국 EEZ 대략 bbox: 위도 {b['lat_min']}~{b['lat_max']}, "
        f"경도 {b['lon_min']}~{b['lon_max']}\n\n"
        "재현: `uv run python scripts/clean_accidents.py`\n"
    )


def main() -> None:
    settings = load_settings(CONFIG if CONFIG.exists() else None)
    df = load_mtis_accidents(settings.mtis_xlsx)
    lat_min, lat_max, lon_min, lon_max = settings.eez_bbox
    _, report = clean_coordinates(
        df, lat_min=lat_min, lat_max=lat_max, lon_min=lon_min, lon_max=lon_max
    )

    out_dir = settings.reports_dir / "clean"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "coordinate_cleaning.json").write_text(
        json.dumps(report.as_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    md = _render_md(report)
    (out_dir / "coordinate_cleaning.md").write_text(md, encoding="utf-8")
    print(md)


if __name__ == "__main__":
    main()
