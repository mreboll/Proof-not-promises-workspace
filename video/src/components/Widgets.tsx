import React from "react";
import { useCurrentFrame } from "remotion";
import { pop } from "../anim";
import { C, FONT } from "../theme";

/** Sello que entra con rebote (LGTM, Approved, cancelled...). */
export function Stamp({ text, color, x, y, start, rotate = -8, size = 44 }: { text: string; color: string; x: number; y: number; start: number; rotate?: number; size?: number }) {
  const frame = useCurrentFrame();
  const s = pop(frame, start);
  if (frame < start) return null;
  return (
    <div
      style={{
        position: "absolute", left: x, top: y, transform: `translate(-50%, -50%) rotate(${rotate}deg) scale(${0.6 + 0.4 * s})`, opacity: s,
        border: `5px solid ${color}`, color, borderRadius: 14, padding: "8px 22px", font: `700 ${size}px ${FONT.sans}`, letterSpacing: 2,
        background: "rgba(255,253,249,.92)", whiteSpace: "nowrap",
      }}
    >
      {text}
    </div>
  );
}

/** Caja de Modal: ejecuta un test aislado y sin red; muestra ✅ o ❌ al terminar. */
export function Sandbox({ x, y, label, result, doneAt, w = 220 }: { x: number; y: number; label: string; result: "pass" | "fail" | null; doneAt: number; w?: number }) {
  const frame = useCurrentFrame();
  const done = result !== null && frame >= doneAt;
  const s = done ? pop(frame, doneAt) : 0;
  const color = !done ? C.modal : result === "pass" ? C.green : C.red;
  return (
    <div style={{ position: "absolute", left: x, top: y, transform: "translate(-50%, -50%)", width: w, height: w * 0.62, borderRadius: 16, border: `4px solid ${color}`, background: C.sheet, boxShadow: `0 8px 24px rgba(${C.shadow},.10)` }}>
      <div style={{ position: "absolute", top: 8, left: 12, font: `600 18px ${FONT.mono}`, color: C.ink2 }}>🔒 {label}</div>
      <div style={{ position: "absolute", bottom: 8, left: 12, font: `400 14px ${FONT.sans}`, color: C.modal }}>Modal · no network</div>
      <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", font: `700 ${w * 0.28}px ${FONT.sans}`, transform: `scale(${done ? s : 1})` }}>
        {done ? (result === "pass" ? "✅" : "❌") : <span style={{ fontSize: w * 0.14, color: C.ink2 }}>{".".repeat(1 + (Math.floor(frame / 8) % 3))}</span>}
      </div>
    </div>
  );
}

/** Tarjeta (problemas, objeciones, tests). */
export function Card({ children, x, y, w, start, color = C.ink, bg = C.sheet }: { children: React.ReactNode; x: number; y: number; w: number; start: number; color?: string; bg?: string }) {
  const frame = useCurrentFrame();
  if (frame < start) return null;
  const s = pop(frame, start);
  return (
    <div style={{ position: "absolute", left: x, top: y, width: w, transform: `translate(-50%, -50%) scale(${0.8 + 0.2 * s})`, opacity: s, background: bg, border: `3px solid ${color}`, borderRadius: 18, padding: "18px 22px", boxShadow: `0 10px 30px rgba(${C.shadow},.12)`, font: `600 30px ${FONT.sans}`, color: C.ink }}>
      {children}
    </div>
  );
}

/** Bocadillo de diálogo. */
export function Bubble({ text, x, y, w, start, crossedAt }: { text: string; x: number; y: number; w: number; start: number; crossedAt?: number }) {
  const frame = useCurrentFrame();
  if (frame < start) return null;
  const s = pop(frame, start);
  const crossed = crossedAt !== undefined && frame >= crossedAt;
  return (
    <div style={{ position: "absolute", left: x, top: y, width: w, transform: `translate(-50%, -100%) scale(${0.85 + 0.15 * s})`, opacity: crossed ? 0.45 : s, background: C.sheet, border: `3px solid ${C.ink}`, borderRadius: 22, padding: "16px 20px", font: `500 26px ${FONT.sans}`, color: C.ink, lineHeight: 1.3 }}>
      <span style={{ textDecoration: crossed ? "line-through" : undefined, textDecorationColor: C.red, textDecorationThickness: 4 }}>{text}</span>
    </div>
  );
}
