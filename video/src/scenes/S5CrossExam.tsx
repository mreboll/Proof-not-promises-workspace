import React from "react";
import { AbsoluteFill, random, useCurrentFrame } from "remotion";
import { lerp, pop } from "../anim";
import { Character } from "../components/Character";
import { Backdrop, Eyebrow, Words } from "../components/Stage";
import { at } from "../cues";
import data from "../data/video-data.json";
import { C, FONT, glow } from "../theme";
import { FunnelStrip } from "./S3Command";

function Spotlight({ x, color }: { x: number; color: string }) {
  return <div style={{ position: "absolute", left: x - 260, top: 0, width: 520, height: 900, background: `linear-gradient(180deg, ${color}38, ${color}00 85%)`, clipPath: "polygon(42% 0, 58% 0, 100% 100%, 0 100%)" }} />;
}

/** El argumento del Defensor se rompe en fragmentos que salen despedidos. */
function Shatter({ text, x, y, appear, at: breakAt }: { text: string; x: number; y: number; appear: number; at: number }) {
  const frame = useCurrentFrame();
  const t = frame - breakAt;
  const pieces = 6;
  const bubble: React.CSSProperties = { padding: "18px 28px", borderRadius: 24, border: `3px solid ${C.fg2}`, background: C.panel, font: `500 30px ${FONT.sans}`, color: C.fg, whiteSpace: "nowrap" };
  if (t <= 0) {
    // Entero hasta que se rompe (con su pico hacia el Defensor).
    const s = pop(frame, appear);
    return (
      <div style={{ position: "absolute", left: x, top: y, transform: `translate(-50%, -50%) scale(${0.9 + 0.1 * s})` }}>
        <div style={bubble}>{text}</div>
        <div style={{ position: "absolute", right: 60, bottom: -18, width: 0, height: 0, borderLeft: "18px solid transparent", borderRight: "18px solid transparent", borderTop: `20px solid ${C.fg2}` }} />
      </div>
    );
  }
  return (
    <>
      {Array.from({ length: pieces }, (_, k) => {
        const dx = t > 0 ? (random(`dx${k}`) - 0.5) * t * 26 : 0;
        const dy = t > 0 ? (random(`dy${k}`) * 0.8 + 0.2) * t * t * 0.9 : 0;
        const rot = t > 0 ? (random(`r${k}`) - 0.5) * t * 9 : 0;
        const l = (k / pieces) * 100, r = ((k + 1) / pieces) * 100;
        return (
          <div key={k} style={{ position: "absolute", left: x, top: y, transform: `translate(-50%, -50%) translate(${dx}px, ${dy}px) rotate(${rot}deg)`, opacity: t > 0 ? Math.max(0, 1 - t / 26) : 1, clipPath: `polygon(${k === 0 ? -5 : l}% 0, ${r}% 0, ${k === pieces - 1 ? 105 : r + 4}% 100%, ${k === 0 ? -5 : l + 4}% 100%)`, ...bubble }}>
            {text}
          </div>
        );
      })}
    </>
  );
}

/** Código mutante con glitch RGB; al morir, estalla en píxeles. */
function Mutant({ x, y, dieAt }: { x: number; y: number; dieAt: number }) {
  const frame = useCurrentFrame();
  const jitter = (k: string) => (random(`${k}${Math.floor(frame / 2)}`) - 0.5) * 8;
  const code = "#if !NETSTANDARD2_0  // removed";
  if (frame >= dieAt) {
    const t = frame - dieAt;
    return (
      <>
        {Array.from({ length: 40 }, (_, k) => {
          const a = random(`a${k}`) * Math.PI * 2;
          const d = t * (6 + random(`d${k}`) * 10);
          return <div key={k} style={{ position: "absolute", left: x + Math.cos(a) * d, top: y + Math.sin(a) * d, width: 10, height: 10, background: k % 2 ? C.red : "#ff9a8f", opacity: Math.max(0, 1 - t / 24) }} />;
        })}
        <div style={{ position: "absolute", left: x, top: y, transform: `translate(-50%, -50%) scale(${pop(frame, dieAt)})`, font: `800 110px ${FONT.sans}`, color: C.red, textShadow: glow(C.red, 1) }}>✗</div>
        <Eyebrow color={C.red} style={{ position: "absolute", left: x, top: y + 70, transform: "translateX(-50%)", whiteSpace: "nowrap" }}>fails on the mutant</Eyebrow>
      </>
    );
  }
  return (
    <div style={{ position: "absolute", left: x, top: y, transform: "translate(-50%, -50%)" }}>
      {[C.red, C.cyan, C.fg].map((c, k) => (
        <div key={c} style={{ position: k === 2 ? "relative" : "absolute", left: k === 2 ? 0 : jitter(`x${k}`), top: k === 2 ? 0 : jitter(`y${k}`), font: `600 28px ${FONT.mono}`, color: c, opacity: k === 2 ? 1 : 0.7, whiteSpace: "nowrap", padding: "12px 18px", border: k === 2 ? `3px dashed ${C.red}` : undefined, borderRadius: 14, background: k === 2 ? "rgba(239,91,76,.08)" : undefined }}>
          {code}
        </div>
      ))}
      <div style={{ font: `600 22px ${FONT.sans}`, color: C.red, marginTop: 8, textAlign: "center" }}>😈 real mutant: the guard removed, on purpose</div>
    </div>
  );
}

