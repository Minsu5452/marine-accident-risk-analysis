"""격자 정의·배정. 위경도를 해상도(도)별 격자 셀에 배정한다.

세 해상도(0.05·0.1·0.25°)를 모두 산출하고 프론트에서 선택한다. 셀은 위경도 bin
인덱스(원점 0 기준 floor)로 식별하고, grid_id = "{resolution}:{lat_bin}_{lon_bin}"를 쓴다.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

GRID_RESOLUTIONS: tuple[float, ...] = (0.05, 0.1, 0.25)


def assign_grid(
    df: pd.DataFrame, resolution: float, *, lat_col: str = "lat", lon_col: str = "lon"
) -> pd.DataFrame:
    """df에 격자 컬럼을 붙여 돌려준다.

    추가 컬럼: grid_lat_bin, grid_lon_bin(정수 bin), grid_id(문자열),
    grid_lat_center, grid_lon_center(셀 중심 좌표). 좌표 결측 행의 grid_id는 None.
    """
    out = df.copy()
    lat = pd.to_numeric(out[lat_col], errors="coerce")
    lon = pd.to_numeric(out[lon_col], errors="coerce")
    lat_bin = np.floor(lat / resolution).astype("Int64")
    lon_bin = np.floor(lon / resolution).astype("Int64")
    out["grid_lat_bin"] = lat_bin
    out["grid_lon_bin"] = lon_bin
    out["grid_id"] = [
        f"{resolution}:{a}_{o}" if pd.notna(a) and pd.notna(o) else None
        for a, o in zip(lat_bin, lon_bin, strict=True)
    ]
    out["grid_lat_center"] = (lat_bin + 0.5) * resolution
    out["grid_lon_center"] = (lon_bin + 0.5) * resolution
    return out
