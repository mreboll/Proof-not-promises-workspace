import React from "react";
import { random } from "remotion";
import { C, FONT, glow } from "../theme";
import { Eyebrow } from "./Stage";

export const SHEET_H = 3.1;

/** Torre de ficheros en perspectiva (escena 1) — la misma que luego se encoge sobre la mesa de Alex. */
export function Tower({ x, base, sheets, squash = 0, fade = 0 }: { x: number; base: number; sheets: number; squash?: number; fade?: number }) {
  const h = SHEET_H * (1 - squash * 0.85);
  return (
    <svg style={{ position: "absolute", left: 0, top: 0, opacity: 1 - fade }} width={1920} height={1080}>
      {Array.from({ length: sheets }, (_, i) => {
        const y = base - i * h;
        const j = (random(`s${i}`) - 0.5) * 10;
        return (
          <polygon
            key={i}
            points={`${x - 150 + j},${y} ${x + 130 + j},${y} ${x + 162 + j},${y - 15} ${x - 118 + j},${y - 15}`}
            fill={i % 2 ? "#14495a" : "#1b5a6d"}
            stroke={C.mint}
            strokeOpacity={0.25}
            strokeWidth={0.6}
          />
        );
      })}
    </svg>
  );
}

/** Holograma "LGTM 98 %": la confianza autodeclarada. `broken` (0→1) lo agrieta y lo vuelve rojo. */
export function Hologram({ x, y, scale = 1, shown, broken = 0, frame, note }: { x: number; y: number; scale?: number; shown: number; broken?: number; frame: number; note?: string }) {
  const color = broken > 0.5 ? C.red : C.mint;
  const flicker = broken > 0 ? 0.75 + 0.25 * Math.sin(frame * 1.7) : 0.88 + 0.12 * Math.sin(frame / 3);
  return (
    <div style={{ position: "absolute", left: x, top: y, transform: `translate(-50%, -50%) scale(${(0.6 + 0.4 * shown) * scale}) perspective(700px) rotateY(-16deg) rotate(${broken * -6}deg)`, opacity: shown * flicker, textAlign: "center", padding: "20px 36px", border: `3px solid ${color}`, borderRadius: 20, background: `${color}14`, boxShadow: glow(color, 1) }}>
      <Eyebrow color={color}>review complete</Eyebrow>
      <div style={{ font: `800 72px ${FONT.sans}`, color, textShadow: glow(color, 0.8) }}>LGTM ✓</div>
      <div style={{ font: `600 34px ${FONT.mono}`, color: C.fg, textDecoration: broken > 0.6 ? "line-through" : undefined, textDecorationColor: C.red, textDecorationThickness: 4 }}>98% confident</div>
      {note && <div style={{ font: `500 18px ${FONT.sans}`, color: C.fg2, marginTop: 8, letterSpacing: 1, whiteSpace: "nowrap" }}>{note}</div>}
      {broken > 0 && (
        <svg style={{ position: "absolute", inset: 0, overflow: "visible" }} width="100%" height="100%">
          <path d="M40 10 L120 90 L95 130 L170 210 M120 90 L210 70 L260 140 M95 130 L30 180" stroke={C.red} strokeWidth={4} fill="none" strokeDasharray={600} strokeDashoffset={600 * (1 - Math.min(1, broken * 1.6))} style={{ filter: `drop-shadow(0 0 6px ${C.red})` }} />
        </svg>
      )}
    </div>
  );
}

/** Etiqueta de trazabilidad al requisito (el reto: "evidence is traceable to a requirement"). */
export function ReqTag({ style }: { style?: React.CSSProperties }) {
  return (
    <div style={{ position: "absolute", display: "inline-flex", alignItems: "center", gap: 8, padding: "6px 14px", borderRadius: 8, border: `2px solid ${C.cyan}`, color: C.cyan, font: `700 20px ${FONT.mono}`, letterSpacing: 1, ...style }}>
      REQ · issue #2297
    </div>
  );
}
