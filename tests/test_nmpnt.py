import json
import math
from pathlib import Path

import httpx
import pandas as pd
import pytest
import respx

from marine_accident_risk.data.nmpnt import (
    DATE_URL,
    NOW_URL,
    STATION_URL,
    _circular_mean,
    fetch_stations,
    fetch_weather_date,
    fetch_weather_now,
    make_client,
    parse_weather,
    resample_hourly,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


# ---- 순수 함수 ----

def test_circular_mean_wraps_around_zero():
    # 350°와 10°의 평균은 산술 평균(180°)이 아니라 0°다
    assert _circular_mean(pd.Series([350.0, 10.0])) == pytest.approx(0.0, abs=1e-6)


def test_circular_mean_all_missing_is_nan():
    assert math.isnan(_circular_mean(pd.Series([None, None], dtype="float64")))


def test_parse_weather_renames_types_and_mixed_sensors():
    rs = _load("nmpnt_weather_response.json")["result"]["recordset"]
    df = parse_weather(rs)
    assert len(df) == 3
    assert {"observed_at", "station_code", "wind_dir", "wind_speed", "lat"} <= set(df.columns)
    assert pd.api.types.is_datetime64_any_dtype(df["observed_at"])
    assert pd.api.types.is_float_dtype(df["wind_speed"])
    # 여수 견내량은 수온·시정·유속 센서가 있다
    yeosu = df[df["station_code"] == "994401584"].iloc[0]
    assert yeosu["water_temp"] == 14.2
    assert yeosu["visibility"] == 1000.0
    assert yeosu["current_dir"] == 187.0
    # 부산 남항동 레코드엔 수온 센서가 없어 NaN
    busan = df[df["station_code"] == "1019001"]
    assert busan["water_temp"].isna().all()


def test_parse_weather_empty():
    assert parse_weather([]).empty


def test_resample_hourly_scalar_and_vector_mean():
    df = pd.DataFrame(
        {
            "observed_at": pd.to_datetime(
                ["2024-01-15 10:00:00", "2024-01-15 10:10:00", "2024-01-15 11:00:00"]
            ),
            "station_code": ["A", "A", "A"],
            "station_name": ["남항동", "남항동", "남항동"],
            "mmaf_code": ["101", "101", "101"],
            "wind_dir": [350.0, 10.0, 90.0],
            "wind_speed": [10.0, 20.0, 5.0],
            "air_temp": [5.0, 7.0, 6.0],
            "lat": [35.0, 35.0, 35.0],
            "lon": [129.0, 129.0, 129.0],
        }
    )
    out = resample_hourly(df).sort_values("observed_hour").reset_index(drop=True)
    assert len(out) == 2
    assert list(out["n_obs"]) == [2, 1]
    assert out.loc[0, "wind_speed"] == 15.0          # 스칼라 산술 평균
    assert out.loc[0, "air_temp"] == 6.0
    assert out.loc[0, "wind_dir"] == pytest.approx(0.0, abs=1e-6)  # 각도 벡터 평균
    assert out.loc[0, "station_name"] == "남항동"      # 메타 유지
    assert out.loc[0, "lat"] == 35.0                 # 좌표 유지
    assert out.loc[1, "wind_speed"] == 5.0


# ---- 네트워크(mock) ----

@respx.mock
def test_fetch_stations_parses_list():
    respx.post(STATION_URL).mock(
        return_value=httpx.Response(200, json=_load("nmpnt_stations_response.json"))
    )
    with make_client(verify=False) as client:
        stations = fetch_stations(client)
    assert len(stations) == 2
    s0 = stations[0]
    assert s0.mmaf_code == "101"
    assert s0.station_code == "1019001"
    assert s0.station_name == "남항동방파제등대"
    assert "풍향" in s0.observe_items and "기압" in s0.observe_items
    assert s0.lat is None  # 좌표는 getStationInfo에 없다


@respx.mock
def test_fetch_weather_date_sends_params_and_returns_records():
    route = respx.get(DATE_URL).mock(
        return_value=httpx.Response(200, json=_load("nmpnt_weather_response.json"))
    )
    with make_client() as client:
        rs = fetch_weather_date(
            client, service_key="K", date="20240115", mmsi=["1019001", "994401584"], mmaf="101"
        )
    assert len(rs) == 3
    params = route.calls.last.request.url.params
    assert params["serviceKey"] == "K"
    assert params["date"] == "20240115"
    assert params["resultType"] == "json"
    assert params["dataType"] == "1"
    assert params["mmsi"] == "1019001,994401584"  # 리스트는 콤마로 합쳐 보낸다


@respx.mock
def test_fetch_weather_now_sends_params_without_date():
    route = respx.get(NOW_URL).mock(
        return_value=httpx.Response(200, json=_load("nmpnt_weather_response.json"))
    )
    with make_client() as client:
        rs = fetch_weather_now(client, service_key="K", mmsi="1019001", mmaf="101")
    assert len(rs) == 3
    params = route.calls.last.request.url.params
    assert params["serviceKey"] == "K"
    assert params["dataType"] == "2"        # 최신 호출 기본 dataType
    assert "date" not in params             # 최신 호출엔 date가 없다