/** 5a · El juicio. Todo se ancla a las dos primeras frases de la voz. */
function Trial({ frame }: { frame: number }) {
  const prosecutor = at("crossExam", 0);
  const defender = at("crossExam", 1);
  const breakAt = defender + 70; // el argumento se lee ~2,3 s antes de romperse
  const throwAt = breakAt + 36;
  const split = lerp(frame, [throwAt, throwAt + 18], [0, 1]);
  const prOk = pop(frame, throwAt + 20);
  return (
    <>
      <Spotlight x={300} color={C.green} />
      <Spotlight x={1620} color={C.cyan} />
      <Character kind="nemotron" x={300} y={600} scale={1.0} label="Prosecutor" talking={frame > prosecutor && frame < defender} />
      <Character kind="gemini" x={1620} y={600} scale={1.0} label="Defender" mirrored talking={frame > defender && frame < breakAt} />
      <Eyebrow color={C.fg2} style={{ position: "absolute", left: 560, top: 108 }}>high-risk file · {data.sampleObjectionFile}</Eyebrow>
      <div style={{ position: "absolute", left: 560, top: 150, width: 800 }}>
        <div style={{ font: `800 90px ${FONT.serif}`, color: C.mint, lineHeight: 0.6, textShadow: glow(C.mint, 0.6) }}>“</div>
        <Words text={data.sampleObjection} start={prosecutor} every={1} size={34} weight={600} align="left" lineHeight={1.3} />
      </div>
      {frame >= defender && <Shatter text="Trust me, the code looks correct." x={1310} y={420} appear={defender} at={breakAt} />}
      {frame >= breakAt - 22 && frame < breakAt + 4 && (
        <div style={{ position: "absolute", left: 1310, top: 420, transform: `translate(-50%, -50%) rotate(-8deg) scale(${0.6 + 0.4 * pop(frame, breakAt - 22)})`, opacity: pop(frame, breakAt - 22), padding: "6px 26px", border: `5px solid ${C.red}`, borderRadius: 10, color: C.red, font: `800 46px ${FONT.sans}`, letterSpacing: 4, background: "rgba(5,26,34,.85)", boxShadow: glow(C.red, 0.8) }}>
          REJECTED
        </div>
      )}
      {frame >= breakAt + 4 && (
        <div style={{ position: "absolute", left: 0, right: 0, top: 500 }}>
          <Words text="No arguments. Only tests." start={breakAt + 4} every={3} size={70} font={FONT.serif} weight={700} highlight={{ 0: C.red, 1: C.red, 2: C.mint, 3: C.mint }} />
        </div>
      )}
      {frame >= throwAt - 10 && frame < throwAt + 20 && (
        <div style={{ position: "absolute", left: 1480 - 500 * split, top: 620 + 150 * split, padding: "8px 18px", borderRadius: 999, background: C.mint, color: C.bg, font: `700 22px ${FONT.mono}`, boxShadow: glow(C.mint, 1) }}>test</div>
      )}
      {frame >= throwAt - 16 && (
        <>
          <div style={{ position: "absolute", left: 640, top: 790, transform: "translate(-50%, -50%)", textAlign: "center", opacity: lerp(frame, [throwAt - 16, throwAt - 4], [0, 1]) }}>
            <div style={{ width: 150, height: 150, borderRadius: "50%", border: `5px solid ${prOk > 0 ? C.mint : C.line}`, boxShadow: prOk > 0 ? glow(C.mint, 1.2) : undefined, display: "flex", alignItems: "center", justifyContent: "center", font: `800 ${74 * Math.max(0.01, prOk)}px ${FONT.sans}`, color: C.mint }}>✓</div>
            <Eyebrow color={C.fg} style={{ marginTop: 8 }}>passes on the PR</Eyebrow>
          </div>
          <Mutant x={1230} y={790} dieAt={throwAt + 26} />
        </>
      )}
    </>
  );
}

