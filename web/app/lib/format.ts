import type { RiskLevel } from "./types";

// 위험 = 웜 단색 램프 (사고 심각도 직관, 저→고)
// globals.css 의 --t0..--t4 와 같은 값이어야 한다(단일 출처). 한쪽을 바꾸면 다른 쪽도 함께 바꾼다.
export const RAMP = ["#fbf1e0", "#fad9a4", "#f4a65a", "#e8703f", "#c8392b"] as const;

interface LevelStyle {
  label: string;
  color: string; // 채움/스와치 색
  on: string; // 배지 텍스트 색
  bg: string; // 배지 배경
}

export const LEVELS: RiskLevel[] = ["veryhigh", "high", "mid", "low", "verylow"];

// color/bg 의 웜 스톱은 RAMP(=globals.css --t0..--t4)와 같은 값을 쓴다
export const LEVEL_STYLE: Record<RiskLevel, LevelStyle> = {
  veryhigh: { label: "매우 높음", color: "#c8392b", on: "#ffffff", bg: "#c8392b" },
  high: { label: "높음", color: "#e8703f", on: "#ffffff", bg: "#e8703f" },
  mid: { label: "보통", color: "#f4a65a", on: "#7a3b12", bg: "#fcefe4" },
  low: { label: "낮음", color: "#fad9a4", on: "#7a5a1e", bg: "#fbf1e0" },
  verylow: { label: "매우 낮음", color: "#fbf1e0", on: "#69707b", bg: "#f4f5f7" },
};

export function levelColor(level: RiskLevel): string {
  return LEVEL_STYLE[level]?.color ?? "#fbf1e0";
}

// 숫자 포매팅 — 표는 tabular-nums(.num)로 정렬
export function int(n: number): string {
  return n.toLocaleString("ko-KR");
}

export function risk2(r: number): string {
  return r.toFixed(2);
}

export function or2(or: number): string {
  return or.toFixed(2);
}

export function ci(lo: number, hi: number): string {
  return `[${lo.toFixed(2)}, ${hi.toFixed(2)}]`;
}

export function effect3(e: number): string {
  return `${e >= 0 ? "+" : ""}${e.toFixed(3)}`;
}

// p값/q값 표기 (작은 값은 임계 표기)
export function pval(p: number): string {
  if (p < 0.001) return "p<0.001";
  return `p=${p.toFixed(3)}`;
}

export function qval(q: number): string {
  if (q < 0.001) return "q<0.001";
  return `q=${q.toFixed(3)}`;
}

// 유의성 배지 — 다중 비교 보정 후 q값 기준
export function sigClass(q: number): "s1" | "s2" | "ns" {
  if (q < 0.01) return "s1";
  if (q < 0.05) return "s2";
  return "ns";
}

export function sigLabel(q: number): string {
  if (q < 0.01) return "q<0.01";
  if (q < 0.05) return "q<0.05";
  return "n.s.";
}

export function casualty(n: number): string {
  return n > 0 ? `${n}명` : "—";
}

// 0.10° 상세: 순위 기반 상위 백분위
export function topPctByRank(rank: number, total: number): string {
  const pct = (rank / total) * 100;
  return pct < 1 ? "상위 1% 이내" : `상위 ${pct.toFixed(0)}%`;
}

// grid 셀: 백분위(pct, 1=최상위)
export function percentileLabel(pct: number): string {
  return `백분위 ${(pct * 100).toFixed(0)} / 100`;
}

// past[]에서 가장 잦은 사고 유형 1~2개
export function topAccidentTypes(
  past: { accident_type: string }[],
  k = 2,
): string {
  if (!past.length) return "—";
  const counts = new Map<string, number>();
  for (const p of past) counts.set(p.accident_type, (counts.get(p.accident_type) ?? 0) + 1);
  return [...counts.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, k)
    .map(([t]) => t)
    .join(" · ");
}
