"""좌표 정제 — 한국 EEZ 대략 bbox 밖이거나 결측인 좌표를 제거한다.

MTIS 원본에는 한국 해역을 벗어난 좌표 이상치(위도 음수, 경도 200대 등)가 섞여 있다.
격자 배정 전에 이 단계를 반드시 거치고, 제거 건수는 리포트로 남긴다.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class CleaningReport:
    """좌표 정제 결과 요약. (lat_min, lat_max, lon_min, lon_max) 순서의 bbox."""

    total: int
    kept: int
    removed_missing: int
    removed_out_of_bbox: int
    bbox: tuple[float, float, float, float]

    @property
    def removed(self) -> int:
        return self.total - self.kept

    def as_dict(self) -> dict:
        return {
            "total": self.total,
            "kept": self.kept,
            "removed": self.removed,
            "removed_missing": self.removed_missing,
            "removed_out_of_bbox": self.removed_out_of_bbox,
            "bbox": {
                "lat_min": self.bbox[0],
                "lat_max": self.bbox[1],
                "lon_min": self.bbox[2],
                "lon_max": self.bbox[3],
            },
        }


def clean_coordinates(
    df: pd.DataFrame,
    *,
    lat_min: float,
    lat_max: float,
    lon_min: float,
    lon_max: float,
    lat_col: str = "lat",
    lon_col: str = "lon",
) -> tuple[pd.DataFrame, CleaningReport]:
    """bbox 밖·결측 좌표 행을 제거한 DataFrame과 정제 리포트를 돌려준다.

    결측(좌표 NaN)과 범위 밖(bbox 초과)을 따로 센다. lat_col/lon_col은 숫자이거나
    숫자로 변환 가능한 컬럼이면 된다(문자열 좌표도 직접 정제할 수 있게 to_numeric을 거친다).
    bbox 경계값은 포함한다(between inclusive).
    """
    total = len(df)
    lat = pd.to_numeric(df[lat_col], errors="coerce")
    lon = pd.to_numeric(df[lon_col], errors="coerce")
    missing = lat.isna() | lon.isna()
    in_bbox = lat.between(lat_min, lat_max) & lon.between(lon_min, lon_max)
    keep = (~missing) & in_bbox
    cleaned = df.loc[keep].reset_index(drop=True)
    report = CleaningReport(
        total=total,
        kept=int(keep.sum()),
        removed_missing=int(missing.sum()),
        removed_out_of_bbox=int(((~missing) & (~in_bbox)).sum()),
        bbox=(lat_min, lat_max, lon_min, lon_max),
    )
    return cleaned, report
