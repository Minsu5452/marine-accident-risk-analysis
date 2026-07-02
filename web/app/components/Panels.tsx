import type { ReactNode } from "react";
import type { CellDetail, GridCell, Resolution } from "../lib/types";
import {
  LEVEL_STYLE,
  ci,
  int,
  or2,
  percentileLabel,
  risk2,
  topPctByRank,
} from "../lib/format";

const RES_OPTIONS: { value: Resolution; label: string }[] = [
  { value: "0.05", label: "0.05°" },
  { value: "0.1", label: "0.10°" },
  { value: "0.25", label: "0.25°" },
];

const LOCKED_SEASON = ["전체", "봄", "여름", "가을", "겨울"];
const LOCKED_TIME = ["전체", "주간", "야간"];
const LOCKED_TYPE = ["충돌", "좌초", "전복", "기관손상", "화재·폭발", "침수"];
const LOCKED_VAR = ["위험도", "풍속", "시정"];

export function FilterPanel({
  resolution,
  onResolution,
}: {
  resolution: Resolution;
  onResolution: (r: Resolution) => void;
}) {
  return (
    <aside className="flt filter">
      <div className="ph">
        <h2>분석 조건</h2>
        <span className="lockbadge">정적 데모 · 전체 고정</span>
      </div>

      <div className="fg">
        <div className="l">격자 크기</div>
        <div className="seg" role="group" aria-label="격자 해상도 선택">
          {RES_OPTIONS.map((o) => (
            <button
              key={o.value}
              className={resolution === o.value ? "on" : ""}
              aria-pressed={resolution === o.value}
              onClick={() => onResolution(o.value)}
            >
              {o.label}
            </button>
          ))}
        </div>
      </div>

      <div className="fg locked">
        <div className="l">계절</div>
        <div className="chips" aria-hidden="true">
          {LOCKED_SEASON.map((s, i) => (
            <span key={s} className={`chip${i === 0 ? " on" : ""}`}>
              {s}
            </span>
          ))}
        </div>
      </div>

      <div className="fg locked">
        <div className="l">시간대</div>
        <div className="seg" aria-hidden="true">
          {LOCKED_TIME.map((t, i) => (
            <button key={t} className={i === 0 ? "on" : ""} disabled>
              {t}
            </button>
          ))}
        </div>
      </div>

      <div className="fg locked">
        <div className="l">사고 유형</div>
        <div className="chips" aria-hidden="true">
          {LOCKED_TYPE.map((t, i) => (
            <span key={t} className={`chip${i === 0 ? " on" : ""}`}>
              {t}
            </span>
          ))}
        </div>
      </div>

      <div className="fg locked">
        <div className="l">표시 변수</div>
        <div className="chips" aria-hidden="true">
          {LOCKED_VAR.map((t, i) => (
            <span key={t} className={`chip${i === 0 ? " on" : ""}`}>
              {t}
            </span>
          ))}
        </div>
      </div>

      <div className="lockednote">
        <b>정적 데모: 세부 필터는 전체 기준으로 고정됩니다.</b> 해상도 전환과 지도 격자 선택만
        동작합니다. 로컬 백엔드에 연결하면 계절·시간대·사고 유형별 조회가 동작합니다.
      </div>
    </aside>
  );
}

interface Selection {
  grid: GridCell;
  detail: CellDetail | null;
}

export function ResultPanel({
  selection,
  resolution,
}: {
  selection: Selection | null;
  resolution: Resolution;
}) {
  return (
    <aside className="flt result">
      <div className="ph">
        <h2>조회 결과 · 선택 격자</h2>
        <span className="tag live">실측값</span>
      </div>
      <div className="pb">
        {!selection ? (
          <EmptyResult resolution={resolution} />
        ) : selection.detail ? (
          <DetailResult grid={selection.grid} detail={selection.detail} />
        ) : (
          <SummaryResult grid={selection.grid} resolution={resolution} />
        )}
      </div>
    </aside>
  );
}

function EmptyResult({ resolution }: { resolution: Resolution }) {
  return (
    <div className="empty">
      <span className="ic" aria-hidden="true">
        ⊹
      </span>
      지도에서 격자를 클릭하세요.
      <br />
      선택한 격자의 위험도와 모델 근거가 여기에 표시됩니다.
      {resolution !== "0.1" && (
        <>
          <br />
          <span style={{ fontSize: "11px" }}>
            기여 요인·과거 사고 상세는 0.10° 격자에서 제공됩니다.
          </span>
        </>
      )}
    </div>
  );
}

function ScoreBox({
  risk,
  level,
  rightTop,
  rightBottom,
}: {
  risk: number;
  level: GridCell["level"];
  rightTop: ReactNode;
  rightBottom: ReactNode;
}) {
  const st = LEVEL_STYLE[level];
  return (
    <div className="score rise">
      <div className="big num">{risk2(risk)}</div>
      <div className="meta">
        <span className="pill" style={{ background: st.bg, color: st.on }}>
          {st.label}
        </span>
        <span className="sm">
          {rightTop}
          <br />
          {rightBottom}
        </span>
      </div>
    </div>
  );
}

