import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { lerp, pop } from "../anim";
import { Backdrop, Draw, Eyebrow, Words } from "../components/Stage";
import { at } from "../cues";
import { C, FONT, glow } from "../theme";

// Contexto del enunciado del reto: los tokens de agentes superaron a los humanos en febrero de 2026 y llegaron a
// 7,3 billones (trillion) en agosto (OpenRouter, gráfico de a16z). Curvas esquemáticas: solo se rotulan esos dos hechos.
const X0 = 260, X1 = 1500, BASE = 700;
const CROSS = { x: 1010, y: 500 };
const PEAK = { x: X1, y: 190 };
const HUMANS = `M${X0} 580 C 560 560, 820 525, ${CROSS.x} ${CROSS.y} S 1340 460, ${X1} 445`;
const AGENTS = `M${X0} 680 C 640 675, 860 630, ${CROSS.x} ${CROSS.y} S 1380 270, ${PEAK.x} ${PEAK.y}`;

/** Escena 0 · Introducción: los agentes ya escriben más que las personas; ¿quién revisa todo ese código? */
export function S0Intro() {
  const frame = useCurrentFrame();
  const q = at("intro", 1);
  // Entrada: primero solo el fondo; después la gráfica entra con un barrido de luz y las curvas se dibujan.
  const reveal = lerp(frame, [10, 32], [0, 100]);
  const drawStart = 12;
  const cross = 52;
  const trillions = lerp(frame, [28, 82], [0, 7.3]);
  const chartOut = lerp(frame, [q - 10, q + 6], [1, 0]);
  const ring = pop(frame, cross);

  return (
    <AbsoluteFill>
      <AbsoluteFill style={{ opacity: lerp(frame, [0, 14], [0.35, 1]) }}>
        <Backdrop drift={0.6} />
      </AbsoluteFill>
      {reveal > 0 && reveal < 100 && <div style={{ position: "absolute", left: `${reveal}%`, top: 0, width: 4, height: "100%", background: C.mint, boxShadow: glow(C.mint, 1.4), opacity: 0.8 }} />}
      <AbsoluteFill style={{ opacity: chartOut, transform: `scale(${1 + 0.06 * (1 - chartOut)})`, clipPath: `inset(0 ${100 - reveal}% 0 0)` }}>
        <svg style={{ position: "absolute", left: 0, top: 0 }} width={1920} height={1080}>
          <line x1={X0} y1={BASE} x2={X1 + 60} y2={BASE} stroke={C.line} strokeWidth={2} />
          <Draw d={HUMANS} start={drawStart} duration={70} length={1400} color={C.cyan} width={6} />
          <Draw d={AGENTS} start={drawStart} duration={80} length={1600} color={C.mint} width={8} />
          {frame >= cross && <circle cx={CROSS.x} cy={CROSS.y} r={14 + 40 * (1 - ring)} fill="none" stroke={C.fg} strokeWidth={3} opacity={ring} />}
        </svg>
        <div style={{ position: "absolute", left: X1 + 30, top: 428, font: `700 26px ${FONT.sans}`, color: C.cyan }}>humans</div>
        <div style={{ position: "absolute", left: X1 - 40, top: 60, opacity: lerp(frame, [28, 40], [0, 1]), textAlign: "right", transform: "translateX(-100%)" }}>
          <div style={{ font: `800 112px/1 ${FONT.mono}`, color: C.mint, textShadow: glow(C.mint, 0.8) }}>{trillions.toFixed(1)}T</div>
          <div style={{ font: `700 28px ${FONT.sans}`, color: C.fg }}>AI agent tokens · August 2026</div>
        </div>
        {frame >= cross && (
          <div style={{ position: "absolute", left: CROSS.x + 30, top: CROSS.y + 20, opacity: ring }}>
            <Eyebrow color={C.fg}>February 2026</Eyebrow>
            <div style={{ font: `600 26px ${FONT.sans}`, color: C.fg2 }}>agents pass humans</div>
          </div>
        )}
        <div style={{ position: "absolute", left: X0, top: BASE + 22, font: `500 20px ${FONT.mono}`, color: C.fg2 }}>Source: OpenRouter data, via a16z</div>
      </AbsoluteFill>
      {frame >= q - 4 && (
        <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", paddingBottom: 80 }}>
          <Words text="So who reviews all that code?" start={q - 4} every={4} size={104} font={FONT.serif} weight={700} highlight={{ 1: C.mint, 2: C.mint }} />
        </AbsoluteFill>
      )}
    </AbsoluteFill>
  );
}
