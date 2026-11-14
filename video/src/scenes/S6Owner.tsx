import React from "react";
import { AbsoluteFill, random, useCurrentFrame } from "remotion";
import { lerp, pop } from "../anim";
import { Character } from "../components/Character";
import { ReqTag, Tower } from "../components/Props";
import { Backdrop, Eyebrow, Words } from "../components/Stage";
import { at } from "../cues";
import data from "../data/video-data.json";
import { C, FONT, glow } from "../theme";

const TOWER_X = 1030;
const DESK_Y = 820;
const counts = data.verdictCounts as Record<string, number>;
const NON_GREEN = (counts.RED ?? 0) + (counts.YELLOW ?? 0);

/** Escena 6 · La mesa de Alex: la misma torre se encoge, lo aprobado por la evidencia se va y caen 12 tarjetas. */
export function S6Owner() {
  const frame = useCurrentFrame();
  const shrinkAt = at("owner", 0) + 6;
  const refusedAt = at("owner", 1) - 4;
  const squash = lerp(frame, [shrinkAt, shrinkAt + 30], [0, 1]);
  const towerFade = lerp(frame, [shrinkAt + 20, shrinkAt + 44], [0, 1]);
  const cardsDrop = lerp(frame, [shrinkAt + 10, shrinkAt + 48], [0, 1]);
  const zoom = pop(frame, refusedAt);
  const dim = lerp(frame, [refusedAt, refusedAt + 12], [0, 0.55]);
  const n = Math.round(lerp(frame, [shrinkAt + 10, shrinkAt + 48], [data.files, data.needHuman]));

  return (
    <AbsoluteFill>
      <Backdrop spot={{ x: 55, y: 55 }} />
      <Character kind="human" x={360} y={560} scale={1.25} label="Alex — owner" calm={frame > shrinkAt + 40} />
      {/* la mesa */}
      <div style={{ position: "absolute", left: 560, top: DESK_Y, width: 1260, height: 18, borderRadius: 9, background: `linear-gradient(90deg, ${C.cyan}, ${C.mint})`, boxShadow: glow(C.mint, 0.6) }} />
      <Tower x={TOWER_X} base={DESK_Y - 4} sheets={data.files} squash={squash} fade={towerFade} />
      {/* las 225 aprobadas se disuelven hacia arriba como puntos */}
      {Array.from({ length: 60 }, (_, i) => {
        const t = lerp(frame, [shrinkAt + 14 + (i % 10), shrinkAt + 50 + (i % 10)], [0, 1]);
        if (t <= 0 || t >= 1) return null;
        return <div key={i} style={{ position: "absolute", left: TOWER_X - 150 + random(`ox${i}`) * 300, top: DESK_Y - 60 - t * 520 - random(`oy${i}`) * 200, width: 8, height: 8, borderRadius: 4, background: C.mint, opacity: 1 - t }} />;
      })}
      {/* las 12 tarjetas que caen sobre la mesa */}
      {Array.from({ length: NON_GREEN }, (_, k) => {
        const color = k === 5 ? C.amber : C.red;
        const tx = 720 + k * 88, ty = DESK_Y - 112 + (k % 2) * 6;
        const sx = TOWER_X - 40 + (k % 4) * 20, sy = 300 + (k % 3) * 40;
        const d = Math.min(1, Math.max(0, cardsDrop * 1.4 - k * 0.03));
        const rot = (1 - d) * (k % 2 ? 30 : -30) + (k % 3 - 1) * 4;
        return <div key={k} style={{ position: "absolute", left: sx + (tx - sx) * d, top: sy + (ty - sy) * d * d, width: 72, height: 104, borderRadius: 8, background: `${color}26`, border: `3px solid ${color}`, boxShadow: glow(color, 0.5), transform: `rotate(${rot}deg)`, opacity: frame > shrinkAt + 10 ? 1 : 0 }} />;
      })}
      <div style={{ position: "absolute", left: 1260, top: 150, opacity: lerp(frame, [shrinkAt + 10, shrinkAt + 24], [0, 1]) }}>
        <div style={{ font: `800 200px/0.9 ${FONT.mono}`, color: C.fg, textShadow: glow(C.cyan, 0.7) }}>{n}</div>
        <div style={{ font: `700 34px ${FONT.sans}`, color: C.fg }}>of {data.files} files need your eyes</div>
        <div style={{ font: `500 24px ${FONT.sans}`, color: C.fg2, marginTop: 6 }}>{counts.GREEN} approved by executable evidence, unread</div>
      </div>

      {/* una tarjeta se acerca: se niega a decidir y dice exactamente qué leer */}
      <AbsoluteFill style={{ background: "#000", opacity: dim }} />
      {frame >= refusedAt && (
        <div style={{ position: "absolute", left: 960, top: 470, width: 1100, transform: `translate(-50%, -50%) scale(${0.5 + 0.5 * zoom}) rotate(${(1 - zoom) * -8}deg)`, opacity: zoom, padding: "40px 52px", borderRadius: 24, background: C.panel, border: `4px solid ${C.red}`, boxShadow: `${glow(C.red, 1)}, 0 40px 80px rgba(0,0,0,.6)` }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <div style={{ padding: "8px 22px", border: `4px solid ${C.red}`, borderRadius: 10, color: C.red, font: `800 34px ${FONT.sans}`, letterSpacing: 3, transform: "rotate(-3deg)" }}>REFUSED TO DECIDE</div>
            <ReqTag style={{ position: "relative" }} />
          </div>
          <div style={{ font: `700 32px ${FONT.mono}`, color: C.fg, marginTop: 26 }}>{data.refusedFile}</div>
          <Eyebrow color={C.fg2} style={{ marginTop: 18 }}>open objection</Eyebrow>
          <div style={{ font: `500 30px/1.4 ${FONT.sans}`, color: C.fg, marginTop: 6 }}>“{data.refusedQuestion}”</div>
          <div style={{ font: `700 28px ${FONT.sans}`, color: C.red, marginTop: 18 }}>{data.refusedRedTests} Defender tests fail on the PR → possible defect</div>
          <div style={{ marginTop: 22 }}>
            <Words text="Read this file. The rest is backed by evidence." start={refusedAt + 30} every={2} size={36} weight={800} color={C.mint} align="left" />
          </div>
        </div>
      )}
    </AbsoluteFill>
  );
}
