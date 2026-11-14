import React from "react";
import { AbsoluteFill, random, useCurrentFrame } from "remotion";
import { lerp, pop } from "../anim";
import { Character } from "../components/Character";
import { Hologram, SHEET_H, Tower } from "../components/Props";
import { Backdrop } from "../components/Stage";
import { at } from "../cues";
import data from "../data/video-data.json";
import { C, FONT, glow } from "../theme";
import { SCENES, TRANSITION } from "../timeline";

const D = SCENES.friday.duration + TRANSITION;
export const TOWER_X = 1030;
export const TOWER_BASE = 940;

/** Escena 1 · La torre: el Agente apila 237 hojas que dejan diminuto al humano; el revisor la barre en un segundo. */
export function S1Friday() {
  const frame = useCurrentFrame();
  const says237 = at("friday", 0) + 40; // la voz dice "237" hacia la mitad de la primera frase
  const scanAt = at("friday", 1);
  const sheets = Math.round(lerp(frame, [0, says237], [24, data.files]));
  const towerTop = TOWER_BASE - sheets * SHEET_H;
  const scanY = lerp(frame, [scanAt, scanAt + 22], [TOWER_BASE - data.files * SHEET_H - 20, TOWER_BASE + 10]);
  const scanning = frame >= scanAt && frame <= scanAt + 24;
  const holo = pop(frame, scanAt + 24);
  // Ken Burns muy suave y centrado: nada se sale del encuadre (ni el holograma ni el revisor).
  const drift = lerp(frame, [0, D], [1, 1.025]);

  const particles = Array.from({ length: 30 }, (_, i) => {
    const t = ((frame * 1.8 + i * 23) % 60) / 60;
    const sx = 330, sy = 600;
    const tx = TOWER_X + (random(`px${i}`) - 0.5) * 120, ty = towerTop - 10;
    const cx = (sx + tx) / 2, cy = Math.min(sy, ty) - 220;
    return {
      i,
      x: (1 - t) * (1 - t) * sx + 2 * (1 - t) * t * cx + t * t * tx,
      y: (1 - t) * (1 - t) * sy + 2 * (1 - t) * t * cy + t * t * ty,
      o: frame < says237 ? Math.sin(t * Math.PI) : 0,
    };
  });

  return (
    <AbsoluteFill>
      <Backdrop spot={{ x: 52, y: 50 }} />
      <AbsoluteFill style={{ transform: `scale(${drift})`, transformOrigin: "50% 50%" }}>
        <Character kind="robot" x={250} y={640} scale={1.3} talking={frame < says237} label="AI agent" />
        {particles.map((p) => (
          <div key={p.i} style={{ position: "absolute", left: p.x, top: p.y, width: 16, height: 6, borderRadius: 2, background: p.i % 3 ? C.mint : C.cyan, opacity: p.o, boxShadow: glow(C.mint, 0.5) }} />
        ))}
        <Tower x={TOWER_X} base={TOWER_BASE} sheets={sheets} />
        {scanning && <div style={{ position: "absolute", left: TOWER_X - 240, top: scanY, width: 480, height: 9, background: C.mint, boxShadow: glow(C.mint, 1.4) }} />}
        <div style={{ position: "absolute", left: TOWER_X + 200, top: Math.max(120, towerTop - 20), font: `800 120px/1 ${FONT.mono}`, color: C.fg, textShadow: glow(C.cyan, 0.6) }}>
          {sheets}
          <div style={{ font: `700 30px ${FONT.sans}`, color: C.fg2, letterSpacing: 3 }}>FILES CHANGED</div>
        </div>

        <Character kind="human" x={640} y={660} scale={1.2} label="Alex — owner" calm={false} />
        <div style={{ position: "absolute", left: 640, top: 880, transform: "translateX(-50%)", padding: "12px 40px", borderRadius: 999, border: `3px solid ${C.mint}`, color: C.mint, font: `800 34px ${FONT.sans}`, letterSpacing: 2, boxShadow: glow(C.mint, 0.5) }}>
          APPROVE
        </div>

        <Character kind="robot" x={1690} y={680} scale={1.3} mirrored label="AI reviewer" talking={frame > scanAt && frame < scanAt + 70} />
        {frame >= scanAt + 24 && <Hologram x={1710} y={300} shown={holo} frame={frame} note="illustrative example" />}
      </AbsoluteFill>
    </AbsoluteFill>
  );
}
