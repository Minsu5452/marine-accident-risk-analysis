"""negative sampling — 무사고 격자×시간 셀 추출.

학습셋은 사고가 난 (격자, 시간) 셀(양성)과 사고가 없던 셀(음성)으로 구성한다.
음성은 사고가 한 번이라도 난 연안 격자들(사고의 공간 범위)과 분석 기간의 시간들에서,
양성 셀을 빼고 무작위로 양성 수의 ratio배만큼 뽑는다. 시드로 재현 가능하다.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def sample_negative_cells(
    positives: pd.DataFrame,
    coastal_cells: pd.DataFrame,
    hours: pd.Series | list,
    *,
    ratio: int = 3,
    seed: int = 0,
) -> pd.DataFrame:
    """무사고 (grid_id, hour) 셀을 양성 수의 ratio배만큼 무작위 추출한다.

    positives: grid_id·hour 컬럼(양성 셀). coastal_cells: grid_id·grid_lat_center·grid_lon_center
    (음성을 뽑을 공간). hours: 추출 대상 시각들. 반환: grid_id·hour·grid_lat_center·grid_lon_center.
    공간이 모자라면 가능한 만큼만 돌려준다.
    """
    rng = np.random.default_rng(seed)
    pos_keys = set(zip(positives["grid_id"], pd.to_datetime(positives["hour"]), strict=True))
    hours_arr = pd.to_datetime(pd.Series(list(hours))).to_numpy()
    cell_ids = coastal_cells["grid_id"].to_numpy()
    centers = coastal_cells.set_index("grid_id")[["grid_lat_center", "grid_lon_center"]].to_dict("index")

    n_target = ratio * len(positives)
    capacity = len(cell_ids) * len(hours_arr) - len(pos_keys)
    n_target = min(n_target, max(capacity, 0))

    chosen: set[tuple] = set()
    rows: list[dict] = []
    attempts = 0
    max_attempts = n_target * 50 + 1000
    while len(rows) < n_target and attempts < max_attempts:
        attempts += 1
        c = cell_ids[int(rng.integers(len(cell_ids)))]
        h = pd.Timestamp(hours_arr[int(rng.integers(len(hours_arr)))])
        key = (c, h)
        if key in pos_keys or key in chosen:
            continue
        chosen.add(key)
        rows.append(
            {
                "grid_id": c,
                "hour": h,
                "grid_lat_center": centers[c]["grid_lat_center"],
                "grid_lon_center": centers[c]["grid_lon_center"],
            }
        )
    return pd.DataFrame(rows)
