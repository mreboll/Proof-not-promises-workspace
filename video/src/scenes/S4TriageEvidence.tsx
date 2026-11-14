import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { lerp, pop } from "../anim";
import { Character } from "../components/Character";
import { Backdrop, Draw, Eyebrow, Words } from "../components/Stage";
import data from "../data/video-data.json";
import { C, FONT, glow } from "../theme";
import { at } from "../cues";
import { FunnelStrip } from "./S3Command";


type Bin = "low" | "high" | "out";
const POOLS: Record<Bin, { x: number; color: string; label: string; count: number; width: number }> = {
  low: { x: 420, color: C.mint, label: "low risk", count: data.lowIn, width: 40 },
  high: { x: 960, color: C.red, label: "high risk", count: data.highIn, width: 10 },
  out: { x: 1500, color: C.amber, label: "out of scope", count: data.outOfScope, width: 6 },
};
const SCAN_Y = 300;
const POOL_Y = 740;

// Reparto determinista: las de riesgo alto y fuera de alcance, intercaladas entre las de riesgo bajo.
function binOf(i: number): Bin {
  if (i % 19 === 7 && i < 19 * data.highIn) return "high";
  if (i === 100 || i === 200) return "out";
  return "low";
}

function channel(bin: Bin): string {
  const x = POOLS[bin].x;
  return `M960 ${SCAN_Y + 20} C960 520 ${x} 500 ${x} ${POOL_Y - 70}`;
}

function bezier(bin: Bin, t: number): { x: number; y: number } {
  const x3 = POOLS[bin].x;
  const p = [[960, SCAN_Y + 20], [960, 520], [x3, 500], [x3, POOL_Y - 70]];
  const u = 1 - t;
  return {
    x: u * u * u * p[0][0] + 3 * u * u * t * p[1][0] + 3 * u * t * t * p[2][0] + t * t * t * p[3][0],
    y: u * u * u * p[0][1] + 3 * u * u * t * p[1][1] + 3 * u * t * t * p[2][1] + t * t * t * p[3][1],
  };
}

/** 4a · El tamiz: 237 partículas, un escáner de reglas estáticas y un Sankey hacia tres depósitos. */
function Sieve({ frame, until }: { frame: number; until: number }) {
  const step = Math.max(0.3, (until - 70) / data.files);
  const arrived: Record<Bin, number> = { low: 0, high: 0, out: 0 };
  const dots = Array.from({ length: data.files }, (_, i) => {
    const bin = binOf(i);
    const start = 8 + i * step;
    const fall = lerp(frame, [start, start + 10], [0, 1]);
    const flow = lerp(frame, [start + 10, start + 38], [0, 1]);
    if (flow >= 1) arrived[bin]++;
    if (fall <= 0 || flow >= 1) return null;
    const pos = flow > 0 ? bezier(bin, flow) : { x: 960 + ((i % 7) - 3) * 6, y: 130 + fall * (SCAN_Y + 20 - 130) };
    const color = flow > 0 ? POOLS[bin].color : C.fg2;
    return <circle key={i} cx={pos.x} cy={pos.y} r={6} fill={color} style={{ filter: flow > 0 ? `drop-shadow(0 0 6px ${color})` : undefined }} />;
  });
  const scanPulse = 0.6 + 0.4 * Math.sin(frame / 3);

  return (
    <>
      <svg style={{ position: "absolute", left: 0, top: 0 }} width={1920} height={1080}>
        {(Object.keys(POOLS) as Bin[]).map((b) => (
          <g key={b} opacity={0.45}><Draw d={channel(b)} start={10} duration={40} length={1100} color={POOLS[b].color} width={POOLS[b].width} glowOn={false} /></g>
        ))}
        <rect x={700} y={SCAN_Y} width={520} height={10} rx={5} fill={C.cyan} opacity={scanPulse} style={{ filter: `drop-shadow(0 0 14px ${C.cyan})` }} />
        {dots}
      </svg>
      <div style={{ position: "absolute", left: 1240, top: SCAN_Y - 18, font: `700 24px ${FONT.mono}`, color: C.cyan, letterSpacing: 3 }}>📏 STATIC RULES</div>
      <div style={{ position: "absolute", left: 1240, top: SCAN_Y + 14, font: `500 22px/1.4 ${FONT.sans}`, color: C.fg2 }}>
        risk: static rules, not a model
        <br />
        scope: Gemini reads the literal issue
      </div>
      {(Object.keys(POOLS) as Bin[]).map((b) => {
        const pool = POOLS[b];
        const n = Math.min(pool.count, arrived[b]);
        return (
          <div key={b} style={{ position: "absolute", left: pool.x, top: POOL_Y, transform: "translate(-50%, -50%)", textAlign: "center" }}>
            <div style={{ width: 230, height: 70, borderRadius: "50%", border: `3px solid ${pool.color}`, background: `${pool.color}22`, boxShadow: glow(pool.color, 0.6), margin: "0 auto" }} />
            <div style={{ font: `800 84px ${FONT.mono}`, color: pool.color, textShadow: glow(pool.color, 0.5), marginTop: 6 }}>{n}</div>
            <div style={{ font: `700 24px ${FONT.sans}`, color: C.fg, letterSpacing: 3, textTransform: "uppercase" }}>{pool.label}</div>
          </div>
        );
      })}
      {frame > 60 && (
        <div style={{ position: "absolute", right: 70, top: POOL_Y - 300, opacity: pop(frame, 60), transform: `scale(${0.85 + 0.15 * pop(frame, 60)})`, transformOrigin: "right top", padding: "14px 20px", borderRadius: 14, border: `3px solid ${C.red}`, background: C.panel, boxShadow: glow(C.red, 0.6), textAlign: "right" }}>
          <div style={{ font: `700 24px ${FONT.mono}`, color: C.amber }}>TransformUtilities.cs</div>
          <div style={{ font: `700 22px ${FONT.sans}`, color: C.fg, marginTop: 4 }}>Nobody asked for this change</div>
          <div style={{ font: `500 20px ${FONT.sans}`, color: C.red, marginTop: 2 }}>out of scope + high risk → red</div>
        </div>
      )}
      <div style={{ position: "absolute", left: POOLS.low.x, top: POOL_Y + 132, transform: "translateX(-50%)", font: `500 22px ${FONT.sans}`, color: C.fg2, whiteSpace: "nowrap" }}>{data.snapshots} are generated snapshots</div>
    </>
  );
}

