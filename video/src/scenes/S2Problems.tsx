import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { lerp } from "../anim";
import { Backdrop, Draw, Words } from "../components/Stage";
import { at } from "../cues";
import data from "../data/video-data.json";
import { C, FONT } from "../theme";


// Pictogramas que se dibujan solos (coordenadas en una caja de 220×160).
function Pictogram({ kind, start }: { kind: number; start: number }) {
  const frame = useCurrentFrame();
  const t = frame - start;
  return (
    <svg width={220} height={160} viewBox="0 0 220 160" style={{ overflow: "visible" }}>
      {kind === 0 && (
        <>
          {/* documento que corre sin fin */}
          <Draw d="M60 10 H150 L175 35 V150 H60 Z" start={start} duration={20} length={500} />
          {Array.from({ length: 7 }, (_, i) => {
            const y = 40 + ((i * 16 + t * 6) % 110);
            return t > 10 ? <rect key={i} x={74} y={y} width={84 - (i % 3) * 18} height={5} rx={2} fill={C.mint} opacity={0.7} /> : null;
          })}
        </>
      )}
      {kind === 1 && (
        <>
          {/* dos robots ante un espejo: el mismo punto ciego */}
          <Draw d="M110 0 V160" start={start} duration={16} length={170} color={C.cyan} width={3} />
          <Draw d="M20 50 h64 v56 h-64 Z M52 50 V30 M52 24 a5 5 0 1 0 0.1 0 M38 92 h28" start={start + 6} duration={18} length={360} />
          <Draw d="M136 50 h64 v56 h-64 Z M168 50 V30 M168 24 a5 5 0 1 0 0.1 0 M154 92 h28" start={start + 6} duration={18} length={360} />
          {t > 24 && <circle cx={64} cy={72} r={9} fill={C.red} opacity={0.9} />}{t > 20 && <circle cx={40} cy={72} r={5} fill={C.mint} />}
          {t > 30 && <circle cx={156} cy={72} r={9} fill={C.red} opacity={0.9} />}{t > 20 && <circle cx={180} cy={72} r={5} fill={C.mint} />}
          {t > 36 && <text x={110} y={152} textAnchor="middle" fill={C.red} style={{ font: `600 16px ${FONT.mono}` }}>same blind spot</text>}
        </>
      )}
      {kind === 2 && (
        <>
          {/* velocímetro clavado en el 98 % */}
          <Draw d="M20 140 A90 90 0 0 1 200 140" start={start} duration={20} length={300} color={C.cyan} width={6} />
          {(() => {
            const angle = lerp(t, [10, 34], [-180, -180 + 0.98 * 180]) + Math.sin(t / 2) * (t > 34 ? 1.2 : 0);
            const rad = (angle * Math.PI) / 180;
            return t > 8 ? <line x1={110} y1={140} x2={110 + 78 * Math.cos(rad)} y2={140 + 78 * Math.sin(rad)} stroke={C.mint} strokeWidth={6} strokeLinecap="round" /> : null;
          })()}
          {t > 30 && <text x={110} y={120} textAnchor="middle" fill={C.fg} style={{ font: `800 30px ${FONT.mono}` }}>98%</text>}
          {t > 40 && <Draw d="M150 30 L130 70 L150 80 L125 125" start={start + 40} duration={10} length={140} color={C.red} width={5} />}
        </>
      )}
      {kind === 3 && (
        <>
          {/* una firma que se queda en interrogación */}
          <Draw d="M10 130 H210" start={start} duration={14} length={210} color={C.fg2} width={3} glowOn={false} />
          <Draw d="M40 110 C60 60 80 140 100 90 S130 70 140 100" start={start + 10} duration={22} length={260} color={C.cyan} width={4} />
          {t > 34 && <text x={175} y={115} textAnchor="middle" fill={C.amber} style={{ font: `800 70px ${FONT.serif}` }}>?</text>}
        </>
      )}
    </svg>
  );
}

// En el orden de la voz. Un solo estilo de icono: el pictograma animado (sin emoji).
const PROBLEMS = [
  { kind: 0, title: "Too much to read", sub: `Nobody reads ${data.files} files.` },
  { kind: 2, title: "Confident isn't correct", sub: "It sounds just as sure when it is wrong." },
  { kind: 1, title: "AI grading AI", sub: "Same model, same blind spots." },
  { kind: 3, title: "Who owns the merge?", sub: "“The AI said it was fine” is not an owner." },
];

/** Escena 2 · Los problemas: cada uno entra cuando la voz lo nombra, con su pictograma dibujándose. */
export function S2Problems() {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill>
      <Backdrop spot={{ x: 30, y: 40 }} />
      {PROBLEMS.map((p, i) => {
        const start = at("problems", i) - 4;
        if (frame < start) return null;
        const current = PROBLEMS.reduce((acc, _, k) => (frame >= at("problems", k) - 4 ? k : acc), 0);
        const active = i === current;
        return (
          <div key={p.title} style={{ position: "absolute", left: 170, top: 90 + i * 200, display: "flex", alignItems: "center", gap: 44, opacity: active ? 1 : 0.45, transition: "none" }}>
            <div style={{ width: 230 }}>
              <Pictogram kind={p.kind} start={start} />
            </div>
            <div>
              <Words text={p.title} start={start} size={72} align="left" every={2} />
              <div style={{ font: `500 32px ${FONT.sans}`, color: C.fg2, opacity: lerp(frame, [start + 8, start + 18], [0, 1]), marginTop: 4 }}>{p.sub}</div>
            </div>
          </div>
        );
      })}
    </AbsoluteFill>
  );
}
