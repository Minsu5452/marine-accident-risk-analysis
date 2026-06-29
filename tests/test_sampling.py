import pandas as pd

from marine_accident_risk.grid.sampling import sample_negative_cells

HOURS = pd.to_datetime(
    [
        "2020-03-01 00:00:00",
        "2020-03-01 01:00:00",
        "2020-03-01 02:00:00",
        "2020-03-01 03:00:00",
        "2020-03-01 04:00:00",
    ]
)
CELLS = pd.DataFrame(
    {
        "grid_id": ["0.1:1_1", "0.1:1_2", "0.1:2_1"],
        "grid_lat_center": [35.15, 35.15, 35.25],
        "grid_lon_center": [129.15, 129.25, 129.15],
    }
)
POSITIVES = pd.DataFrame(
    {"grid_id": ["0.1:1_1", "0.1:1_2"], "hour": pd.to_datetime(["2020-03-01 00:00:00", "2020-03-01 01:00:00"])}
)


def test_ratio_count():
    neg = sample_negative_cells(POSITIVES, CELLS, HOURS, ratio=3, seed=0)
    assert len(neg) == 6  # 양성 2개 × 3


def test_no_overlap_with_positives():
    neg = sample_negative_cells(POSITIVES, CELLS, HOURS, ratio=3, seed=0)
    pos_keys = set(zip(POSITIVES["grid_id"], POSITIVES["hour"]))
    neg_keys = set(zip(neg["grid_id"], neg["hour"]))
    assert pos_keys.isdisjoint(neg_keys)  # 음성에 양성 셀이 섞이지 않는다
    assert len(neg_keys) == len(neg)  # 중복 없음


def test_cells_and_hours_within_support():
    neg = sample_negative_cells(POSITIVES, CELLS, HOURS, ratio=3, seed=0)
    assert set(neg["grid_id"]) <= set(CELLS["grid_id"])
    assert set(neg["hour"]) <= set(HOURS)
    # 셀 중심 좌표가 따라온다
    assert "grid_lat_center" in neg.columns


def test_deterministic_with_seed():
    a = sample_negative_cells(POSITIVES, CELLS, HOURS, ratio=2, seed=42)
    b = sample_negative_cells(POSITIVES, CELLS, HOURS, ratio=2, seed=42)
    assert a.equals(b)