function DetailResult({ grid, detail }: { grid: GridCell; detail: CellDetail }) {
  const maxAbsLn = Math.max(
    ...detail.contributing_factors.map((f) => Math.abs(Math.log(f.odds_ratio))),
    1e-6,
  );
  return (
    <>
      <ScoreBox
        risk={grid.risk}
        level={grid.level}
        rightTop={<>위험도 점수 (0~1)</>}
        rightBottom={
          <>
            전체 {int(detail.total_cells)}셀 중 <b>{detail.rank}위</b> ·{" "}
            <span style={{ whiteSpace: "nowrap" }}>
              {topPctByRank(detail.rank, detail.total_cells)}
            </span>
          </>
        }
      />
      <div className="kv">
        <span className="k">격자 좌표</span>
        <span className="v num">
          {detail.lat.toFixed(2)}°N, {detail.lon.toFixed(2)}°E
        </span>
      </div>
      <div className="kv">
        <span className="k">해역</span>
        <span className="v">{detail.sea_area}</span>
      </div>
      <div className="kv">
        <span className="k">최근접 관측 지점까지</span>
        <span className="v num">{detail.dist_km.toFixed(1)} km</span>
      </div>
      <div className="kv">
        <span className="k">격자 내 누적 사고</span>
        <span className="v num">{int(detail.accidents)}건</span>
      </div>

      <div className="subh">
        모델 기여 요인 <span className="ex">로지스틱 오즈비 · 격자 공통</span>
      </div>
      <table className="ctab">
        <tbody>
          {detail.contributing_factors.map((f) => {
            const up = f.odds_ratio >= 1;
            const w = (Math.abs(Math.log(f.odds_ratio)) / maxAbsLn) * 100;
            return (
              <FactorRow key={f.feature} feature={f.feature} or={f.odds_ratio} up={up} width={w} ciTxt={ci(f.ci_low, f.ci_high)} />
            );
          })}
        </tbody>
      </table>
      <div className="note">
        모델 점수(0~1)는 분포가 압축돼 있어 단계(매우 높음 등)는 상대 백분위로 표시합니다. 기여 요인은
        로지스틱 회귀의 전역 오즈비로 모든 격자에 공통 적용됩니다(1보다 크면 사고 오즈 증가, 작으면
        감소). 파고·파향은 관측 지점에서 제공되지 않아 거친 바다의 영향은 풍속으로 간접적으로만 반영됩니다.
      </div>
    </>
  );
}

function FactorRow({
  feature,
  or,
  up,
  width,
  ciTxt,
}: {
  feature: string;
  or: number;
  up: boolean;
  width: number;
  ciTxt: string;
}) {
  return (
    <>
      <tr>
        <td className="fac">{feature}</td>
        <td className="cond">
          95% CI {ciTxt}
          <span className={`dir ${up ? "up" : "down"}`}>{up ? "▲" : "▼"}</span>
        </td>
        <td className="val">{or2(or)}×</td>
      </tr>
      <tr>
        <td colSpan={3} style={{ padding: "0 0 8px" }}>
          <div className="cbar">
            <i
              className={`grow ${up ? "up" : "down"}`}
              style={{ width: `${Math.max(width, 4)}%` }}
            />
          </div>
        </td>
      </tr>
    </>
  );
}

function SummaryResult({
  grid,
  resolution,
}: {
  grid: GridCell;
  resolution: Resolution;
}) {
  return (
    <>
      <ScoreBox
        risk={grid.risk}
        level={grid.level}
        rightTop={<>위험도 점수 (0~1)</>}
        rightBottom={<>{percentileLabel(grid.pct)}</>}
      />
      <div className="kv">
        <span className="k">격자 좌표</span>
        <span className="v num">
          {grid.lat.toFixed(3)}°N, {grid.lon.toFixed(3)}°E
        </span>
      </div>
      <div className="kv">
        <span className="k">격자 내 누적 사고</span>
        <span className="v num">{int(grid.accidents)}건</span>
      </div>
      <div className="kv">
        <span className="k">매칭 표본</span>
        <span className="v num">{int(grid.samples)}건</span>
      </div>
      <div className="note">
        현재 해상도({parseFloat(resolution).toFixed(2)}°)에서는 요약만 제공합니다. 기여 요인과 과거 사고
        상세는 <b style={{ color: "var(--ink-2)" }}>0.10° 격자</b>에서 확인할 수 있습니다. 모델 점수는
        분포가 압축돼 있어 단계는 상대 백분위로 표시합니다.
      </div>
    </>
  );
}
