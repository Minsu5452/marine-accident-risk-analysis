"""국립해양측위정보원(NMPNT) 해양기상 수집기.

공식 매뉴얼: https://marineweather.nmpnt.go.kr/serviceReq/serviceOpenApiIntro.do
- 지점 목록: POST getStationInfo.json → 76개 지점(기관코드·지점코드·지점명·관측항목).
  좌표는 여기 없고 기상 레코드(LATITUDE/LONGITUDE)에서 얻는다.
- 날짜별 기상: GET openWeatherDate.do?serviceKey=..&date=YYYYMMDD&mmaf=..&mmsi=..&dataType=1
- 최신 기상: GET openWeatherNow.do?serviceKey=..&mmaf=..&mmsi=..&dataType=2
응답은 UTF-8 JSON. 값은 문자열로 오고, 풍향(WIND_DIRECT)은 도(degree) 단위다.
파고·파향(WAVE_*)은 매뉴얼엔 있으나 76개 지점 모두 미제공이다.

서비스키는 환경변수 NMPNT_SERVICE_KEY로만 주입한다(레포엔 이름만). 기상 엔드포인트는
HTTP 전용이라 키가 평문으로 오가는데, NMPNT가 HTTPS를 제공하지 않는 외부 제약이다.
"""

from __future__ import annotations

from typing import Any

import httpx
import numpy as np
import pandas as pd
from pydantic import BaseModel
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

# 일부 호출은 브라우저 User-Agent를 요구한다.
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
DATA_BASE = "http://marineweather.nmpnt.go.kr:8001"
NOW_URL = f"{DATA_BASE}/openWeatherNow.do"
DATE_URL = f"{DATA_BASE}/openWeatherDate.do"
# getStationInfo는 https인데 인증서 체인이 불완전해 verify=False가 필요하다(공공 호스트 설정 문제).
STATION_URL = "https://marineweather.nmpnt.go.kr/serviceReq/getStationInfo.json"

# NMPNT 기상 응답 필드(대문자 스네이크) → 분석용 필드명.
WEATHER_FIELDS: dict[str, str] = {
    "DATETIME": "observed_at",
    "MMAF_CODE": "mmaf_code",
    "MMAF_NM": "mmaf_name",
    "MMSI_CODE": "station_code",
    "MMSI_NM": "station_name",
    "WIND_DIRECT": "wind_dir",        # 풍향(degree)
    "WIND_SPEED": "wind_speed",
    "AIR_TEMPERATURE": "air_temp",
    "HUMIDITY": "humidity",
    "AIR_PRESSURE": "air_pressure",
    "WATER_TEMPER": "water_temp",
    "SALINITY": "salinity",
    "HORIZON_VISIBL": "visibility",
    "SURFACE_CURR_DRC": "current_dir",
    "SURFACE_CURR_SPEED": "current_speed",
    "WAVE_DRC": "wave_dir",
    "WAVE_HEIGTH": "wave_height",      # API 원문 철자(HEIGTH) 유지
    "TIDE_SPEED": "tide_speed",
    "LATITUDE": "lat",
    "LONGITUDE": "lon",
}
META_FIELDS = ("mmaf_code", "mmaf_name", "station_code", "station_name")
# 각도 변수 — 시간 리샘플 때 벡터(원형) 평균.
ANGLE_FIELDS = ("wind_dir", "current_dir", "wave_dir")
# 스칼라 변수 — 시간 리샘플 때 산술 평균(좌표 포함, 지점당 상수).
SCALAR_FIELDS = (
    "wind_speed", "air_temp", "humidity", "air_pressure",
    "water_temp", "salinity", "visibility", "current_speed",
    "wave_height", "tide_speed", "lat", "lon",
)
NUMERIC_FIELDS = ANGLE_FIELDS + SCALAR_FIELDS


class Station(BaseModel):
    """NMPNT 관측 지점. 좌표는 getStationInfo에 없어 기상 레코드로 보강한다."""

    mmaf_code: str       # 기관코드(mmafCode)
    mmaf_name: str       # 지방청명(mmafNm)
    station_code: str    # 지점코드(mmsi)
    station_name: str    # 지점명(stationNm)
    observe_items: list[str] = []  # 관측 항목(observeItems 파싱)
    lat: float | None = None
    lon: float | None = None


def make_client(*, verify: bool = True, timeout: float = 30.0) -> httpx.Client:
    """기본 User-Agent를 단 httpx 클라이언트. 지점 호출은 verify=False가 필요하다."""
    return httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=timeout, verify=verify)


def _is_retryable(exc: BaseException) -> bool:
    """일시적 오류(연결·타임아웃 등 전송 오류·5xx)만 재시도한다. 4xx(키·날짜 오류 등)는 즉시 실패."""
    if isinstance(exc, httpx.TransportError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code >= 500
    return False


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, max=10),
    retry=retry_if_exception(_is_retryable),
    reraise=True,
)
def _request(client: httpx.Client, method: str, url: str, **kwargs: Any) -> httpx.Response:
    r = client.request(method, url, **kwargs)
    r.raise_for_status()
    return r


