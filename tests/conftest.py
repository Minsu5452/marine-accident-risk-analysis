from pathlib import Path

import pandas as pd
import pytest

from marine_accident_risk.data.mtis import COLUMN_MAP, SHEET_NAME

# 분석용 필드명 → 원본 한글 컬럼명(픽스처 xlsx를 실제 파일과 같은 헤더로 만들기 위한 역매핑).
# COLUMN_MAP 값은 유일해서 역매핑이 안전하다.
_SRC = {v: k for k, v in COLUMN_MAP.items()}
_FIELDS = list(COLUMN_MAP.values())


def _row(name: str, occurred: str, atype: str, lat, lon, **kw) -> dict:
    base = {
        "incident_name": name,
        "occurred_at": occurred,
        "accident_type": atype,
        "safety_type": None,
        "deaths": 0,
        "missing": 0,
        "deaths_missing": 0,
        "injuries": 0,
        "sea_area": "서해영해",
        "vessel_use": "어선",
        "vessel_use_l": "어선",
        "vessel_use_m": "연안어업선",
        "vessel_use_s": "기타",
        "tonnage": 1.0,
        "tonnage_class": "2톤 미만",
        "lat": lat,
        "lon": lon,
    }
    base.update(kw)
    return base


@pytest.fixture()
def accident_rows() -> list[dict]:
    """정상 2건 + 좌표 이상치 2건(음수 위도·경도 200대) + 결측 1건을 섞은 작은 표."""
    return [
        _row("정상사건A", "2020-03-01 09:30:00", "충돌", 34.81, 126.40),
        _row("정상사건B", "2021-07-15 18:05:00", "좌초", 37.47, 126.59),
        _row("이상치_경도", "2019-01-01 00:10:00", "침수", 36.05, 232.066667),
        _row("이상치_위도", "2018-11-20 23:50:00", "전복", -72.133, 126.40),
        _row("결측좌표", "2022-05-05 05:05:00", "화재", None, 127.0),
    ]


@pytest.fixture()
def accident_df(accident_rows: list[dict]) -> pd.DataFrame:
    """분석용 필드명(개명 후)을 가진 DataFrame — clean_coordinates 직접 테스트용."""
    return pd.DataFrame([{f: r[f] for f in _FIELDS} for r in accident_rows])


@pytest.fixture()
def mtis_xlsx(tmp_path: Path, accident_rows: list[dict]) -> Path:
    """실제 파일과 같은 한글 헤더·시트명으로 작은 xlsx를 만든다 — load_mtis_accidents 테스트용."""
    df = pd.DataFrame([{_SRC[f]: r[f] for f in _FIELDS} for r in accident_rows])
    p = tmp_path / "mtis_sample.xlsx"
    df.to_excel(p, sheet_name=SHEET_NAME, index=False)
    return p
