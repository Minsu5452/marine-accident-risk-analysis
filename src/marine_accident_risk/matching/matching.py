"""사고-기상 최근접 매칭.

각 사고에 대해 거리 임계(기본 ~60km) 안의 가장 가까운 관측 지점을 찾고, 사고 시각이
속한 시간(hour)의 그 지점 기상을 붙인다. 임계 밖이거나 해당 시간 기상이 없으면 결측 처리한다.
거리는 haversine(구면 근사)로 계산한다 — 약 60km 임계 판단에 충분하다.

match_status:
- matched: 임계 안 최근접 지점의 해당 시간 기상을 붙임
- no_station: 임계 안에 지점이 없음(또는 좌표 결측)
- no_weather: 임계 안 지점은 있으나 그 시간 기상이 없음
"""

from __future__ import annotations

import numpy as np
import pandas as pd

EARTH_RADIUS_KM = 6371.0
# 지점 식별·좌표·시간은 기상 변수가 아니므로 매칭 결과에 붙이지 않는다.
_NON_WEATHER = {"station_code", "observed_hour", "mmaf_code", "mmaf_name", "station_name", "lat", "lon"}


def haversine_km(
    lat1: float | np.ndarray,
    lon1: float | np.ndarray,
    lat2: float | np.ndarray,
    lon2: float | np.ndarray,
) -> np.ndarray:
    """두 좌표(스칼라·배열) 사이 구면 거리(km)."""
    rlat1, rlon1, rlat2, rlon2 = (np.radians(np.asarray(x, dtype=float)) for x in (lat1, lon1, lat2, lon2))
    dlat = rlat2 - rlat1
    dlon = rlon2 - rlon1
    a = np.sin(dlat / 2) ** 2 + np.cos(rlat1) * np.cos(rlat2) * np.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(a))


def nearest_station(lat: float, lon: float, stations: pd.DataFrame) -> tuple[str, float]:
    """(lat, lon)에서 가장 가까운 지점의 (station_code, 거리km). stations: station_code·lat·lon."""
    d = haversine_km(lat, lon, stations["lat"].to_numpy(dtype=float), stations["lon"].to_numpy(dtype=float))
    i = int(np.argmin(d))
    return str(stations["station_code"].astype(str).to_numpy()[i]), float(d[i])


def match_accidents_to_weather(
    accidents: pd.DataFrame,
    weather_hourly: pd.DataFrame,
    stations: pd.DataFrame,
    *,
    max_km: float = 60.0,
    lat_col: str = "lat",
    lon_col: str = "lon",
    time_col: str = "occurred_at",
) -> pd.DataFrame:
    """사고마다 최근접 지점·거리·해당 시간 기상을 붙인 DataFrame을 돌려준다.

    accidents에 occurred_hour(시각을 시 단위로 내림), nearest_station, station_dist_km,
    match_station, match_status, 그리고 기상 변수 컬럼이 추가된다.
    """
    acc = accidents.copy()
    acc["occurred_hour"] = pd.to_datetime(acc[time_col]).dt.floor("h")

    slat = stations["lat"].to_numpy(dtype=float)
    slon = stations["lon"].to_numpy(dtype=float)
    scode = stations["station_code"].astype(str).to_numpy()
    codes: list[str | None] = []
    dists: list[float] = []
    for la, lo in zip(acc[lat_col].to_numpy(dtype=float), acc[lon_col].to_numpy(dtype=float), strict=True):
        if np.isnan(la) or np.isnan(lo):
            codes.append(None)
            dists.append(float("nan"))
            continue
        d = haversine_km(la, lo, slat, slon)
        i = int(np.argmin(d))
        codes.append(str(scode[i]))
        dists.append(float(d[i]))
    acc["nearest_station"] = codes
    acc["station_dist_km"] = dists
    within = acc["station_dist_km"] <= max_km
    acc["match_station"] = acc["nearest_station"].where(within, other=None)

    weather_cols = [c for c in weather_hourly.columns if c not in _NON_WEATHER]
    w = weather_hourly[["station_code", "observed_hour", *weather_cols]].rename(
        columns={"station_code": "match_station", "observed_hour": "occurred_hour"}
    )
    w = w.copy()
    w["match_station"] = w["match_station"].astype(str)

    merged = acc.merge(w, on=["match_station", "occurred_hour"], how="left", indicator=True)
    within_m = merged["station_dist_km"] <= max_km
    merged["match_status"] = np.where(
        ~within_m.to_numpy(),
        "no_station",
        np.where(merged["_merge"].to_numpy() == "both", "matched", "no_weather"),
    )
    return merged.drop(columns="_merge")
