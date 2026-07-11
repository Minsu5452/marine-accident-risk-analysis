"use client";

import { useState } from "react";
import type { ModelData } from "../lib/data";
import type { OddsRatioStat, StatsData, XaiData } from "../lib/types";
import { ci, int, or2, pval, qval, sigClass, sigLabel, varLabel } from "../lib/format";

export default function StatsExplorer({
  stats,
  xai,
  model,
}: {
  stats: StatsData;
  xai: XaiData;
  model: ModelData;
}) {
  const [tab, setTab] = useState<"case" | "model">("case");
  const [varIdx, setVarIdx] = useState(0);

  return (
    <section className="panel stat">
      <div className="ph">
        <h2>통계 탐색 · 사고 시점 대조 분석</h2>
        <div className="tabs">
          <button className={tab === "case" ? "on" : ""} onClick={() => setTab("case")}>
            사고 시점 대조
          </button>
          <button className={tab === "model" ? "on" : ""} onClick={() => setTab("model")}>
            모델 기여도
          </button>
        </div>
      </div>
      {tab === "case" ? (
        <CaseView stats={stats} varIdx={varIdx} setVarIdx={setVarIdx} />
      ) : (
        <ModelView xai={xai} model={model} />
      )}
    </section>
  );
}

function qShort(q?: number): string {
  if (q == null) return "—";
  return q < 0.001 ? "<0.001" : q.toFixed(3);
}

