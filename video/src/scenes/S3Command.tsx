import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { lerp, pop } from "../anim";
import { Terminal } from "../components/Code";
import { ReqTag } from "../components/Props";
import { Backdrop, Draw, Eyebrow, Words } from "../components/Stage";
import { at } from "../cues";
import { C, FONT, glow } from "../theme";

const COMMAND = "LEDGER_RUNNER=modal python -m ledger run --issue 2297";

export const FUNNEL = [
  { tag: "T1", name: "Triage", note: "static rules + scope" },
  { tag: "T2", name: "Evidence", note: "tests, not opinions" },
  { tag: "T3", name: "Cross-examination", note: "Prosecutor vs Defender" },
];

// Geometría del embudo de neón (la reutiliza la escena 4 para el anillo T1).
export const RING = { cx: 860, top: 330, h: 110, gap: 22, w0: 980, shrink: 240 };

export function ringPath(i: number): string {
  const y = RING.top + i * (RING.h + RING.gap);
  const wTop = RING.w0 - i * RING.shrink;
  const wBot = wTop - RING.shrink + 40;
  const x1 = RING.cx - wTop / 2, x2 = RING.cx + wTop / 2, x3 = RING.cx + wBot / 2, x4 = RING.cx - wBot / 2;
  return `M${x1} ${y} L${x2} ${y} L${x3} ${y + RING.h} L${x4} ${y + RING.h} Z`;
}

/** Píldoras compactas del embudo (cabecera de las escenas 4 y 5). `active` resalta una etapa. */
export function FunnelStrip({ active = -1, y = 46 }: { active?: number; y?: number }) {
  return (
    <>
    <ReqTag style={{ left: 60, top: y + 4 }} />
    <div style={{ position: "absolute", top: y, left: 0, right: 0, display: "flex", justifyContent: "center", gap: 16 }}>
      {FUNNEL.map((s, i) => (
        <div key={s.tag} style={{ display: "flex", gap: 10, alignItems: "center", padding: "8px 20px", borderRadius: 999, border: `2px solid ${i === active ? C.mint : C.line}`, color: i === active ? C.mint : C.fg2, boxShadow: i === active ? glow(C.mint, 0.4) : undefined, font: `600 22px ${FONT.sans}` }}>
          <span style={{ font: `700 18px ${FONT.mono}` }}>{s.tag}</span>
          {s.name}
        </div>
      ))}
    </div>
    </>
  );
}

/** Escena 3 · El comando y la regla: el terminal dibuja el embudo y la regla central ocupa la pantalla. */
export function S3Command() {
  const frame = useCurrentFrame();
  const enter = 37;
  const collapseAt = 53;
  const rule = at("command", 1) - 6;
  const collapse = lerp(frame, [collapseAt, collapseAt + 10], [1, 0.012]);
  const terminalGone = frame > collapseAt + 16;
  const flash = lerp(frame, [enter, enter + 3, enter + 12], [0, 0.35, 0]);
  const funnelOut = lerp(frame, [rule - 4, rule + 8], [1, 0]);
  const poster = pop(frame, rule);

  return (
    <AbsoluteFill>
      <Backdrop />
      <AbsoluteFill style={{ opacity: funnelOut, transform: `scale(${1 - 0.1 * (1 - funnelOut)})` }}>
        <div style={{ position: "absolute", top: 70, width: "100%", textAlign: "center" }}>
          <Words text="Proof, not promises" start={0} every={3} size={76} font={FONT.serif} weight={700} highlight={{ 2: C.mint }} />
        </div>
        <ReqTag style={{ left: 120, top: 92 }} />
        {!terminalGone && (
          <div style={{ position: "absolute", inset: 0, transform: `scaleY(${collapse})`, transformOrigin: "50% 50%" }}>
            <Terminal command={COMMAND} start={2} x={960} y={560} w={1400} charsPerFrame={4} outputs={[{ at: enter + 2, text: "▶ running the evidence funnel…" }]} />
          </div>
        )}
        <svg style={{ position: "absolute", left: 0, top: 0 }} width={1920} height={1080}>
          {frame > collapseAt + 4 && (
            <g opacity={lerp(frame, [collapseAt + 30, collapseAt + 44], [1, 0])}>
              <Draw d={`M${RING.cx - 700} 560 L${RING.cx + 700} 560`} start={collapseAt + 4} duration={8} length={1400} color={C.mint} width={3} />
            </g>
          )}
          {FUNNEL.map((_, i) => (
            <Draw key={i} d={ringPath(i)} start={collapseAt + 14 + i * 10} duration={20} length={2800} color={i === 1 ? C.cyan : C.mint} width={4} fill={frame > collapseAt + 34 + i * 10 ? "rgba(34,211,180,.06)" : "none"} />
          ))}
        </svg>
        {FUNNEL.map((f, i) => {
          const y = RING.top + i * (RING.h + RING.gap) + RING.h / 2 - 34;
          const x = RING.cx + (RING.w0 - i * RING.shrink) / 2 + 40;
          return (
            <div key={f.tag} style={{ position: "absolute", left: x, top: y, opacity: lerp(frame, [collapseAt + 24 + i * 10, collapseAt + 34 + i * 10], [0, 1]) }}>
              <div style={{ font: `800 46px ${FONT.sans}`, color: C.fg }}>
                <span style={{ font: `700 30px ${FONT.mono}`, color: i === 1 ? C.cyan : C.mint, marginRight: 14 }}>{f.tag}</span>
                {f.name}
              </div>
              <div style={{ font: `500 24px ${FONT.mono}`, color: C.fg2 }}>{f.note}</div>
            </div>
          );
        })}
      </AbsoluteFill>
      <AbsoluteFill style={{ background: C.mint, opacity: flash }} />
      {frame >= rule && (
        <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", transform: `scale(${0.92 + 0.08 * poster})`, opacity: poster }}>
          <Eyebrow color={C.mint} style={{ marginBottom: 24 }}>the one rule</Eyebrow>
          <Words text="No model approves anything." start={rule} every={3} size={118} font={FONT.serif} weight={700} />
          <div style={{ height: 18 }} />
          <Words text="Only executable evidence counts." start={rule + 18} every={3} size={78} weight={800} color={C.mint} />
        </AbsoluteFill>
      )}
    </AbsoluteFill>
  );
}
