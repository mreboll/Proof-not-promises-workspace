import React from "react";
import { AbsoluteFill, random, useCurrentFrame } from "remotion";
import { lerp, pop } from "../anim";
import { Character } from "../components/Character";
import { ReqTag } from "../components/Props";
import { Backdrop, Draw, Eyebrow, Words } from "../components/Stage";
import { at } from "../cues";
import data from "../data/video-data.json";
import { C, FONT, glow } from "../theme";

const counts = data.verdictCounts as Record<string, number>;
const CHECK = "M0 22 L16 38 L46 4";
const COLS = 15;

/** 9a · La muestra: un hash recorre los ficheros verdes y elige los que una persona leerá enteros. */
function Sample({ frame }: { frame: number }) {
  const greens = counts.GREEN ?? 0;
  // Posiciones (deterministas) de los elegidos dentro de la cuadrícula de verdes.
  const picked = data.spotCheckFiles.map((_, k) => Math.floor(random(`pick${k}`) * greens));
  const hash = Array.from({ length: 4 }, (_, k) => Math.floor(random(`h${Math.floor(frame / 2)}${k}`) * 0xffff).toString(16).padStart(4, "0")).join("");
  return (
    <>
      <Eyebrow color={C.mint} style={{ position: "absolute", left: 640, top: 130 }}>spot-checks · humans check the AI reviewer</Eyebrow>
      <div style={{ position: "absolute", left: 640, top: 175, font: `700 30px ${FONT.mono}`, color: C.cyan }}>sha256(issue, path) → {hash}…</div>
      {Array.from({ length: greens }, (_, i) => {
        const x = 640 + (i % COLS) * 34, y = 250 + Math.floor(i / COLS) * 34;
        const k = picked.indexOf(i);
        const chosen = k >= 0 && frame > 18 + k * 4;
        return <div key={i} style={{ position: "absolute", left: x, top: y, width: 22, height: 22, borderRadius: 6, background: chosen ? C.mint : `${C.mint}40`, boxShadow: chosen ? glow(C.mint, 1) : undefined, transform: chosen ? `scale(${1 + 0.4 * pop(frame, 18 + k * 4)})` : undefined }} />;
      })}
      <div style={{ position: "absolute", left: 1200, top: 250, width: 640 }}>
        {data.spotCheckFiles.map((f, k) => (
          <div key={`${f}-${k}`} style={{ font: `600 22px ${FONT.mono}`, color: C.fg, marginBottom: 14, opacity: pop(frame, 20 + k * 4), whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
            <span style={{ color: C.mint }}>▸ </span>{f}
          </div>
        ))}
        <div style={{ font: `600 26px ${FONT.sans}`, color: C.fg2, marginTop: 18, opacity: lerp(frame, [44, 56], [0, 1]) }}>
          {data.spotCheckFiles.length} green files, picked by hash, not by the AI. Read in full before signing.
        </div>
      </div>
    </>
  );
}

/** 9b · La firma: tres compromisos que se marcan a mano, la etiqueta del requisito y un nombre que se escribe. */
function Signature({ frame }: { frame: number }) {
  const items = ["What was checked, and by what", "What was NOT checked, and why", "Residual risk I accept"];
  const nameReveal = lerp(frame, [14, 52], [0, 100]); // la firma se escribe ~1,3 s: es el clímax
  return (
    <>
      <div style={{ position: "absolute", left: 640, top: 130, display: "flex", gap: 20, alignItems: "center" }}>
        <Eyebrow color={C.mint}>approval and accountability record</Eyebrow>
        <ReqTag style={{ position: "relative" }} />
      </div>
      {items.map((t, i) => (
        <div key={t} style={{ position: "absolute", left: 640, top: 200 + i * 92, display: "flex", alignItems: "center", gap: 26 }}>
          <svg width={56} height={46} style={{ overflow: "visible" }}>
            <Draw d={CHECK} start={4 + i * 6} duration={10} length={70} color={C.mint} width={7} />
          </svg>
          <Words text={t} start={i * 6} every={2} size={48} font={FONT.serif} weight={700} align="left" />
        </div>
      ))}
      <div style={{ position: "absolute", left: 640, top: 500, width: 760 }}>
        <div style={{ font: `600 110px/1 ${FONT.hand}`, color: C.cyan, clipPath: `inset(0 ${100 - nameReveal}% 0 0)`, textShadow: glow(C.cyan, 0.5) }}>Alex Kim</div>
        <div style={{ height: 3, background: C.fg2, marginTop: 4 }} />
        <Eyebrow style={{ marginTop: 8 }}>signed by · named owner (example)</Eyebrow>
      </div>
      <div style={{ position: "absolute", left: 640, top: 740, display: "flex", gap: 20, alignItems: "center", opacity: lerp(frame, [54, 66], [0, 1]) }}>
        {["APPROVED", "REJECTED"].map((d) => (
          <div key={d} style={{ padding: "10px 28px", borderRadius: 999, border: `3px solid ${C.line}`, font: `800 26px ${FONT.sans}`, color: C.fg2, letterSpacing: 2 }}>☐ {d}</div>
        ))}
        <div style={{ font: `500 26px ${FONT.sans}`, color: C.fg2 }}>the decision stays human</div>
      </div>
    </>
  );
}

/** Escena 9 · Muestra de spot-checks y firma. */
export function S9Sign() {
  const frame = useCurrentFrame();
  const signAt = at("sign", 1) - 6;
  const sampleStart = at("sign", 0) - 6;
  const part = frame < signAt ? 0 : 1;
  const wipe = part === 1 ? lerp(frame - signAt, [0, 12], [0, 100]) : 100;
  return (
    <AbsoluteFill>
      <Backdrop spot={{ x: 55, y: 45 }} />
      <Character kind="human" x={330} y={560} scale={1.2} label="Alex — owner" calm />
      <AbsoluteFill style={{ clipPath: `inset(0 0 0 ${100 - wipe}%)` }}>
        {part === 0 ? <Sample frame={frame - sampleStart} /> : <Signature frame={frame - signAt} />}
      </AbsoluteFill>
    </AbsoluteFill>
  );
}