/** 4b · Dos mundos: el test escrito sin ver el arreglo falla en BASE y pasa en PR. */
function Worlds({ frame, hit }: { frame: number; hit: number }) {
  const split = lerp(frame, [hit - 40, hit - 4], [0, 1]);
  const leftC = frame > hit ? C.red : C.cyan;
  const rightC = frame > hit ? C.mint : C.cyan;
  const capsule = (side: -1 | 1) => {
    const x = 960 + side * 430 * split;
    const y = 360 + 230 * split;
    return frame > hit - 44 && frame < hit ? (
      <div key={side} style={{ position: "absolute", left: x, top: y, transform: "translate(-50%, -50%)", padding: "8px 18px", borderRadius: 999, background: C.mint, color: C.bg, font: `700 20px ${FONT.mono}`, boxShadow: glow(C.mint, 1) }}>test</div>
    ) : null;
  };
  const impact = pop(frame, hit);
  const labels = lerp(frame, [hit + 10, hit + 20], [0, 1]);
  return (
    <>
      <div style={{ position: "absolute", left: 0, top: 380, width: 960, height: 600, background: `linear-gradient(180deg, transparent, ${leftC}22)` }} />
      <div style={{ position: "absolute", left: 960, top: 380, width: 960, height: 600, background: `linear-gradient(180deg, transparent, ${rightC}22)` }} />
      <div style={{ position: "absolute", left: 958, top: 380, width: 4, height: 600, background: C.cyan, boxShadow: glow(C.cyan, 1) }} />
      <Eyebrow style={{ position: "absolute", left: 120, top: 410 }}>BASE · before the fix · Modal sandbox</Eyebrow>
      <Eyebrow style={{ position: "absolute", right: 120, top: 410, textAlign: "right" }}>PR · after the fix · Modal sandbox</Eyebrow>
      <Character kind="gemini" x={960} y={250} scale={0.62} blindfold />
      <div style={{ position: "absolute", left: 1090, top: 190, font: `600 24px ${FONT.mono}`, color: C.fg }}>
        issue #2297.md
        <div style={{ font: `500 20px ${FONT.sans}`, color: C.fg2 }}>its only input · never sees the fix</div>
      </div>
      {capsule(-1)}
      {capsule(1)}
      {frame > hit && (
        <>
          <div style={{ position: "absolute", left: 530, top: 690, transform: `translate(-50%, -50%) scale(${impact})`, font: `800 200px ${FONT.sans}`, color: C.red, textShadow: glow(C.red, 1) }}>✗</div>
          <div style={{ position: "absolute", left: 1390, top: 690, transform: `translate(-50%, -50%) scale(${impact})`, font: `800 200px ${FONT.sans}`, color: C.mint, textShadow: glow(C.mint, 1) }}>✓</div>
          <div style={{ position: "absolute", left: 530, top: 860, transform: "translateX(-50%)", font: `700 34px ${FONT.sans}`, color: C.fg, opacity: labels }}>fails before</div>
          <div style={{ position: "absolute", left: 1390, top: 860, transform: "translateX(-50%)", font: `700 34px ${FONT.sans}`, color: C.fg, opacity: labels }}>passes after</div>
        </>
      )}
    </>
  );
}

