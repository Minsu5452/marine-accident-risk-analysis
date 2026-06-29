# korean-marine-accident-risk

[![Live Demo](https://img.shields.io/badge/라이브_데모-vercel-000000?logo=vercel&logoColor=white)](https://korean-marine-accident-risk.vercel.app) ![Python](https://img.shields.io/badge/python-3.12-3776AB?logo=python&logoColor=white) [![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

전국 연안의 해양사고 기록과 해양기상 관측을 결합해 **격자×시간 단위 사고 위험도**를 추정하고, 어떤 기상·환경 조건이 위험을 끌어올리는지 통계와 해석 가능한 모델로 설명하는 분석 프로젝트입니다. 분석 결과는 해양경찰 순찰 배치를 가정한 지도 대시보드에서 확인할 수 있습니다.

해양사고는 드물고 위치·시각이 불규칙해, 단순 건수 집계만으로는 "언제 어디가 위험한지" 말하기 어렵습니다. 게다가 기상 관측은 연안 76개 지점에만 있고 사고는 그 사이 바다에서 납니다. 그래서 사고 좌표를 먼저 정제하고, 사고마다 가장 가까운 관측 지점의 같은 시각 기상을 정해진 거리 안에서 붙였습니다. 통계 검정은 변수 분포가 정규를 따르는지 확인해 거기에 맞는 방법을 골랐고, 위험도는 해석이 되는 모델로 추정했습니다.

![대시보드](docs/diagrams/web-demo.png)

> 위 화면은 실제 분석 실행 결과를 캡처한 정적 데모입니다(표시 수치는 손으로 고치지 않았습니다). **라이브: [korean-marine-accident-risk.vercel.app](https://korean-marine-accident-risk.vercel.app)** — 키 없이 동작합니다.

## 구현 범위

코드와 테스트로 확인되는 기능입니다. 모든 수치는 아래 재현 명령으로 다시 만들 수 있습니다.

- **MTIS 사고 데이터 적재·좌표 정제** — 엑셀(`사고목록` 시트)을 분석용 스키마로 읽어 들이고, 한국 EEZ를 대략 감싸는 좌표 범위(bbox)를 벗어나거나 좌표가 비어 있는 행을 걸러냅니다(29,695 → 28,935건, 범위 밖 760건).
- **NMPNT 해양기상 수집** — 전국 76개 관측 지점 가운데 기상값이 있는 71개 지점의 2018–2025년 관측을 받아, 10분 간격 값을 1시간 단위로 리샘플합니다(풍향 같은 각도 값은 벡터로 평균). 수집이 중간에 끊겨도 이어서 받고, 실패한 날짜만 건너뜁니다.
- **격자 배정·사고-기상 매칭·negative sampling** — 0.05°·0.1°·0.25° 세 가지 격자 해상도로 나누고, 사고마다 가장 가까운 관측 지점을 haversine 거리로 찾아 붙입니다(거리 60km·시간 ±30분 안). 학습용으로는 사고가 난 셀에 더해, 사고가 없는 셀을 사고 셀의 3배(기본값)만큼 뽑습니다.
- **통계 분석(case-crossover)** — 사고가 난 시각의 기상을 같은 자리에서 7일 전 같은 시각의 기상과 짝지어 비교합니다. 변수마다 분포의 정규성을 확인해 검정 방법을 자동으로 고르고, 효과크기와 다중비교 보정(Benjamini–Hochberg)을 함께 계산합니다.
- **모델** — 해석이 되는 로지스틱 회귀를 본 모델로 삼고, 성능이 어디까지 오르는지 견주는 상한선으로 LightGBM을 함께 둡니다. 둘 다 연도 기준 OOF 교차검증으로 평가합니다(AUC·PR-AUC·Brier·임계값 표).
- **XAI** — 표준화 오즈비(신뢰구간 포함)와 순열 중요도로 위험 요인을 설명합니다.
- **FastAPI 예측 API** — 격자 위험·셀 상세·통계·XAI 엔드포인트를 제공합니다.
- **Next.js + MapLibre 지도 대시보드** — 실제 실행을 캡처한 정적 데모를 키 없이 재생합니다.

## 아키텍처

![아키텍처](docs/diagrams/architecture.png)

## 기술 스택

| 영역 | 기술 |
|---|---|
| 언어·프레임워크 | ![Python](https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=white) ![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white) |
| 데이터·통계 | ![pandas](https://img.shields.io/badge/pandas-150458?logo=pandas&logoColor=white) ![NumPy](https://img.shields.io/badge/NumPy-013243?logo=numpy&logoColor=white) ![SciPy](https://img.shields.io/badge/SciPy-8CAAE6?logo=scipy&logoColor=white) ![statsmodels](https://img.shields.io/badge/statsmodels-5B6770) |
| 모델 | ![scikit-learn](https://img.shields.io/badge/scikit--learn-F7931E?logo=scikitlearn&logoColor=white) ![LightGBM](https://img.shields.io/badge/LightGBM-5B6770) |
| 프론트엔드 | ![Next.js](https://img.shields.io/badge/Next.js-000000?logo=nextdotjs&logoColor=white) ![React](https://img.shields.io/badge/React-61DAFB?logo=react&logoColor=black) ![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?logo=typescript&logoColor=white) ![MapLibre](https://img.shields.io/badge/MapLibre_GL_JS-1E5CB3) |
| 코드 품질 | ![pytest](https://img.shields.io/badge/pytest-0A9EDC?logo=pytest&logoColor=white) ![Ruff](https://img.shields.io/badge/Ruff-D7FF64?logo=ruff&logoColor=black) ![mypy](https://img.shields.io/badge/mypy-2A6DB2) |

## 실행 방법

### 데이터 준비

사고 원본은 라이선스상 레포에 포함하지 않습니다. 직접 내려받아 배치합니다.

1. 한국해양교통안전공단(KOMSA) MTIS "GIS기반 해양사고분석"에서 사고 목록 엑셀을 내려받습니다.
2. `data/raw/GIS기반해양사고분석.xlsx` 로 저장합니다(`data/`는 `.gitignore` 대상).

### 분석 파이프라인

```bash
uv sync                                          # 의존성 설치(Python 3.12)
make clean-report                                # 좌표 정제 리포트
export NMPNT_SERVICE_KEY=...                      # 국립해양측위정보원 서비스키
uv run python scripts/collect_weather_bulk.py    # 전기간 기상 수집(재개 가능)
uv run python scripts/build_dataset.py           # 격자×시간 학습셋
uv run python scripts/run_stats.py               # case-crossover 통계
uv run python scripts/run_model.py               # 로지스틱·LightGBM 평가
uv run python scripts/run_xai.py                 # 오즈비·순열 중요도
```

### API와 프론트

```bash
uv run uvicorn marine_accident_risk.serving.app:get_app --factory   # 예측 API
cd web && npm install && npm run dev                                  # 대시보드(개발)
npm run build                                                         # 정적 export → web/out
```

## 평가 / 검증

표는 모두 `reports/` 산출물 한 곳에서 끌어옵니다.

### case-crossover (`reports/stats/case_crossover.md`)

사고 시점 기상이 평소와 유의하게 다른지를 짝지어 비교했습니다. 큰 표본이라 작은 차이도 유의해지므로 효과크기를 함께 봅니다.

| 변수 | 검정 | 효과크기 | q(BH) |
|---|---|---|---|
| 풍속 | Wilcoxon | **−0.073** | <0.01 |
| 습도 | Wilcoxon | −0.034 | <0.05 |
| 기압 | Wilcoxon | +0.030 | <0.05 |
| 기온 | Wilcoxon | +0.026 | <0.05 |

풍속·습도·기압·기온이 통계적으로 유의했지만 효과크기는 작고, **풍속은 오히려 사고 시점이 약간 낮았습니다**.

### 모델 (`reports/model/metrics.md`, 격자 0.1°)

| 모델 | AUC | PR-AUC | Brier |
|---|---|---|---|
| 로지스틱(해석) | 0.653 | 0.422 | 0.233 |
| LightGBM(성능 상한) | 0.834 | 0.698 | 0.159 |

### XAI 핵심 (`reports/xai/odds_ratios.md`)

야간에는 사고 오즈가 낮고(0.62×), 기온·기압이 높을수록 오즈가 올라가며(1.47×·1.28×), 풍속은 유의하지 않았습니다. 즉 이 데이터에서 사고는 *위험한 기상*보다 **활동 패턴**(주간·따뜻한 날·특정 해역)에 더 좌우됩니다 — 사고의 상당수가 기관손상·부유물 감김 같은 비기상 요인이라는 점과 일치합니다.

## 프로젝트 구조

```text
korean-marine-accident-risk/
├── src/marine_accident_risk/
│   ├── data/      # MTIS 로더·좌표 정제·NMPNT 수집기·기상 캐시
│   ├── grid/      # 격자 배정·negative sampling
│   ├── matching/  # 사고-기상 최근접 매칭(haversine)
│   ├── stats/     # 정규성·검정 선택·효과크기·BH·case-crossover
│   ├── modeling/  # 특징 구성·OOF 교차검증·지표·임계값
│   └── serving/   # FastAPI 예측 API
├── web/           # Next.js + MapLibre 대시보드, 정적 데모 데이터
├── scripts/       # 수집·정제·데이터셋 빌드·분석·캡처 실행
├── reports/       # 재현 가능한 통계·모델·XAI 리포트
├── tests/         # 단위 테스트
├── configs/       # 실행 설정(default.yaml)
└── docs/          # 아키텍처 다이어그램(HTML·PNG)
```

## 구현하면서 신경 쓴 점

- 통계 검정은 변수마다 분포를 보고 골랐습니다. p값 하나로 판단하지 않고, 변수별로 차이가 정규분포를 따르는지 확인해 짝 t검정과 Wilcoxon 검정을 나눠 썼습니다. 표본이 커서 작은 차이도 쉽게 "유의"하게 나오기 때문에, 효과크기와 다중비교 보정(FDR)을 늘 같이 봤습니다.
- 시간 순서가 뒤섞이지 않게 신경 썼습니다. 모델은 연도별로 학습과 검증을 나눠(OOF 교차검증), 과거를 예측하는 데 미래 데이터가 끼어들지 않도록 했습니다. case-crossover도 같은 위치·같은 관측 지점의 7일 전 같은 시각을 대조로 잡아, 계절이나 지역 차이가 결과에 섞이지 않게 걷어냈습니다.
- 성능보다 해석을 우선했습니다. 위험 요인은 로지스틱 회귀의 오즈비로 설명하고, LightGBM은 같은 데이터에서 성능이 어디까지 오르는지 보는 상한선으로만 뒀습니다. 둘의 AUC 차이(0.65 대 0.83)가 곧 해석을 택한 대가인 셈입니다.
- 데모는 실제로 돌린 결과를 그대로 보여줍니다. 화면의 수치는 분석을 실행해 캡처한 값이고, 데이터가 없는 필터는 동작하는 척하지 않고 비활성으로 표시했습니다.

## 한계

- **파고·파향을 쓰지 않습니다**(NMPNT 미제공). 거친 바다 자체의 영향은 풍속으로만 어느 정도 가늠할 수 있습니다.
- 관측 지점이 연안에 76개뿐이라, 먼 바다에서 난 사고는 가까운 관측 지점이 없어 기상이 매칭되지 않고 빠집니다(사고의 약 절반만 60km 안에서 매칭됩니다).
- 사고 데이터는 신고·접수 기반이라 미신고·경미 사고가 빠지는 관측 편향이 있습니다.
- 기상만으로는 예측력이 약합니다(로지스틱 AUC 0.65). 예측력의 상당 부분은 공간·시간 패턴에서 나옵니다.
- 상관·위험요인 분석이며 인과를 주장하지 않습니다. 사고 기록은 2017–2025년이지만 해양기상이 있는 2018–2025년 구간을 분석했고, 데이터는 정적 스냅샷입니다.

## 라이선스

Apache-2.0. 자세한 내용은 [LICENSE](LICENSE)를 참고하세요.
