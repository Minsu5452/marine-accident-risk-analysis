import pandas as pd
import pytest

from marine_accident_risk.data.mtis import load_mtis_accidents


def test_renames_columns_and_parses_datetime(mtis_xlsx):
    df = load_mtis_accidents(mtis_xlsx)
    assert {"incident_name", "occurred_at", "accident_type", "lat", "lon"} <= set(df.columns)
    assert pd.api.types.is_datetime64_any_dtype(df["occurred_at"])
    assert pd.api.types.is_float_dtype(df["lat"])
    assert pd.api.types.is_float_dtype(df["lon"])
    assert len(df) == 5


def test_loader_does_not_clean_outliers(mtis_xlsx):
    # 로더는 좌표 정제를 하지 않는다 — 이상치 행도 그대로 읽어 정제 단계로 넘긴다
    df = load_mtis_accidents(mtis_xlsx)
    assert df["lon"].max() > 200
    assert df["lat"].min() < 0


def test_missing_sheet_raises(mtis_xlsx):
    # 없는 시트는 openpyxl/pandas에서 ValueError로 발생한다
    with pytest.raises(ValueError):
        load_mtis_accidents(mtis_xlsx, sheet="없는시트")
