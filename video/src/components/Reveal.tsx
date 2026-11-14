import React from "react";
import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";
import { C } from "../theme";

export type RevealKind = "blinds" | "iris" | "zoom" | "diagonal" | "shutter" | "rise";

const SLICES = 8;
// Radio de referencia de circle(100%) en CSS: hipotenusa / √2 del lienzo 1920×1080.
const IRIS_REF = Math.hypot(1920, 1080) / Math.SQRT2;

function staircaseVertical(p: number, fromBottom: boolean): string {
  // Persianas verticales: cada tira baja (o sube) con un pequeño retraso respecto a la anterior.
  const pts: string[] = [];
  const heights = Array.from({ length: SLICES }, (_, i) => Math.max(0, Math.min(1, p * 1.6 - i * 0.6 / SLICES)) * 100);
  if (!fromBottom) {
    pts.push("0% 0%", "100% 0%");
    for (let i = SLICES - 1; i >= 0; i--) pts.push(`${((i + 1) / SLICES) * 100}% ${heights[i]}%`, `${(i / SLICES) * 100}% ${heights[i]}%`);
  } else {
    pts.push("0% 100%", "100% 100%");
    for (let i = SLICES - 1; i >= 0; i--) pts.push(`${((i + 1) / SLICES) * 100}% ${100 - heights[i]}%`, `${(i / SLICES) * 100}% ${100 - heights[i]}%`);
  }
  return `polygon(${pts.join(", ")})`;
}

function staircaseHorizontal(p: number): string {
  // Cortinas horizontales: cada franja entra desde la izquierda, escalonada.
  const bars = 6;
  const pts: string[] = ["0% 0%"];
  for (let i = 0; i < bars; i++) {
    const w = Math.max(0, Math.min(1, p * 1.5 - i * 0.5 / bars)) * 100;
    pts.push(`${w}% ${(i / bars) * 100}%`, `${w}% ${((i + 1) / bars) * 100}%`);
  }
  pts.push("0% 100%");
  return `polygon(${pts.join(", ")})`;
}

/**
 * Transición de ENTRADA de una escena sobre la anterior (las escenas se solapan `duration` frames en Demo.tsx).
 * Cada corte usa una forma distinta; nunca un simple fundido.
 */
export function Reveal({ kind, duration, origin = { x: 50, y: 50 }, children }: {
  kind: RevealKind; duration: number; origin?: { x: number; y: number }; children: React.ReactNode;
}) {
  const frame = useCurrentFrame();
  const p = interpolate(frame, [0, duration], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.inOut(Easing.cubic) });
  if (p >= 1) return <AbsoluteFill>{children}</AbsoluteFill>;

  let clipPath = "none";
  let transform = "none";
  let edge: React.ReactNode = null;
  switch (kind) {
    case "blinds":
      clipPath = staircaseVertical(p, false);
      break;
    case "rise":
      clipPath = staircaseVertical(p, true);
      break;
    case "shutter":
      clipPath = staircaseHorizontal(p);
      break;
    case "iris":
      clipPath = `circle(${p * 125}% at ${origin.x}% ${origin.y}%)`;
      edge = (
        <div style={{ position: "absolute", left: `${origin.x}%`, top: `${origin.y}%`, width: p * 2.5 * IRIS_REF, height: p * 2.5 * IRIS_REF, transform: "translate(-50%, -50%)", borderRadius: "50%", border: `4px solid ${C.mint}`, boxShadow: `0 0 30px ${C.mint}`, opacity: 1 - p }} />
      );
      break;
    case "zoom":
      clipPath = `circle(${p * 125}% at ${origin.x}% ${origin.y}%)`;
      transform = `scale(${1.6 - 0.6 * p})`;
      break;
    case "diagonal": {
      // Barrido diagonal con un filo de luz.
      const x = -40 + p * 180; // % del ancho
      clipPath = `polygon(0% 0%, ${x}% 0%, ${x - 40}% 100%, 0% 100%)`;
      edge = (
        <div style={{ position: "absolute", left: `${x - 20}%`, top: "-10%", width: 6, height: "120%", background: C.mint, boxShadow: `0 0 30px ${C.mint}, 0 0 60px ${C.cyan}`, transform: "rotate(21.8deg)", transformOrigin: "center" }} />
      );
      break;
    }
  }
  return (
    <AbsoluteFill>
      <AbsoluteFill style={{ clipPath, transform, transformOrigin: `${origin.x}% ${origin.y}%` }}>{children}</AbsoluteFill>
      {edge}
    </AbsoluteFill>
  );
}
