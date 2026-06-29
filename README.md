# korean-marine-accident-risk

한국 연안의 해양사고 기록과 해양기상 관측을 결합해, 격자×시간 단위로 사고 위험도를 추정하고 그 근거(어떤 기상·환경 조건이 위험을 끌어올리는지)를 설명하는 분석 프로젝트다.

해양사고는 드물고 위치·시각이 불규칙해, 단순 건수 집계만으로는 "언제 어디가 위험한지" 말하기 어렵다. 그래서 사고 좌표를 정제하고, 가장 가까운 관측소의 같은 시각 기상을 거리 임계 안에서 매칭한 뒤, 변수 분포가 정규인지 먼저 확인해 맞는 통계 검정을 고르고, 해석 가능한 모델로 위험도를 추정한다.

> 진행 중인 프로젝트다. 현재는 데이터 적재·좌표 정제 단계가 구현돼 있고, 아래 로드맵 순서로 확장한다.

## 구현 범위

- [x] MTIS 해양사고 엑셀 로더 — 원본 컬럼을 분석용 스키마로 정규화, 발생일시 파싱
- [x] 좌표 정제 — 한국 EEZ 대략 bbox 밖·결측 좌표 제거, 제거 건수 리포트
- [x] NMPNT 해양기상 수집 — 76개 지점 목록·기간별 수집·10분→시간 리샘플(풍향은 벡터 평균)
- [ ] 격자 배정 · 사고-기상 최근접 매칭 · negative sampling
- [ ] 통계 분석(정규성 → 검정 선택 → 효과크기 → 다중보정, case-crossover)
- [ ] 모델(로지스틱·GAM·부스팅 비교) · XAI
- [ ] FastAPI 예측 API · Next.js 지도 대시보드

## 데이터 준비

사고 원본 데이터는 라이선스상 레포에 포함하지 않는다. 직접 내려받아 배치한다.

1. 한국해양교통안전공단(KOMSA) MTIS "GIS기반 해양사고분석"에서 사고 목록 엑셀을 내려받는다.
2. `data/raw/GIS기반해양사고분석.xlsx` 로 저장한다(`data/`는 `.gitignore` 대상이라 커밋되지 않는다).

## 개발 환경

```bash
uv sync          # 가상환경·의존성 설치(Python 3.12)
make test        # pytest
make lint        # ruff
make typecheck   # mypy
```

## 좌표 정제 실행

```bash
make clean-report
# = uv run python scripts/clean_accidents.py
# reports/clean/coordinate_cleaning.md 에 정제 리포트를 생성한다.
```

## 해양기상 수집

기상 수집에는 국립해양측위정보원(NMPNT) 서비스키가 필요하다. 환경변수 `NMPNT_SERVICE_KEY`로 주입한다(`.env.example` 참고).

```bash
make coverage                              # 지점 변수 커버리지 리포트(키 불필요)
make collect START=20240115 END=20240115   # 기간별 수집·시간 리샘플 → data/cache/
```

지점별 관측 변수 커버리지는 `reports/weather/station_coverage.md`에 있다. 파고·파향은 모든 지점에서 미제공이라 분석에서 제외한다.

## 라이선스

Apache-2.0. 자세한 내용은 [LICENSE](LICENSE)를 참고한다.
