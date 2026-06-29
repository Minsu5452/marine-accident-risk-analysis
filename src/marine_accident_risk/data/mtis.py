"""MTIS(KOMSA) 해양사고 엑셀 로더.

원본은 한국해양교통안전공단(KOMSA) MTIS "GIS기반 해양사고분석" 엑셀(시트 `사고목록`)로,
중앙해양안전심판원(KMST) 통계를 정제한 형태다. 원본·가공본은 레포에 커밋하지 않는다
(README 데이터 준비 절차 참고).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

SHEET_NAME = "사고목록"

# 원본 한글 컬럼(공백 제거 기준) → 분석용 필드명.
# 위·경도 컬럼명에는 º(U+00BA)가 섞여 있어 별도 접두 매칭으로 보강한다(_rename_map).
COLUMN_MAP: dict[str, str] = {
    "사건명": "incident_name",
    "사고발생일시": "occurred_at",
    "사고종류": "accident_type",
    "안전사고유형": "safety_type",        # 약 96% 결측 → 분석에서 제외
    "사망자(명)": "deaths",
    "실종자(명)": "missing",
    "사망·실종자(명)": "deaths_missing",
    "부상자(명)": "injuries",
    "해역": "sea_area",
    "선박용도(통계)": "vessel_use",
    "선박용도(대)": "vessel_use_l",
    "선박용도(중)": "vessel_use_m",
    "선박용도(소)": "vessel_use_s",
    "선박톤수(톤)": "tonnage",
    "선박톤수(통계)": "tonnage_class",
    "위도(º)": "lat",
    "경도(º)": "lon",
}

# 이 세 필드는 이후 단계(좌표 정제·시간 처리)의 전제라 반드시 있어야 한다.
REQUIRED_FIELDS = ("occurred_at", "lat", "lon")


def _rename_map(columns: list[str]) -> dict[str, str]:
    """원본 컬럼 → 분석용 필드명 매핑. 위·경도는 º 표기 변형에 대비해 접두로 보강한다."""
    out: dict[str, str] = {}
    for c in columns:
        key = str(c).replace(" ", "")
        target = COLUMN_MAP.get(key)
        if target is None:
            if key.startswith("위도"):
                target = "lat"
            elif key.startswith("경도"):
                target = "lon"
        if target is not None:
            out[c] = target
    return out


def load_mtis_accidents(path: str | Path, *, sheet: str = SHEET_NAME) -> pd.DataFrame:
    """MTIS 엑셀을 읽어 분석용 컬럼명·타입으로 정규화한 DataFrame을 돌려준다.

    - 컬럼을 분석용 필드명으로 일괄 개명한다(위·경도는 접두 매칭으로 보강).
    - occurred_at을 datetime으로 파싱한다.
    - lat/lon을 float으로 강제한다(파싱 실패는 NaN).

    좌표 이상치 정제는 하지 않는다. 그건 clean_coordinates가 따로 맡는다.
    """
    df = pd.read_excel(Path(path), sheet_name=sheet)
    df = df.rename(columns=_rename_map(list(df.columns)))
    missing = [f for f in REQUIRED_FIELDS if f not in df.columns]
    if missing:
        raise ValueError(f"필수 필드 누락(원본 컬럼명을 확인하세요): {missing}")
    df["occurred_at"] = pd.to_datetime(df["occurred_at"], errors="coerce")
    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lon"] = pd.to_numeric(df["lon"], errors="coerce")
    return df
