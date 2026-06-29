import numpy as np
import pandas as pd

from marine_accident_risk.modeling.features import add_time_features, build_xy


def test_add_time_features_derives_season_and_night():
    df = pd.DataFrame(
        {"occurred_hour": pd.to_datetime(["2020-12-15 23:00:00", "2020-06-15 10:00:00"])}
    )
    out = add_time_features(df)
    assert list(out["month"]) == [12, 6]
    assert list(out["hour"]) == [23, 10]
    assert list(out["season"]) == ["겨울", "여름"]
    assert list(out["is_night"]) == [1, 0]
    assert out.loc[0, "dow"] == 1  # 2020-12-15 = 화요일(월=0)


def test_build_xy_drops_nan_and_onehots_categorical():
    df = pd.DataFrame(
        {
            "wind": [1.0, 2.0, np.nan, 4.0],
            "season": ["겨울", "여름", "봄", "겨울"],
            "label": [1, 0, 1, 0],
        }
    )
    X, y, names = build_xy(df, numeric=["wind"], categorical=["season"], label_col="label")
    assert len(X) == 3  # wind 결측 행 제거
    assert list(y) == [1, 0, 0]
    assert "wind" in names
    assert any(n.startswith("season_") for n in names)  # season one-hot