function Clock({ minutes, x, y, r = 130, color = C.cyan }: { minutes: number; x: number; y: number; r?: number; color?: string }) {
  const a = ((minutes % 60) / 60) * Math.PI * 2 - Math.PI / 2;
  const ha = (((minutes / 60) % 12) / 12) * Math.PI * 2 - Math.PI / 2;
  return (
    <svg style={{ position: "absolute", left: x - r - 10, top: y - r - 10 }} width={2 * r + 20} height={2 * r + 20}>
      <circle cx={r + 10} cy={r + 10} r={r} fill="none" stroke={color} strokeWidth={5} style={{ filter: `drop-shadow(0 0 10px ${color})` }} />
      {Array.from({ length: 12 }, (_, k) => {
        const t = (k / 12) * Math.PI * 2;
        return <line key={k} x1={r + 10 + Math.cos(t) * (r - 14)} y1={r + 10 + Math.sin(t) * (r - 14)} x2={r + 10 + Math.cos(t) * (r - 4)} y2={r + 10 + Math.sin(t) * (r - 4)} stroke={C.fg2} strokeWidth={3} />;
      })}
      <line x1={r + 10} y1={r + 10} x2={r + 10 + Math.cos(ha) * r * 0.5} y2={r + 10 + Math.sin(ha) * r * 0.5} stroke={C.fg} strokeWidth={8} strokeLinecap="round" />
      <line x1={r + 10} y1={r + 10} x2={r + 10 + Math.cos(a) * r * 0.82} y2={r + 10 + Math.sin(a) * r * 0.82} stroke={color} strokeWidth={5} strokeLinecap="round" />
    </svg>
  );
}

const fmt = (m: number): string => (m >= 60 ? `${Math.floor(m / 60)} h ${String(Math.floor(m % 60)).padStart(2, "0")} min` : `${Math.floor(m)} min`);

/** 5b · Una sola puerta: el reloj recorre la hora mientras dura la frase "One by one, that took over an hour". */
function Queue({ frame, length }: { frame: number; length: number }) {
  const minutes = lerp(frame, [4, length - 18], [0, 65]);
  const advance = frame * 0.06;
  const cancelled = length - 16;
  return (
    <>
      <div style={{ position: "absolute", top: 140, width: "100%" }}>
        <Words text={`One by one: ${data.objections} objections in one queue`} start={0} every={2} size={54} weight={800} highlight={{ 0: C.amber, 1: C.amber, 2: C.amber }} />
      </div>
      {Array.from({ length: data.objections }, (_, i) => {
        const x = 1340 - (i - advance) * 56;
        if (x > 1380 || x < -60) return null;
        return <div key={i} style={{ position: "absolute", left: x, top: 450, width: 44, height: 60, borderRadius: 22, background: i % 3 === 0 ? C.cyan : C.mint, opacity: 0.85, boxShadow: glow(C.mint, 0.3) }} />;
      })}
      <div style={{ position: "absolute", left: 1400, top: 400, width: 260, height: 160, borderRadius: 20, border: `4px solid ${C.mint}`, boxShadow: glow(C.mint, 0.8), background: "rgba(34,211,180,.06)", display: "flex", alignItems: "center", justifyContent: "center", font: `700 24px ${FONT.mono}`, color: C.mint }}>
        1 at a time
      </div>
      <Clock minutes={minutes} x={720} y={740} />
      <div style={{ position: "absolute", left: 900, top: 690, font: `800 80px ${FONT.mono}`, color: C.fg }}>{fmt(minutes)}</div>
      {frame > cancelled && (
        <div style={{ position: "absolute", left: 1180, top: 760, transform: `translate(-50%, -50%) rotate(-8deg) scale(${0.7 + 0.3 * pop(frame, cancelled)})`, opacity: pop(frame, cancelled), padding: "8px 34px", border: `6px solid ${C.red}`, borderRadius: 12, color: C.red, font: `800 60px ${FONT.sans}`, letterSpacing: 4, background: "rgba(5,26,34,.9)", boxShadow: glow(C.red, 0.8) }}>
          OVER 1 HOUR · CANCELLED
        </div>
      )}
    </>
  );
}

