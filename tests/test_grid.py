import numpy as np
import pandas as pd
import pytest

from marine_accident_risk.grid.grid import assign_grid


def test_assign_grid_bins_and_center():
    df = pd.DataFrame({"lat": [34.811667], "lon": [126.401944]})
    out = assign_grid(df, 0.1)
    assert out.loc[0, "grid_lat_bin"] == 348  # floor(34.811667/0.1)
    assert out.loc[0, "grid_lon_bin"] == 1264  # floor(126.401944/0.1)
    assert out.loc[0, "grid_id"] == "0.1:348_1264"
    assert out.loc[0, "grid_lat_center"] == pytest.approx(34.85)  # (348+0.5)*0.1
    assert out.loc[0, "grid_lon_center"] == pytest.approx(126.45)


def test_nearby_points_share_cell_at_coarse_resolution():
    df = pd.DataFrame({"lat": [34.81, 34.86], "lon": [126.41, 126.41]})
    out = assign_grid(df, 0.1)
    assert out.loc[0, "grid_id"] == out.loc[1, "grid_id"]  # 같은 0.1° 셀


def test_finer_resolution_splits_cell():
    df = pd.DataFrame({"lat": [34.81, 34.86], "lon": [126.41, 126.41]})
    out = assign_grid(df, 0.05)
    assert out.loc[0, "grid_id"] != out.loc[1, "grid_id"]  # 0.05°에선 다른 셀


def test_missing_coords_get_none_grid_id():
    df = pd.DataFrame({"lat": [np.nan], "lon": [126.4]})
    out = assign_grid(df, 0.1)
    assert out.loc[0, "grid_id"] is None
