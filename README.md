# 연안 해양사고 위험 분석

[![CI](https://github.com/Minsu5452/korean-marine-accident-risk/actions/workflows/ci.yml/badge.svg)](https://github.com/Minsu5452/korean-marine-accident-risk/actions/workflows/ci.yml) [![Live Demo](https://img.shields.io/badge/라이브_데모-vercel-000000?logo=vercel&logoColor=white)](https://korean-marine-accident-risk.vercel.app) ![Python](https://img.shields.io/badge/python-3.12-3776AB?logo=python&logoColor=white) [![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

전국 연안의 해양사고 기록과 해양기상 관측을 결합해 **격자×시간 단위 사고 위험도**를 추정하고, 어떤 기상 조건이 위험을 높이는지 통계로 검증하는 분석 시스템입니다. 결과는 해양경찰 순찰 배치 검토를 가정한 지도 대시보드에서 확인할 수 있습니다.

해양사고 위험 분석은 일반적인 예측 문제와 조금 다릅니다. 사고는 드물고 위치·시각이 불규칙하며, 해양기상은 연안 76개 지점에서만 관측되어 사고 지점의 기상을 직접 알 수 없습니다. 그래서 좌표를 정제한 뒤 사고마다 가장 가까운 관측 지점을 찾아 같은 시각의 기상을 연결하는 방식으로 데이터를 만들었습니다. 이 데이터 위에서 기상과 사고의 연관은 시간층화 case-crossover로 검증하고, 격자×시간 위험도는 해석 가능한 모델로 추정합니다.

![대시보드](docs/diagrams/web-demo.png)

해양경찰 순찰 배치 검토를 가정해 만든 지도 대시보드입니다. **[데모 사이트 바로가기 →](https://korean-marine-accident-risk.vercel.app)** 실제 분석 실행 결과를 키 없이 그대로 재생하며, 로컬에서 FastAPI 백엔드에 연결하면 계절·시간대·사고 유형별 조회도 동작합니다. (소스: [`web/`](web/))

## 구현 범위

- MTIS 해양사고 엑셀을 분석용 스키마로 읽고 한국 EEZ 밖·결측 좌표를 제거(29,695 → 28,935건)
- NMPNT 해양기상 수집: 71개 관측 지점의 2018–2025년 관측을 받아 10분 간격 값을 1시간 단위로 리샘플(풍향 같은 각도 값은 벡터 평균), 중단되면 이어서 수집
- 사고를 0.05°·0.1°·0.25° 세 해상도 격자에 배정하고, 사고가 없는 셀을 negative sampling으로 추출(양성 셀당 3배)
- 사고마다 가장 가까운 관측 지점을 haversine 거리로 찾아 같은 시각의 기상을 매칭(거리 60km·시간 ±30분)
- 시간층화 case-crossover 통계: 조건부 로지스틱 회귀로 오즈비 추정, 다변량 보정, 사고 유형군별 비교, Benjamini–Hochberg 보정
- 해석용 로지스틱 회귀와 성능 상한 확인용 LightGBM을 연도 기준 OOF 교차검증으로 평가(AUC·PR-AUC·Brier·임계값 표)
- XAI: 표준화 오즈비(95% CI)와 순열 중요도로 위험 요인 설명
- FastAPI 예측 API: 격자 위험, 셀 상세, 통계, XAI 엔드포인트 제공
- 해양경찰 순찰 배치 검토를 가정한 Next.js + MapLibre 지도 대시보드: 실제 실행 결과를 키 없이 재생하는 정적 데모

## 아키텍처

![아키텍처](docs/diagrams/architecture.png)

분석은 세 경로로 나눠 수행합니다.

| 경로 | 역할 |
|---|---|
| 통계(시간층화 case-crossover) | 사고 시각의 기상을 같은 장소·같은 조건의 다른 시점과 비교해 연관을 검증 |
| 모델(로지스틱·LightGBM) | 격자×시간 셀의 사고 발생 확률을 추정 |
| XAI(오즈비·순열 중요도) | 어떤 조건이 위험을 높이는지 설명 |

## 기술 스택

| 영역 | 기술 |
|---|---|
| 언어·프레임워크 | ![Python](https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=white) ![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white) |
| 데이터·통계 | ![pandas](https://img.shields.io/badge/pandas-150458?logo=pandas&logoColor=white) ![NumPy](https://img.shields.io/badge/NumPy-013243?logo=numpy&logoColor=white) ![SciPy](https://img.shields.io/badge/SciPy-8CAAE6?logo=scipy&logoColor=white) ![statsmodels](https://img.shields.io/badge/statsmodels-5B6770) |
| 모델 | ![scikit-learn](https://img.shields.io/badge/scikit--learn-F7931E?logo=scikitlearn&logoColor=white) ![LightGBM](https://img.shields.io/badge/LightGBM-5B6770) |
| 프론트엔드 | ![Next.js](https://img.shields.io/badge/Next.js-000000?logo=nextdotjs&logoColor=white) ![React](https://img.shields.io/badge/React-61DAFB?logo=react&logoColor=black) ![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?logo=typescript&logoColor=white) ![MapLibre](https://img.shields.io/badge/MapLibre_GL_JS-1E5CB3) |
| 인프라·배포 | ![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-2088FF?logo=githubactions&logoColor=white) ![Vercel](https://img.shields.io/badge/Vercel-000000?logo=vercel&logoColor=white) |
| 코드 품질 | ![pytest](https://img.shields.io/badge/pytest-0A9EDC?logo=pytest&logoColor=white) ![Ruff](https://img.shields.io/badge/Ruff-D7FF64?logo=ruff&logoColor=black) ![mypy](https://img.shields.io/badge/mypy-2A6DB2) |

## 실행 방법

### 데이터 준비

사고 원본 데이터는 이용약관상 저장소에 포함하지 않습니다. 아래 위치에 직접 내려받아 둡니다.

1. 한국해양교통안전공단(KOMSA) MTIS "GIS기반 해양사고분석"에서 사고 목록 엑셀을 내려받습니다.
2. `data/raw/GIS기반해양사고분석.xlsx`로 저장합니다(`data/`는 `.gitignore` 대상).

### 분석 파이프라인

```bash
uv sync                                          # 의존성 설치(Python 3.12)
make clean-report                                # 좌표 정제 리포트
export NMPNT_SERVICE_KEY=...                      # 국립해양측위정보원 서비스키
uv run python scripts/collect_weather_bulk.py    # 전 기간 기상 수집(재개 가능)
uv run python scripts/build_dataset.py           # 격자×시간 학습셋
uv run python scripts/run_stats.py               # 시간층화 case-crossover 통계
uv run python scripts/run_model.py               # 로지스틱·LightGBM 평가
uv run python scripts/run_xai.py                 # 오즈비·순열 중요도
```

### API와 대시보드

```bash
uv run uvicorn marine_accident_risk.serving.app:get_app --factory   # 예측 API
cd web && npm install && npm run dev                                  # 대시보드(개발)
npm run build                                                         # 정적 export → web/out
```

## 평가와 검증

아래 표는 모두 `reports/`에 저장된 산출물에서 가져온 값입니다. 데이터 준비 단계의 리포트(좌표 정제 [`reports/clean/coordinate_cleaning.md`](reports/clean/coordinate_cleaning.md), 학습셋 구성 [`reports/dataset/summary.md`](reports/dataset/summary.md), 관측 지점 커버리지 [`reports/weather/station_coverage.md`](reports/weather/station_coverage.md))도 같은 폴더에 있습니다.

### case-crossover (`reports/stats/case_crossover.md`)

사고 시각마다 **같은 달·같은 요일·같은 시각의 다른 날들**을 대조로 잡아(시간층화 대조), 조건부 로지스틱 회귀로 기상 1표준편차 증가당 사고 오즈비를 추정했습니다(분석 묶음 9,687건). 위치·계절·요일·시각은 묶음 안에서 통제되므로, 조업이 집중되는 시간대나 계절 추세가 결과에 섞이지 않습니다.

| 변수 | 오즈비 | 95% CI | q(BH) |
|---|---|---|---|
| 풍속 | **0.903** | 0.88–0.93 | <0.01 |
| 기온 | **1.248** | 1.17–1.33 | <0.01 |
| 기압 | 1.052 | 1.01–1.10 | <0.05 |
| 습도 | 0.966 | 0.94–1.00 | <0.05 |

풍속이 낮고 기온이 높을수록 사고 오즈가 높아집니다. 거친 날씨일수록 위험하다는 통념과 반대 방향입니다. 사고종류로 나눠 보면 이 연관은 **기계·비기상형 사고**(기관손상·부유물감김 등)에 집중되어 있고, 기상 민감형 사고(충돌·좌초·전복)에서는 풍속이 유의하지 않았습니다.

| 변수 | 기상 민감형 | 기계·비기상형 |
|---|---|---|
| 풍속 | 1.025 (유의하지 않음) | **0.803** |
| 기온 | 1.031 (유의하지 않음) | **1.447** |

기계 고장형 사고는 위험한 기상이 원인이라기보다, 출항과 조업이 늘어나는 잔잔하고 따뜻한 날에 더 많이 발생합니다. 즉 사고 시점 기상과의 연관은 위험 신호가 아니라 활동·노출 패턴이 반영된 결과로 해석했습니다. 사고종류 구성은 [`reports/stats/accident_types.md`](reports/stats/accident_types.md)에 정리했습니다(설비 고장형 52.7%).

### 모델 (`reports/model/metrics.md`, 격자 0.1°)

| 모델 | AUC | PR-AUC | Brier |
|---|---|---|---|
| 로지스틱(해석) | 0.653 | 0.422 | 0.233 |
| LightGBM(성능 상한) | 0.834 | 0.698 | 0.159 |

### XAI 핵심 (`reports/xai/odds_ratios.md`)

야간에는 사고 오즈가 낮고(0.62×), 기온·기압이 높을수록 오즈가 높아지며(1.47×·1.28×), 풍속은 유의하지 않았습니다. 이 데이터에서 사고는 위험한 기상보다 **활동 패턴**(주간·따뜻한 날·특정 해역)에 더 좌우됩니다. 실제로 정제 사고의 절반 이상(52.7%)이 기관손상·부유물감김 같은 설비 고장형이고([`reports/stats/accident_types.md`](reports/stats/accident_types.md)), 시간층화 case-crossover에서도 기상 연관은 이 비기상형 사고에 집중되어 있었습니다. 위험한 기상의 영향이 아니라, 잔잔한 날 늘어나는 조업 노출이 반영된 결과입니다.

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

- 사고 시점의 기상 효과만 따로 보기 위해 시간층화 case-crossover를 썼습니다. 같은 장소에서 같은 달·같은 요일·같은 시각의 다른 날을 대조로 잡고 조건부 로지스틱 회귀로 비교하면, 위치·계절·요일·시각이 묶음 안에서 통제됩니다. 사고 전 한 시점만 대조로 쓰는 방식은 시간 추세에 편향될 수 있어 시간층화 대조를 택했고, 여러 변수를 함께 보므로 FDR로 보정했습니다. 사고종류별로 나눠 기상 연관이 어디에서 나오는지도 확인했습니다.
- 시간 누수를 막기 위해 모델은 연도 단위로 폴드를 나눠(연도 기준 OOF 교차검증), 같은 해 데이터가 학습과 평가에 동시에 들어가지 않게 했습니다.
- 모델은 성능보다 해석 가능성을 우선했습니다. 위험 요인은 로지스틱 회귀의 오즈비로 설명하고, LightGBM은 같은 데이터에서 성능이 어디까지 오르는지 확인하는 용도로만 뒀습니다. 둘의 AUC 차이(0.65 대 0.83)는 해석 가능성을 위해 감수했습니다.
- 데모는 실제로 실행한 결과만 보여줍니다. 화면의 수치는 분석을 실행해 캡처한 값이고, 정적 데모에서 동작하지 않는 필터는 비활성으로 표시했습니다.

## 한계

- **파고·파향은 쓰지 못했습니다.** NMPNT 관측 지점이 제공하지 않는 항목이라, 거친 바다의 영향은 풍속으로 간접적으로만 반영됩니다.
- 관측 지점이 연안에 76개뿐이라, 먼바다 사고는 가까운 관측 지점이 없어 기상이 매칭되지 않고 분석에서 빠집니다(사고의 약 절반만 60km 안에서 매칭됩니다).
- 사고 데이터는 신고·접수 기반이라 미신고·경미 사고가 빠지는 관측 편향이 있습니다.
- 기상만으로는 예측력이 약합니다(로지스틱 AUC 0.65). 예측력의 상당 부분은 공간·시간 패턴에서 나옵니다.
- 이 프로젝트는 상관·위험 요인 분석이며, 인과를 주장하지 않습니다. 사고 기록은 2017–2025년, 분석 구간은 해양기상이 있는 2018–2025년입니다. 데이터는 수집 시점의 스냅샷이며 자동으로 갱신되지 않습니다.

## 라이선스

코드는 [Apache-2.0](LICENSE) 라이선스를 따릅니다.