def _circular_mean(deg: pd.Series) -> float:
    """각도(도) 시리즈의 원형 평균. 결측은 제외, 전부 결측이면 NaN."""
    vals = pd.to_numeric(deg, errors="coerce").dropna()
    if vals.empty:
        return float("nan")
    rad = np.deg2rad(vals.to_numpy())
    ang = float(np.degrees(np.arctan2(np.sin(rad).mean(), np.cos(rad).mean())) % 360.0)
    # 부동소수점 때문에 360에 근접하면 0으로 맞춘다(범위 [0, 360))
    return 0.0 if abs(ang - 360.0) < 1e-9 else ang


def parse_station_record(rec: dict) -> Station:
    """getStationInfo의 레코드 1건을 Station으로 변환한다."""
    items = [s.strip() for s in str(rec.get("observeItems", "")).split(",") if s.strip()]
    return Station(
        mmaf_code=str(rec.get("mmafCode", "")),
        mmaf_name=str(rec.get("mmafNm", "")),
        station_code=str(rec.get("mmsi", "")),
        station_name=str(rec.get("stationNm", "")),
        observe_items=items,
    )


def fetch_stations(client: httpx.Client) -> list[Station]:
    """지점 목록을 받아 Station 리스트로 돌려준다(좌표 없음)."""
    r = _request(client, "POST", STATION_URL, data={"mmafitem": "", "item": "ALL", "stationNm": ""})
    result = r.json().get("result", [])
    return [parse_station_record(rec) for rec in result]


def parse_weather(recordset: list[dict]) -> pd.DataFrame:
    """기상 recordset을 분석용 컬럼명·타입의 DataFrame으로 변환한다.

    - 필드를 WEATHER_FIELDS로 개명, 알 수 없는 컬럼은 버린다.
    - observed_at을 datetime(YYYYMMDDHHMMSS)으로, 수치 필드를 float으로 파싱한다.
    - 지점마다 센서가 달라 존재하는 컬럼만 담는다(없는 변수는 컬럼 자체가 없음).
    """
    if not recordset:
        return pd.DataFrame()
    df = pd.DataFrame(recordset).rename(columns=WEATHER_FIELDS)
    df = df[[c for c in WEATHER_FIELDS.values() if c in df.columns]].copy()
    if "observed_at" in df.columns:
        df["observed_at"] = pd.to_datetime(df["observed_at"], format="%Y%m%d%H%M%S", errors="coerce")
    for field in NUMERIC_FIELDS:
        if field in df.columns:
            df[field] = pd.to_numeric(df[field], errors="coerce")
    return df


def resample_hourly(df: pd.DataFrame) -> pd.DataFrame:
    """10분 관측을 지점×시(hour)로 리샘플한다(스칼라 평균, 각도 벡터 평균).

    observed_at이 결측(NaT)인 행은 시간 그룹을 만들 수 없어 명시적으로 제외한다.
    """
    if df.empty:
        return pd.DataFrame()
    df = df.dropna(subset=["observed_at"]).copy()
    if df.empty:
        return pd.DataFrame()
    df["observed_hour"] = df["observed_at"].dt.floor("h")
    rows: list[dict[str, Any]] = []
    for (station_code, hour), g in df.groupby(["station_code", "observed_hour"], sort=False):
        row: dict[str, Any] = {"station_code": station_code, "observed_hour": hour, "n_obs": len(g)}
        for field in META_FIELDS:
            if field != "station_code" and field in g.columns:
                row[field] = g[field].iloc[0]
        for field in SCALAR_FIELDS:
            if field in g.columns:
                row[field] = g[field].mean()
        for field in ANGLE_FIELDS:
            if field in g.columns:
                row[field] = _circular_mean(g[field])
        rows.append(row)
    return pd.DataFrame(rows)


def fetch_weather_date(
    client: httpx.Client,
    *,
    service_key: str,
    date: str,
    mmsi: str | list[str],
    mmaf: str = "",
    data_type: int = 1,
) -> list[dict]:
    """날짜별(과거) 기상 recordset(raw dict 리스트)을 받는다. date=YYYYMMDD."""
    mmsi_param = ",".join(mmsi) if isinstance(mmsi, (list, tuple)) else mmsi
    params = {
        "serviceKey": service_key, "resultType": "json", "date": date,
        "mmaf": mmaf, "mmsi": mmsi_param, "dataType": str(data_type),
    }
    r = _request(client, "GET", DATE_URL, params=params)
    result = r.json().get("result", {})
    return result.get("recordset", []) or []


def fetch_weather_now(
    client: httpx.Client,
    *,
    service_key: str,
    mmsi: str | list[str] = "",
    mmaf: str = "",
    data_type: int = 2,
) -> list[dict]:
    """최신 기상 recordset(raw dict 리스트)을 받는다(라이브 모드용)."""
    mmsi_param = ",".join(mmsi) if isinstance(mmsi, (list, tuple)) else mmsi
    params = {
        "serviceKey": service_key, "resultType": "json",
        "mmaf": mmaf, "mmsi": mmsi_param, "dataType": str(data_type),
    }
    r = _request(client, "GET", NOW_URL, params=params)
    result = r.json().get("result", {})
    return result.get("recordset", []) or []
