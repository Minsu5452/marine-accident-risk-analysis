"""모델 학습·평가 실행 — 격자×시간 셀의 사고 발생 확률.

해상도별 데이터셋(build_dataset.py 산출)에 시간 특징을 더해, 연도 기준 OOF 교차검증으로
로지스틱 회귀(해석)와 LightGBM(성능 상한)을 비교한다. 비결측 비율이 낮은 변수는 자동 제외한다.

출력: reports/model/metrics.{md,json}
실행: uv run python scripts/run_model.py
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pandas as pd

from marine_accident_risk.config import load_settings
from marine_accident_risk.modeling.evaluate import binary_metrics, oof_predict, threshold_table
from marine_accident_risk.modeling.features import add_time_features, build_xy
from marine_accident_risk.modeling.models import logistic_factory

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "configs" / "default.yaml"
CACHE = ROOT / "data" / "cache"
OUT = ROOT / "reports" / "model"

# 후보 수치 특징(비결측 50% 이상인 것만 사용). season은 범주형으로 따로.
WEATHER_CANDIDATES = ["wind_speed", "air_temp", "air_pressure", "humidity", "visibility"]
SPATIAL = ["lat", "lon"]
TIME_NUMERIC = ["hour", "is_night", "month"]

try:
    import lightgbm  # noqa: F401

    HAS_LGBM = True
except Exception:  # libomp 등으로 import 실패 시 로지스틱만
    HAS_LGBM = False


def _lgbm_factory() -> Any:
    from lightgbm import LGBMClassifier

    return LGBMClassifier(n_estimators=300, class_weight="balanced", verbose=-1, n_jobs=2)


def _select_numeric(df: pd.DataFrame) -> list[str]:
    cols = []
    for c in [*WEATHER_CANDIDATES, *SPATIAL, *TIME_NUMERIC]:
        if c in df.columns and df[c].notna().mean() > 0.5:
            cols.append(c)
    return cols


def _evaluate_resolution(path: Path) -> dict:
    df = pd.read_csv(path, parse_dates=["occurred_hour"])
    df = add_time_features(df, time_col="occurred_hour")
    numeric = _select_numeric(df)
    # build_xy의 dropna(numeric+label)와 동일하게 보존 행을 구해 group(연도)을 정렬한다.
    kept = df.dropna(subset=[*numeric, "label"]).reset_index(drop=True)
    x, y, names = build_xy(df, numeric=numeric, categorical=["season"], label_col="label")
    groups = pd.to_datetime(kept["occurred_hour"]).dt.year.to_numpy()

    models: dict[str, Callable[[], Any]] = {"logistic": logistic_factory}
    if HAS_LGBM:
        models["lightgbm"] = _lgbm_factory

    metrics = {}
    oof_logit = None
    for name, factory in models.items():
        oof = oof_predict(x, y, groups, factory)
        metrics[name] = {k: round(v, 4) for k, v in binary_metrics(y, oof).items()}
        if name == "logistic":
            oof_logit = oof

    thr = threshold_table(y.to_numpy(), oof_logit) if oof_logit is not None else pd.DataFrame()
    return {
        "n": int(len(y)),
        "positives": int(y.sum()),
        "negatives": int((y == 0).sum()),
        "features": names,
        "metrics": metrics,
        "threshold_table": thr.to_dict("records"),
    }


def main() -> None:
    settings = load_settings(CONFIG if CONFIG.exists() else None)
    OUT.mkdir(parents=True, exist_ok=True)
    report: dict = {"has_lightgbm": HAS_LGBM, "by_resolution": {}}
    for res in settings.grid_resolutions:
        path = CACHE / f"dataset_{res}.csv"
        if not path.exists():
            continue
        report["by_resolution"][str(res)] = _evaluate_resolution(path)

    (OUT / "metrics.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# 모델 평가 — 격자×시간 사고 발생 확률",
        "",
        "연도 기준 OOF(out-of-fold) 교차검증으로 시간 누수를 막고, 해석 모델(로지스틱 회귀)과",
        "성능 상한 비교용(LightGBM)을 같은 분할로 평가했습니다. 지표는 AUC·PR-AUC·Brier(낮을수록 좋음).",
        "",
    ]
    if not HAS_LGBM:
        lines += ["> LightGBM을 불러오지 못해 로지스틱 회귀만 평가했습니다.", ""]
    for res, r in report["by_resolution"].items():
        lines += [
            f"## 격자 {res}°",
            f"- 표본 {r['n']:,} (양성 {r['positives']:,} · 음성 {r['negatives']:,}) · 특징 {len(r['features'])}개",
            "",
            "| 모델 | AUC | PR-AUC | Brier |",
            "|---|---|---|---|",
        ]
        for m, vals in r["metrics"].items():
            lines.append(f"| {m} | {vals['auc']:.3f} | {vals['pr_auc']:.3f} | {vals['brier']:.3f} |")
        lines.append("")

    # 대표 해상도(0.1°)의 임계값 표
    rep = report["by_resolution"].get("0.1")
    if rep and rep["threshold_table"]:
        lines += [
            "## 임계값 표 (격자 0.1°, 로지스틱) — 순찰 알림 정책 검토용",
            "",
            "| 임계값 | precision | recall | f1 | 예측 양성 비율 |",
            "|---|---|---|---|---|",
        ]
        for t in rep["threshold_table"]:
            lines.append(
                f"| {t['threshold']:.2f} | {t['precision']:.3f} | {t['recall']:.3f} "
                f"| {t['f1']:.3f} | {t['pred_pos_rate']:.3f} |"
            )
        lines.append("")
    lines += ["재현: `uv run python scripts/run_model.py`", ""]
    (OUT / "metrics.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