// Anillos de un panal alrededor del centro: 6 + 12 + 18 = 36 celdas, una por objeción.
const HEX_DIRS = [[1, 0], [1, -1], [0, -1], [-1, 0], [-1, 1], [0, 1]];
function hexRing(k: number): Array<[number, number]> {
  const out: Array<[number, number]> = [];
  let q = -k, r = k;
  for (let side = 0; side < 6; side++) {
    for (let step = 0; step < k; step++) {
      out.push([q, r]);
      q += HEX_DIRS[side][0];
      r += HEX_DIRS[side][1];
    }
  }
  return out;
}
const CELLS = [1, 2, 3].flatMap((k) => hexRing(k).map(([q, r]) => ({ q, r, ring: k })));
const OUTCOME = {
  valid: { color: C.mint, mark: "✓", label: "closed by a valid test" },
  red: { color: C.red, mark: "✗", label: "test fails on the PR: possible defect" },
  nothing: { color: C.amber, mark: "?", label: "test proved nothing" },
} as const;
type Outcome = keyof typeof OUTCOME;

// Cómo cubrimos lo que pide el track de Modal (texto del reto), sin coste ni pruebas de carga.
const MODAL_POINTS: Array<[string, string]> = [
  ["🔒", "Agent code in secure Sandboxes: every AI-written test runs isolated, network blocked"],
  ["⚡", `Fan-out: base, PR and every mutant each get their own sandbox, ${data.sandboxesTotal} in total, up to ${data.sandboxPeak} at once`],
  ["🐍", "Plain Python: .NET 8 image + prebuilt worktrees, no Dockerfile, no Kubernetes, no YAML"],
  ["🎯", "Modal does the heavy lifting, so our 48 h went into the verdict logic"],
];

