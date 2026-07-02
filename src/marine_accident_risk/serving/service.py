"""위험도 서비스 — 학습셋과 리포트를 읽어 격자 위험·셀 상세를 메모리에 올린다.

학습셋(build_dataset 산출)에 로지스틱을 적합해 격자별 평균 위험도와 과거 사고 수를
집계하고, 통계·XAI 리포트(JSON)를 그대로 제공한다. 무거운 적합은 시작 시 한 번만 한다.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from ..modeling.features import add_time_features, build_xy
from ..modeling.models import logistic_factory

WEATHER = ["wind_speed", "air_temp", "air_pressure", "humidity", "visibility"]
SPATIAL = ["lat", "lon"]
TIME_NUMERIC = ["hour", "is_night", "month"]


class RiskService:
    """격자 위험·셀 상세·리포트를 제공한다."""

    def __init__(self, cache_dir: str | Path, reports_dir: str | Path, resolution: float = 0.1):
        self.cache_dir = Path(cache_dir)
        self.reports_dir = Path(reports_dir)
        self.resolution = resolution
        self._build()

    def _build(self) -> None:
        df = add_time_features(
            pd.read_csv(self.cache_dir / f"dataset_{self.resolution}.csv", parse_dates=["occurred_hour"])
        )
        numeric = [c for c in [*WEATHER, *SPATIAL, *TIME_NUMERIC] if c in df.columns and df[c].notna().mean() > 0.5]
        x, y, self.features = build_xy(df, numeric=numeric, categorical=["season"], label_col="label")
        model = logistic_factory().fit(x, y)
        kept = df.dropna(subset=[*numeric, "label"]).reset_index(drop=True)
        kept = kept.assign(risk=model.predict_proba(x)[:, 1])
        self._grid = (
            kept.groupby("grid_id")
            .agg(
                lat=("lat", "first"),
                lon=("lon", "first"),
                risk=("risk", "mean"),
                accidents=("label", "sum"),
                samples=("label", "size"),
            )
            .reset_index()
            .sort_values("risk", ascending=False)
        )

    def grid(self) -> list[dict]:
        return [
            {
                "grid_id": r.grid_id,
                "lat": round(float(r.lat), 5),
                "lon": round(float(r.lon), 5),
                "risk": round(float(r.risk), 4),
                "accidents": int(r.accidents),
                "samples": int(r.samples),
            }
            for r in self._grid.itertuples()
        ]

    def cell(self, grid_id: str) -> dict | None:
        row = self._grid[self._grid["grid_id"] == grid_id]
        if row.empty:
            return None
        r = row.iloc[0]
        rank = int((self._grid["risk"] > r["risk"]).sum()) + 1
        return {
            "grid_id": grid_id,
            "lat": round(float(r["lat"]), 5),
            "lon": round(float(r["lon"]), 5),
            "risk": round(float(r["risk"]), 4),
            "risk_rank": rank,
            "total_cells": int(len(self._grid)),
            "accidents": int(r["accidents"]),
            "samples": int(r["samples"]),
            "contributing_factors": self._top_factors(),
        }

    def _top_factors(self, k: int = 4) -> list[dict]:
        """전역 XAI 오즈비 상위(위험을 높이는 변수)를 셀 근거로 제공한다."""
        try:
            data = self.xai()
        except FileNotFoundError:
            return []
        ors = [o for o in data.get("odds_ratios", []) if o["feature"] != "(상수)"]
        ors.sort(key=lambda o: o["odds_ratio"], reverse=True)
        return ors[:k]

    def _report(self, rel: str) -> dict:
        path = self.reports_dir / rel
        if not path.exists():
            raise FileNotFoundError(rel)
        return json.loads(path.read_text(encoding="utf-8"))

    def stats(self) -> dict:
        return self._report("stats/case_crossover.json")

    def xai(self) -> dict:
        return self._report("xai/odds_ratios.json")

    def model_metrics(self) -> dict:
        return self._report("model/metrics.json")
