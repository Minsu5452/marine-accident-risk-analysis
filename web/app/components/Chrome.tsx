import type { Meta, Resolution } from "../lib/types";
import { int } from "../lib/format";

function WaveMark() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M3 15.5q2.4-2.3 4.8 0t4.8 0 4.8 0 3.6 0"
        stroke="#fff"
        strokeWidth="1.7"
        strokeLinecap="round"
        fill="none"
      />
      <path
        d="M3 19q2.4-2.3 4.8 0t4.8 0 4.8 0 3.6 0"
        stroke="#C5CCF4"
        strokeWidth="1.5"
        strokeLinecap="round"
        fill="none"
      />
      <path
        d="M8.5 11.5h7l-1.3-2.6h-4.4z"
        stroke="#fff"
        strokeWidth="1.5"
        fill="none"
        strokeLinejoin="round"
      />
      <line x1="12" y1="8.9" x2="12" y2="5.6" stroke="#fff" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

export function Header({ period }: { period: string }) {
  return (
    <header className="top">
      <div className="wrap">
        <div className="brand">
          <span className="logo">
            <WaveMark />
          </span>
          <span className="nm">
            <b>연안 해양사고 위험 지도</b>
            <span>격자×시간 위험도 · 기상 근거 탐색</span>
          </span>
        </div>
        <div className="right">
          <span className="ghostchip">현장 순찰 검토용 화면</span>
          <span className="ghostchip">데이터 기준 {period}</span>
          <span
            className="livebadge"
            title="실제 분석 실행 결과를 키 없이 그대로 재생하는 정적 데모입니다."
          >
            <span className="d" aria-hidden="true" />
            정적 데모 · 실행 기록 재생
          </span>
        </div>
      </div>
    </header>
  );
}

export function Hero() {
  return (
    <div className="head">
      <h1>연안 위험, 지도에서 바로 확인</h1>
      <p className="lead">
        2018–2025년 전국 해양사고 기록과 연안 해양기상 관측을 결합해, 격자×시간 단위 위험도를 지도에
        펼쳐 보여줍니다. 격자를 고르면 위험을 높인 기상 근거를 함께 확인할 수 있습니다. 해양경찰
        순찰 배치 검토를 가정한 화면입니다.
      </p>
      <div className="src">
        <span>
          자료 <b>MTIS 해양사고</b> · <b>NMPNT 해양기상</b>
        </span>
        <span>
          매칭 임계 <b>60 km · ±30분</b>
        </span>
        <span>
          통계 <b>시간층화 case-crossover · 조건부 로지스틱</b>
        </span>
      </div>
    </div>
  );
}

function years(period: string): { start: string; end: string; span: number } {
  const m = period.split(/[–-]/).map((s) => s.trim());
  const start = m[0] ?? "";
  const end = m[1] ?? "";
  const span = Number(end) && Number(start) ? Number(end) - Number(start) + 1 : 0;
  return { start, end, span };
}

export function Kpi({ meta, resolution }: { meta: Meta; resolution: Resolution }) {
  const { start, end, span } = years(meta.period);
  const resNum = parseFloat(resolution);
  const km = Math.round(resNum * 111);
  const highRisk = meta.high_risk_count[resolution] ?? 0;
  return (
    <div className="kpi">
      <div className="cell rise" style={{ animationDelay: ".02s" }}>
        <div className="lab">분석 기간</div>
        <div className="big num rng">
          {start}–{end}
        </div>
        <div className="sub">{span}개년 · 시 단위 매칭</div>
      </div>
      <div className="cell rise" style={{ animationDelay: ".07s" }}>
        <div className="lab">정제 사고</div>
        <div className="big num">
          {int(meta.accidents)}
          <span className="u">건</span>
        </div>
        <div className="sub">좌표 정제 후 · MTIS 2017–2025</div>
      </div>
      <div className="cell rise" style={{ animationDelay: ".12s" }}>
        <div className="lab">관측 지점</div>
        <div className="big num">
          {int(meta.stations)}
          <span className="u">개소</span>
        </div>
        <div className="sub">연안 해양기상 · NMPNT</div>
      </div>
      <div className="cell rise" style={{ animationDelay: ".17s" }}>
        <div className="lab">고위험 격자</div>
        <div className="big num">
          {int(highRisk)}
          <span className="u">셀</span>
        </div>
        <div className="sub">
          {meta.high_risk_def} · {resNum.toFixed(2)}° 기준
        </div>
      </div>
      <div className="cell rise" style={{ animationDelay: ".22s" }}>
        <div className="lab">격자 해상도</div>
        <div className="big num">{resNum.toFixed(2)}°</div>
        <div className="sub">≈{km} km · 0.05·0.25 전환</div>
      </div>
    </div>
  );
}

export function Notice() {
  return (
    <div className="notice">
      <span className="i">i</span>
      <span>
        <b>분석 참고용 화면입니다.</b> 표시된 위험도는 과거 사고와 해양기상 관측을 결합한 통계 모델
        추정치로, 실제 순찰 배치 지침이 아니며 현장 판단을 대체하지 않습니다. 화면의 수치는 실제 분석
        실행 결과를 그대로 재생한 값입니다.
      </span>
    </div>
  );
}

export function Footer() {
  return (
    <footer>
      <div className="wrap">
        <div className="fb">
          <span className="logo">
            <WaveMark />
          </span>
          <span className="nm">
            <b>연안 해양사고 위험 지도</b>
            <br />
            <span>격자×시간 위험도 · 기상 근거 탐색</span>
          </span>
        </div>
        <div className="meta">
          사고 자료 <b>MTIS · 한국해양교통안전공단(KOMSA)</b>
          <br />
          기상 자료 <b>국립해양측위정보원(NMPNT)</b> 연안 관측 76개소
          <br />
          분석 기간 2018–2025
        </div>
        <div className="disc">
          본 화면은 포트폴리오 데모이며 특정 기관의 실제 운영 서비스가 아닙니다. 지도·위험도·통계·순위는
          공개 데이터로 직접 분석한 실제 실행 결과를 키 없이 그대로 재생합니다. 위험도 점수는 실제
          모델값이며, 파고·파향은 관측 지점에서 제공되지 않아 거친 바다의 영향은 풍속으로 간접적으로만 반영됩니다. 분석 참고용이며
          실제 순찰 배치 지침이 아닙니다. © 2026
        </div>
      </div>
    </footer>
  );
}