/** 5c · En abanico: cada test a su sandbox, a la vez. Cada celda muestra el resultado REAL de su objeción. */
function Fan({ frame, honest }: { frame: number; honest: number }) {
  const S = 50;
  const cx = 960, cy = 590;
  const minutes = lerp(frame, [10, honest - 10], [0, data.parallelMinutes]);
  const hex = (r: number) => Array.from({ length: 6 }, (_, k) => {
    const a = (Math.PI / 3) * k - Math.PI / 2;
    return `${(r * Math.cos(a)).toFixed(1)},${(r * Math.sin(a)).toFixed(1)}`;
  }).join(" ");
  const outcomes = data.objectionOutcomes as Outcome[];
  const counts = data.outcomeCounts as Record<Outcome, number>;
  return (
    <>
      <div style={{ position: "absolute", top: 120, width: "100%" }}>
        <Words text="In parallel: each test in its own sandbox" start={0} every={2} size={54} weight={800} highlight={{ 0: C.mint, 1: C.mint }} />
      </div>
      <div style={{ position: "absolute", top: 196, width: "100%", textAlign: "center", font: `500 24px ${FONT.mono}`, color: C.fg2, opacity: lerp(frame, [30, 50], [0, 1]) }}>
        every AI-written test in its own Modal Sandbox
      </div>
      <svg style={{ position: "absolute", left: 0, top: 0 }} width={1920} height={1080}>
        {CELLS.map(({ q, r, ring }, i) => {
          const x = cx + S * Math.sqrt(3) * (q + r / 2);
          const y = cy + S * 1.5 * r;
          const fly = lerp(frame, [2 + ring * 3, 16 + ring * 3], [0, 1]);
          const done = frame > 24 + ring * 12 + (i % 6) * 4;
          const o = OUTCOME[outcomes[i] ?? "nothing"];
          const px = cx + (x - cx) * fly, py = cy + (y - cy) * fly;
          return (
            <g key={i}>
              <polygon points={hex(S - 5)} transform={`translate(${x} ${y})`} fill={done ? `${o.color}2e` : "rgba(42,147,201,.06)"} stroke={done ? o.color : C.cyan} strokeWidth={3} opacity={fly} style={{ filter: done ? `drop-shadow(0 0 8px ${o.color})` : undefined }} />
              {!done && <circle cx={px} cy={py} r={9} fill={C.mint} style={{ filter: `drop-shadow(0 0 8px ${C.mint})` }} />}
              {done && <text x={x} y={y + 10} textAnchor="middle" fill={o.color} style={{ font: `800 28px ${FONT.sans}` }}>{o.mark}</text>}
            </g>
          );
        })}
        <polygon points={hex(S - 5)} transform={`translate(${cx} ${cy})`} fill={C.mint} style={{ filter: `drop-shadow(0 0 18px ${C.mint})` }} />
        <text x={cx} y={cy + 10} textAnchor="middle" fill={C.bg} style={{ font: `800 26px ${FONT.mono}` }}>T3</text>
      </svg>
      <Character kind="nemotron" x={190} y={430} scale={0.5} talking />
      <Character kind="gemini" x={190} y={700} scale={0.5} talking />
      <div style={{ position: "absolute", left: 1350, top: 340, font: `800 64px ${FONT.mono}`, color: C.mint, textShadow: glow(C.mint, 0.6) }}>⏱ {fmt(minutes)}</div>
      <div style={{ position: "absolute", left: 1350, top: 420, font: `600 24px ${FONT.sans}`, color: C.fg2, opacity: lerp(frame, [honest - 30, honest - 14], [0, 1]) }}>
        {data.parallelRangeMin[0]}–{data.parallelRangeMin[1]} min over 4 real runs
      </div>
      {frame < honest && (
        <div style={{ position: "absolute", left: 1330, top: 480, width: 540, opacity: lerp(frame, [8, 20], [0, 1]) * lerp(frame, [honest - 8, honest], [1, 0]), padding: "22px 26px", borderRadius: 18, border: `2px solid ${C.mint}`, background: "rgba(34,211,180,.07)", boxShadow: glow(C.mint, 0.4) }}>
          <Eyebrow color={C.mint}>powered by Modal</Eyebrow>
          {MODAL_POINTS.map(([icon, text], n) => (
            <div key={text} style={{ display: "flex", gap: 12, marginTop: 12, font: `500 22px/1.35 ${FONT.sans}`, color: C.fg, opacity: lerp(frame, [12 + n * 6, 22 + n * 6], [0, 1]) }}>
              <span style={{ width: 28 }}>{icon}</span>
              <span>{text}</span>
            </div>
          ))}
        </div>
      )}
      {frame >= honest && (
        <div style={{ position: "absolute", left: 1350, top: 480, width: 520 }}>
          <Eyebrow color={C.fg2} style={{ opacity: pop(frame, honest) }}>{data.objections} objections · result of each</Eyebrow>
          {(Object.keys(OUTCOME) as Outcome[]).map((k, n) => (
            <div key={k} style={{ display: "flex", alignItems: "baseline", gap: 14, marginTop: 14, opacity: pop(frame, honest + n * 8), transform: `translateX(${(1 - pop(frame, honest + n * 8)) * 30}px)` }}>
              <span style={{ font: `800 54px ${FONT.mono}`, color: OUTCOME[k].color, width: 76, textShadow: glow(OUTCOME[k].color, 0.5) }}>{counts[k]}</span>
              <span style={{ font: `600 26px ${FONT.sans}`, color: C.fg }}>{OUTCOME[k].label}</span>
            </div>
          ))}
        </div>
      )}
    </>
  );
}

/** Escena 5: juicio (5a), una sola puerta (5b) y en abanico (5c), cada parte con su frase de la voz. */
export function S5CrossExam() {
  const frame = useCurrentFrame();
  const queueAt = at("crossExam", 2);
  const fanAt = at("crossExam", 3);
  const honestAt = at("crossExam", 4);
  const part = frame < queueAt ? 0 : frame < fanAt ? 1 : 2;
  const local = part === 0 ? frame : part === 1 ? frame - queueAt : frame - fanAt;
  const burst = part === 2 ? lerp(local, [0, 6, 18], [0, 0.5, 0]) : 0;
  return (
    <AbsoluteFill>
      <Backdrop spot={{ x: 50, y: 60 }} />
      <FunnelStrip active={2} />
      {part === 0 && <Trial frame={local} />}
      {part === 1 && (
        <AbsoluteFill style={{ clipPath: `inset(${100 - lerp(local, [0, 12], [0, 100])}% 0 0 0)` }}>
          <Queue frame={local} length={fanAt - queueAt} />
        </AbsoluteFill>
      )}
      {part === 2 && <Fan frame={local} honest={honestAt - fanAt} />}
      <AbsoluteFill style={{ background: `radial-gradient(circle at 50% 55%, ${C.mint}, transparent 60%)`, opacity: burst }} />
    </AbsoluteFill>
  );
}
