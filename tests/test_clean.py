import pandas as pd

from marine_accident_risk.data.clean import CleaningReport, clean_coordinates

BBOX = {"lat_min": 32.0, "lat_max": 39.0, "lon_min": 124.0, "lon_max": 132.0}


def test_removes_out_of_bbox_and_missing(accident_df):
    cleaned, report = clean_coordinates(accident_df, **BBOX)
    assert len(cleaned) == 2  # 정상 2건만 남는다
    assert isinstance(report, CleaningReport)
    assert report.total == 5
    assert report.kept == 2
    assert report.removed == 3
    assert report.removed_out_of_bbox == 2
    assert report.removed_missing == 1


def test_kept_rows_within_bbox(accident_df):
    cleaned, _ = clean_coordinates(accident_df, **BBOX)
    assert cleaned["lat"].between(32.0, 39.0).all()
    assert cleaned["lon"].between(124.0, 132.0).all()
    assert list(cleaned.index) == [0, 1]  # 인덱스 리셋 확인


def test_report_as_dict(accident_df):
    _, report = clean_coordinates(accident_df, **BBOX)
    d = report.as_dict()
    assert d["removed"] == 3
    assert d["bbox"]["lat_min"] == 32.0
    assert d["bbox"]["lon_max"] == 132.0


def test_bbox_boundary_inclusive():
    # between(inclusive='both')이라 경계값은 포함, 경계 직전·직후는 제외한다
    df = pd.DataFrame(
        {
            "lat": [32.0, 39.0, 35.0, 31.999, 35.0],
            "lon": [124.0, 132.0, 132.001, 128.0, 128.0],
        }
    )
    cleaned, report = clean_coordinates(df, **BBOX)
    assert report.kept == 3  # (32.0,124.0)·(39.0,132.0)·(35.0,128.0)
    assert report.removed_out_of_bbox == 2
    assert report.removed_missing == 0
    assert (32.0 in set(cleaned["lat"])) and (39.0 in set(cleaned["lat"]))
