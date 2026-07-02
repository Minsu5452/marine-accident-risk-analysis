import os
from pathlib import Path

import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """프로젝트 전역 설정. 환경변수(MAR_*)가 yaml보다 우선한다."""

    # 데이터 경로 — 원본·가공본은 커밋하지 않는다(README 데이터 준비 절차 참고)
    mtis_xlsx: Path = Path("data/raw/GIS기반해양사고분석.xlsx")
    cache_dir: Path = Path("data/cache")
    reports_dir: Path = Path("reports")

    # 한국 EEZ를 대략 감싸는 좌표 범위(bbox) — 이 범위 밖 좌표는 이상치로 제거한다
    eez_lat_min: float = 32.0
    eez_lat_max: float = 39.0
    eez_lon_min: float = 124.0
    eez_lon_max: float = 132.0

    # 격자 해상도(도). 세 해상도를 산출하고 대시보드에서 선택한다
    grid_resolutions: list[float] = [0.05, 0.1, 0.25]

    # 사고-기상 최근접 매칭 임계값(거리 km·시간 분)
    match_max_km: float = 60.0
    match_time_window_min: int = 30

    model_config = SettingsConfigDict(env_prefix="MAR_")

    @property
    def eez_bbox(self) -> tuple[float, float, float, float]:
        """(lat_min, lat_max, lon_min, lon_max) 순서의 bbox."""
        return (self.eez_lat_min, self.eez_lat_max, self.eez_lon_min, self.eez_lon_max)


def load_settings(path: Path | None) -> Settings:
    data: dict = {}
    if path is not None:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    env_keys = {k.upper() for k in os.environ}
    data = {k: v for k, v in data.items() if f"MAR_{k.upper()}" not in env_keys}
    return Settings(**data)