const hexPoints = (r: number): string =>
  Array.from({ length: 6 }, (_, k) => {
    const a = (Math.PI / 3) * k - Math.PI / 2;
    return `${(r * Math.cos(a)).toFixed(1)},${(r * Math.sin(a)).toFixed(1)}`;
  }).join(" ");

const halfHex = (r: number, side: "L" | "R"): string => {
  // Media celda: el lado izquierdo o derecho del hexágono (punta arriba y abajo).
  const pts = side === "L" ? [[0, -r], [-r * 0.866, -r / 2], [-r * 0.866, r / 2], [0, r]] : [[0, -r], [r * 0.866, -r / 2], [r * 0.866, r / 2], [0, r]];
  return pts.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
};

/**
 * 4c · El panal: los 21 casos generales (los que cuenta la invarianza en los informes) más el del issue. En los generales, BASE y PR coinciden;
 * el caso del propio issue (el último) cambia, como pide el issue: eso demuestra que el oráculo distingue.
 */
function Hive({ frame }: { frame: number }) {
  const R = 58;
  const issueCase = data.generalCases;
  const outside = data.generalCases;
  const cells = Array.from({ length: data.generalCases + 1 }, (_, i) => {
    const row = Math.floor(i / 8);
    const col = i % 8;
    return { i, x: 960 + (col - 3.5) * R * 1.8 + (row % 2) * R * 0.9, y: 470 + row * R * 1.6, row, col };
  });
  return (
    <>
      <div style={{ position: "absolute", top: 220, width: "100%", padding: "0 160px", boxSizing: "border-box" }}>
        <Words text={`${outside} general cases outside the issue: generated code identical`} start={4} every={2} size={46} weight={700} highlight={{ 0: C.mint }} />
      </div>
      <svg style={{ position: "absolute", left: 0, top: 0 }} width={1920} height={1080}>
        {cells.map(({ i, x, y, row, col }) => {
          const s = 10 + (Math.abs(col - 3.5) + row) * 5;
          const gap = lerp(frame, [s, s + 18], [28, 0]);
          const merged = frame > s + 18;
          const isIssue = i === issueCase;
          const doneColor = isIssue ? C.amber : C.mint;
          const color = merged ? doneColor : C.cyan;
          const fx = merged ? `drop-shadow(0 0 8px ${doneColor})` : undefined;
          const label = merged ? (isIssue ? "≠" : "=") : "base|PR";
          return (
            <g key={i} transform={`translate(${x} ${y})`} opacity={lerp(frame, [s - 8, s], [0, 1])}>
              <polygon points={halfHex(R - 6, "L")} transform={`translate(${-gap} 0)`} fill={`${color}1f`} stroke={color} strokeWidth={3} style={{ filter: fx }} />
              <polygon points={halfHex(R - 6, "R")} transform={`translate(${gap} 0)`} fill={`${color}1f`} stroke={color} strokeWidth={3} style={{ filter: fx }} />
              {merged && <polygon points={hexPoints(R - 6)} fill="none" stroke={doneColor} strokeWidth={3} />}
              <text y={10} textAnchor="middle" fill={merged ? doneColor : C.fg2} style={{ font: `800 ${merged ? 30 : 15}px ${FONT.mono}` }}>{label}</text>
            </g>
          );
        })}
      </svg>
      <div style={{ position: "absolute", left: 0, width: "100%", textAlign: "center", top: 860, opacity: lerp(frame, [70, 82], [0, 1]), font: `600 26px ${FONT.sans}`, color: C.amber }}>
        ≠ 1 case: the issue's own, changed as asked
      </div>
    </>
  );
}

/** Escena 4: tamiz (4a), dos mundos (4b) y panal (4c). Entre partes, un barrido corto de luz. */
export function S4TriageEvidence() {
  const frame = useCurrentFrame();
  const worldsAt = at("triage", 1);
  const hiveAt = at("triage", 3);
  const part = frame < worldsAt ? 0 : frame < hiveAt ? 1 : 2;
  const local = part === 0 ? frame : part === 1 ? frame - worldsAt : frame - hiveAt;
  const wipe = part > 0 ? lerp(local, [0, 14], [0, 100]) : 100;
  return (
    <AbsoluteFill>
      <Backdrop />
      <FunnelStrip active={part === 0 ? 0 : 1} />
      <AbsoluteFill style={{ clipPath: `inset(0 ${100 - wipe}% 0 0)` }}>
        {part === 0 && <Sieve frame={local} until={worldsAt} />}
        {part === 1 && <Worlds frame={local} hit={at("triage", 2) - worldsAt + 6} />}
        {part === 2 && <Hive frame={local} />}
      </AbsoluteFill>
      {part > 0 && wipe < 100 && <div style={{ position: "absolute", left: `${wipe}%`, top: 0, width: 5, height: "100%", background: C.mint, boxShadow: glow(C.mint, 1.4) }} />}
    </AbsoluteFill>
  );
}
