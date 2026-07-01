# korean-marine-accident-risk

[![Live Demo](https://img.shields.io/badge/라이브_데모-vercel-000000?logo=vercel&logoColor=white)](https://korean-marine-accident-risk.vercel.app) ![Python](https://img.shields.io/badge/python-3.12-3776AB?logo=python&logoColor=white) [![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

전국 연안의 해양사고 기록과 해양기상 관측을 결합해 **격자×시간 단위 사고 위험도**를 추정하고, 어떤 기상·환경 조건이 위험을 끌어올리는지 통계와 해석 가능한 모델로 설명하는 분석 프로젝트입니다. 분석 결과는 해양경찰 순찰 배치를 가정한 지도 대시보드에서 확인할 수 있습니다.

해양사고는 드물고 위치·시각이 불규칙해, 단순 건수 집계만으로는 "언제 어디가 위험한지" 말하기 어렵습니다. 게다가 해양기상 관측은 연안 76개 지점에만 있고, 정작 사고는 관측 지점 사이의 바다에서 납니다. 그래서 사고 좌표를 먼저 정제하고, 사고마다 정해진 거리 안에서 가장 가까운 관측 지점을 찾아 같은 시각의 기상을 붙였습니다. 어떤 기상이 사고와 얽혀 있는지는 사고가 난 시각을 같은 자리·같은 조건의 다른 날들과 견주는 방식(시간층화 case-crossover)으로 따졌고, 격자×시간 위험도는 해석 가능한 모델로 추정했습니다.

![대시보드](docs/diagrams/web-demo.png)

> 위 화면은 실제 분석 실행 결과를 캡처한 정적 데모입니다(표시 수치는 손으로 고치지 않았습니다). **라이브: [korean-marine-accident-risk.vercel.app](https://korean-marine-accident-risk.vercel.app)** — 키 없이 동작합니다.

## 구현 범위

코드와 테스트로 확인되는 기능입니다. 모든 수치는 아래 재현 명령으로 다시 만들 수 있습니다.

- **MTIS 사고 데이터 적재·좌표 정제** — 엑셀(`사고목록` 시트)을 분석용 스키마로 읽어 들이고, 한국 EEZ를 대략 감싸는 좌표 범위(bbox)를 벗어나거나 좌표가 비어 있는 행을 걸러냅니다(29,695 → 28,935건, 범위 밖 760건).
- **NMPNT 해양기상 수집** — 전국 76개 관측 지점 가운데 기상값이 있는 71개 지점의 2018–2025년 관측을 받아, 10분 간격 값을 1시간 단위로 리샘플합니다(풍향 같은 각도 값은 벡터로 평균). 수집이 중간에 끊겨도 이어서 받고, 실패한 날짜만 건너뜁니다.
- **격자 배정·사고-기상 매칭·negative sampling** — 0.05°·0.1°·0.25° 세 가지 격자 해상도로 나누고, 사고마다 가장 가까운 관측 지점을 haversine 거리로 찾아 붙입니다(거리 60km·시간 ±30분 안). 학습용으로는 사고가 난 셀에 더해, 사고가 없는 셀을 사고 셀의 3배(기본값)만큼 뽑습니다.
- **통계 분석(시간층화 case-crossover)** — 사고가 난 시각의 기상을 같은 자리에서 같은 달·같은 요일·같은 시각의 다른 날들과 묶어, 조건부 로지스틱 회귀로 기상 1표준편차 증가당 사고 오즈비를 추정합니다(서로 보정한 다변량·사고 유형군별 분석 포함). 변수를 여러 개 함께 보므로 다중비교 보정(Benjamini–Hochberg)도 적용합니다.
- **모델** — 해석 가능한 로지스틱 회귀를 본 모델로 삼고, 성능이 어디까지 오르는지 견주는 상한선으로 LightGBM을 함께 둡니다. 둘 다 연도 기준 OOF 교차검증으로 평가합니다(AUC·PR-AUC·Brier·임계값 표).
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
uv run python scripts/run_stats.py               # 시간층화 case-crossover 통계
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

표는 모두 `reports/` 산출물 한 곳에서 끌어옵니다. 데이터 준비 단계 리포트도 같은 폴더에 두었습니다 — 좌표 정제 [`reports/clean/coordinate_cleaning.md`](reports/clean/coordinate_cleaning.md), 학습셋 구성 [`reports/dataset/summary.md`](reports/dataset/summary.md), 관측 지점 커버리지 [`reports/weather/station_coverage.md`](reports/weather/station_coverage.md).

### case-crossover (`reports/stats/case_crossover.md`)

사고 시각을 **같은 달·같은 요일·같은 시각의 다른 날들**과 한 묶음으로 묶어(시간층화 대조), 조건부 로지스틱 회귀로 기상 1표준편차 증가당 사고 오즈비를 추정했습니다(분석 묶음 9,687건). 위치·계절·요일·시각은 묶음이 통제하므로, 조업이 몰리는 시간대나 계절 추세가 섞이지 않습니다.

| 변수 | 오즈비 | 95% CI | q(BH) |
|---|---|---|---|
| 풍속 | **0.903** | 0.88–0.93 | <0.01 |
| 기온 | **1.248** | 1.17–1.33 | <0.01 |
| 기압 | 1.052 | 1.01–1.10 | <0.05 |
| 습도 | 0.966 | 0.94–1.00 | <0.05 |

풍속이 낮고 기온이 높을수록 사고 오즈가 올라갑니다 — "거친 날씨가 사고를 부른다"와 반대 방향입니다. 사고종류로 나눠 보면 이 연관은 **기계·비기상형 사고**(기관손상·부유물감김 등)에 몰려 있고, 기상 민감형 사고(충돌·좌초·전복)에서는 풍속이 유의하지 않았습니다.

| 변수 | 기상 민감형 | 기계·비기상형 |
|---|---|---|
| 풍속 | 1.025 (유의하지 않음) | **0.803** |
| 기온 | 1.031 (유의하지 않음) | **1.447** |

기계 고장형 사고는 잔잔하고 따뜻한 날 선박이 더 많이 나가 조업하기 때문에 늘어납니다. 즉 사고 시점 기상의 연관은 위험 신호라기보다 활동·노출 패턴의 흔적입니다. 사고종류 구성은 [`reports/stats/accident_types.md`](reports/stats/accident_types.md)(설비 고장형 52.7%)를 참고하세요.

### 모델 (`reports/model/metrics.md`, 격자 0.1°)

| 모델 | AUC | PR-AUC | Brier |
|---|---|---|---|
| 로지스틱(해석) | 0.653 | 0.422 | 0.233 |
| LightGBM(성능 상한) | 0.834 | 0.698 | 0.159 |

### XAI 핵심 (`reports/xai/odds_ratios.md`)

야간에는 사고 오즈가 낮고(0.62×), 기온·기압이 높을수록 오즈가 올라가며(1.47×·1.28×), 풍속은 유의하지 않았습니다. 즉 이 데이터에서 사고는 *위험한 기상*보다 **활동 패턴**(주간·따뜻한 날·특정 해역)에 더 좌우됩니다. 실제로 정제 사고의 절반 이상(52.7%)이 기관손상·부유물감김 같은 설비 고장형이고([`reports/stats/accident_types.md`](reports/stats/accident_types.md)), 시간층화 case-crossover에서도 기상 연관은 이 비기상형 사고에 몰려 있었습니다 — 위험한 기상이라기보다 잔잔한 날 늘어나는 조업 노출의 흔적입니다.

## 프로젝트 구조

```text
korean-marine-accident-risk/
├── src/marine_accident_risk/
│   ├── data/      # MTIS 로더·좌표 정제·NMPNT 수집기·기상 캐시
│   ├── grid/      # 격자 배정·negative sampling
│   ├── matching/  # 사고-기상 최근접 매칭(haversine)
│   ├── stats/     # 시간층화 case-crossover·조건부 로지스틱·효과크기·BH
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

- 사고 시점만의 특성을 분리하려고 시간층화 case-crossover를 썼습니다. 같은 사고 장소에서 같은 달·같은 요일·같은 시각의 다른 날을 대조로 묶고 조건부 로지스틱 회귀로 비교하면, 위치·계절·요일·시각이 묶음 안에서 자동으로 통제됩니다. 사고 전 한 시점만 대조로 쓰면 시간 추세에 치우칠 수 있어 시간층화 대조를 택했고, 여러 변수를 함께 보므로 FDR로 보정했습니다. 사고종류로 나눠 보며 기상 연관이 어디서 나오는지까지 확인했습니다.
- 시간 순서가 뒤섞이지 않게 신경 썼습니다. 모델은 연도 단위로 폴드를 나눠(연도 기준 OOF 교차검증), 같은 해 데이터가 학습과 평가에 동시에 들어가지 않게 했습니다.
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
