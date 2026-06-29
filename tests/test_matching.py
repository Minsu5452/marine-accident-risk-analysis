import pandas as pd
import pytest

from marine_accident_risk.matching.matching import (
    haversine_km,
    match_accidents_to_weather,
    nearest_station,
)


@pytest.fixture()
def stations():
    return pd.DataFrame(
        {"station_code": ["A", "B"], "lat": [35.0, 34.0], "lon": [129.0, 127.0]}
    )


@pytest.fixture()
def weather_hourly():
    h9 = pd.Timestamp("2020-03-01 09:00:00")
    return pd.DataFrame(
        {
            "station_code": ["A", "B"],
            "observed_hour": [h9, h9],
            "wind_speed": [10.0, 3.0],
            "air_temp": [5.0, 8.0],
            "lat": [35.0, 34.0],
            "lon": [129.0, 127.0],
        }
    )


def test_haversine_one_degree_lat_is_about_111km():
    assert float(haversine_km(35.0, 129.0, 36.0, 129.0)) == pytest.approx(111.19, abs=0.5)


def test_nearest_station_picks_closest(stations):
    code, dist = nearest_station(35.01, 129.01, stations)
    assert code == "A"
    assert dist < 2.0  # 1km 남짓


def test_match_attaches_weather_for_in_range(stations, weather_hourly):
    acc = pd.DataFrame(
        {
            "lat": [35.01, 34.01],
            "lon": [129.01, 127.01],
            "occurred_at": pd.to_datetime(["2020-03-01 09:20:00", "2020-03-01 09:30:00"]),
        }
    )
    out = match_accidents_to_weather(acc, weather_hourly, stations, max_km=60.0)
    assert list(out["match_status"]) == ["matched", "matched"]
    assert out.loc[0, "match_station"] == "A"
    assert out.loc[0, "wind_speed"] == 10.0  # A의 09시 기상
    assert out.loc[1, "wind_speed"] == 3.0  # B의 09시 기상
    assert out.loc[0, "occurred_hour"] == pd.Timestamp("2020-03-01 09:00:00")


def test_match_no_station_when_beyond_threshold(stations, weather_hourly):
    acc = pd.DataFrame(
        {"lat": [38.0], "lon": [131.5], "occurred_at": pd.to_datetime(["2020-03-01 09:20:00"])}
    )
    out = match_accidents_to_weather(acc, weather_hourly, stations, max_km=60.0)
    assert out.loc[0, "match_status"] == "no_station"
    assert pd.isna(out.loc[0, "wind_speed"])


def test_match_no_weather_when_hour_missing(stations, weather_hourly):
    acc = pd.DataFrame(
        {"lat": [35.01], "lon": [129.01], "occurred_at": pd.to_datetime(["2020-03-01 12:00:00"])}
    )
    out = match_accidents_to_weather(acc, weather_hourly, stations, max_km=60.0)
    assert out.loc[0, "match_status"] == "no_weather"  # A는 가깝지만 12시 기상 없음
    assert pd.isna(out.loc[0, "wind_speed"])