function CaseView({
  stats,
  varIdx,
  setVarIdx,
}: {
  stats: StatsData;
  varIdx: number;
  setVarIdx: (i: number) => void;
}) {
  const uni = stats.overall_univariate;
  const cur = uni[varIdx] ?? uni[0];
  const maxAbsLn = Math.max(...uni.map((r) => Math.abs(Math.log(r.odds_ratio))), 1e-6);
  const grp = stats.by_type_group;
  const nWeather = grp.weather_sensitive.n_strata;
  const nMech = grp.mechanical.n_strata;

  return (
    <div className="sg">
      <div className="ctl">
        <div className="l">분석 변수</div>
        <div className="varlist">
          {uni.map((r, i) => (
            <button
              key={r.variable}
              className={`varitem${i === varIdx ? " on" : ""}`}
              onClick={() => setVarIdx(i)}
            >
              <span>{varLabel(r.variable)}</span>
              <span className="vm num">{or2(r.odds_ratio)}×</span>
            </button>
          ))}
        </div>
        <div className="meth">
          <b>시간층화 case-crossover</b> · 사고가 난 시각을 같은 자리에서 <b>같은 달·같은 요일·같은
          시각</b>의 다른 날들과 한 묶음으로 구성해, 조건부 로지스틱 회귀로 기상 1표준편차 증가당 사고
          오즈비를 추정합니다. 위치·계절·요일·시각은 묶음이 통제합니다. 다중 비교는{" "}
          <b>FDR(BH) α={stats.fdr_alpha}</b>로 보정합니다. 분석 묶음 {int(stats.n_strata)}건 · 사고당
          평균 대조 {stats.mean_referents_per_case.toFixed(1)}건.
        </div>
      </div>

      <div className="view">
        <div className="summ">
          <b>{varLabel(cur.variable)}</b>: 1표준편차 오를 때 사고 오즈 <b>{or2(cur.odds_ratio)}×</b>{" "}
          (95% CI {ci(cur.ci_low, cur.ci_high)}), {pval(cur.pvalue)} · FDR 보정{" "}
          {qval(cur.q_value ?? 1)} →{" "}
          <b>{cur.significant ? "통계적으로 유의" : "유의하지 않음"}</b>. 오즈비가 1보다 크면 값이
          높을수록 사고 오즈가 커지고, 작으면 줄어듭니다.
        </div>
        <div className="charts">
          <div>
            <h3>변수별 오즈비 (1표준편차 증가당)</h3>
            <div className="csub">1.0 기준 좌우 · 오른쪽이 오즈 증가 · 색이 진하면 보정 후 유의</div>
            <div className="ebars">
              {uni.map((r, i) => (
                <OrBar
                  key={r.variable}
                  r={r}
                  maxAbsLn={maxAbsLn}
                  selected={i === varIdx}
                  onClick={() => setVarIdx(i)}
                />
              ))}
            </div>
          </div>
          <div>
            <h3>변수별 조건부 로지스틱 결과</h3>
            <div className="csub">오즈비 · 95% CI · 보정 q값 · 유의성</div>
            <table className="stab">
              <thead>
                <tr>
                  <th>변수</th>
                  <th className="r">오즈비</th>
                  <th className="r">95% CI</th>
                  <th className="r">q값</th>
                  <th className="r">유의성</th>
                </tr>
              </thead>
              <tbody>
                {uni.map((r, i) => (
                  <tr key={r.variable} className={i === varIdx ? "sel" : ""}>
                    <td>{varLabel(r.variable)}</td>
                    <td className="r">
                      <b>{or2(r.odds_ratio)}×</b>
                    </td>
                    <td className="r">{ci(r.ci_low, r.ci_high)}</td>
                    <td className="r">{qShort(r.q_value)}</td>
                    <td className="r">
                      <span className={`sig ${sigClass(r.q_value ?? 1)}`}>
                        {sigLabel(r.q_value ?? 1)}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="grpcmp">
          <h3>사고 유형군별 오즈비</h3>
          <div className="csub">
            기상 민감형(충돌·좌초·전복 등 {int(nWeather)}건) vs 기계·비기상형(기관손상·부유물감김 등{" "}
            {int(nMech)}건)
          </div>
          <table className="stab">
            <thead>
              <tr>
                <th>변수</th>
                <th className="r">기상 민감형</th>
                <th className="r">기계·비기상형</th>
              </tr>
            </thead>
            <tbody>
              {uni.map((r) => {
                const g = grp.odds_ratios[r.variable];
                return (
                  <tr key={r.variable}>
                    <td>{varLabel(r.variable)}</td>
                    <OrGroupCell o={g?.weather_sensitive ?? null} />
                    <OrGroupCell o={g?.mechanical ?? null} />
                  </tr>
                );
              })}
            </tbody>
          </table>
          <div className="note">
            강한 기상 연관(풍속 오즈비 1 미만 · 기온 오즈비 1 초과)은 기계·비기상형 사고에 집중되어
            있습니다. 출항과 조업이 늘어나는 잔잔하고 따뜻한 날에 사고도 함께 늘어나는 것으로, 사고
            시점 기상의 연관은 위험 신호라기보다 활동·노출 패턴이 반영된 결과에 가깝습니다.
          </div>
        </div>
      </div>
    </div>
  );
}

function OrGroupCell({ o }: { o: OddsRatioStat | null }) {
  if (!o) {
    return (
      <td className="r" style={{ color: "var(--sub-3)" }}>
        —
      </td>
    );
  }
  const sig = o.pvalue < 0.05;
  return (
    <td className="r">
      <b style={{ color: sig ? "var(--ink)" : "var(--sub-2)" }}>{or2(o.odds_ratio)}×</b>
      <div style={{ fontSize: "10px", color: "var(--sub-3)", fontWeight: 400 }}>
        {ci(o.ci_low, o.ci_high)}
        {sig ? "" : " · 유의하지 않음"}
      </div>
    </td>
  );
}

function OrBar({
  r,
  maxAbsLn,
  selected,
  onClick,
}: {
  r: OddsRatioStat;
  maxAbsLn: number;
  selected: boolean;
  onClick: () => void;
}) {
  const ln = Math.log(r.odds_ratio);
  const up = ln >= 0;
  const w = (Math.abs(ln) / maxAbsLn) * 50;
  const style = up ? { left: "50%", width: `${w}%` } : { right: "50%", width: `${w}%` };
  return (
    <button
      className={`ebar${r.significant ? " sig" : ""}${selected ? " sel" : ""}`}
      onClick={onClick}
      style={{
        border: 0,
        background: "transparent",
        padding: 0,
        cursor: "pointer",
        textAlign: "left",
        fontFamily: "inherit",
        width: "100%",
      }}
    >
      <div className="lab">
        <span className="nm">{varLabel(r.variable)}</span>
        <span className="num">{or2(r.odds_ratio)}×</span>
      </div>
      <div className="track">
        <span className="mid" />
        <i style={style} />
      </div>
    </button>
  );
}

function ModelView({ xai, model }: { xai: XaiData; model: ModelData }) {
  const ors = xai.odds_ratios
    .filter((o) => o.feature !== "(상수)")
    .map((o) => ({ ...o, mag: Math.abs(Math.log(o.odds_ratio)) }))
    .sort((a, b) => b.mag - a.mag)
    .slice(0, 8);

  const imps = [...xai.permutation_importance]
    .sort((a, b) => b.auc_drop - a.auc_drop)
    .slice(0, 8);
  const maxDrop = Math.max(...imps.map((i) => i.auc_drop), 1e-6);

  const resRows = Object.entries(model.by_resolution).sort(
    (a, b) => parseFloat(a[0]) - parseFloat(b[0]),
  );

  return (
    <div className="sg">
      <div className="ctl">
        <div className="l">모델 성능 (검증 AUC)</div>
        <table className="stab">
          <thead>
            <tr>
              <th>해상도</th>
              <th className="r">로지스틱</th>
              <th className="r">LightGBM</th>
            </tr>
          </thead>
          <tbody>
            {resRows.map(([res, m]) => (
              <tr key={res}>
                <td className="num">{parseFloat(res).toFixed(2)}°</td>
                <td className="r">{m.metrics.logistic.auc.toFixed(3)}</td>
                <td className="r">{m.metrics.lightgbm ? m.metrics.lightgbm.auc.toFixed(3) : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="meth">
          오즈비는 <b>로지스틱 회귀</b> 계수(사고=1)이며, 순열 중요도는 변수를 섞었을 때의{" "}
          <b>AUC 감소폭</b>입니다(클수록 기여 큼). 표본 {int(xai.n)}건 · {xai.resolution.toFixed(2)}°
          기준. 단계별 위험도 점수는 LightGBM, 근거 해석은 로지스틱 오즈비로 봅니다.
        </div>
      </div>

      <div className="view">
        <div className="charts">
          <div>
            <h3>로지스틱 오즈비 (영향 큰 순)</h3>
            <div className="csub">1보다 크면 사고 오즈 증가 · 95% 신뢰구간</div>
            <table className="stab">
              <thead>
                <tr>
                  <th>변수</th>
                  <th className="r">오즈비</th>
                  <th className="r">95% CI</th>
                  <th className="r">p값</th>
                </tr>
              </thead>
              <tbody>
                {ors.map((o) => (
                  <tr key={o.feature}>
                    <td>{o.feature}</td>
                    <td className="r">
                      <b>{or2(o.odds_ratio)}×</b>
                    </td>
                    <td className="r">{ci(o.ci_low, o.ci_high)}</td>
                    <td className="r">
                      <span className={`sig ${sigClass(o.pvalue)}`}>{pval(o.pvalue)}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div>
            <h3>순열 중요도 (AUC 감소)</h3>
            <div className="csub">변수를 섞었을 때 떨어지는 AUC · 클수록 기여 큼</div>
            <div className="ebars">
              {imps.map((im) => {
                const w = Math.max((im.auc_drop / maxDrop) * 100, 0);
                return (
                  <div key={im.feature} className="ebar sig">
                    <div className="lab">
                      <span className="nm">{im.feature}</span>
                      <span className="num">{im.auc_drop.toFixed(3)}</span>
                    </div>
                    <div className="track">
                      <i style={{ left: 0, width: `${w}%` }} />
                    </div>
                  </div>
                );
              })}
            </div>
            <div className="note">
              순열 중요도가 음수에 가까우면 해당 변수의 기여가 사실상 없다는 뜻입니다.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
