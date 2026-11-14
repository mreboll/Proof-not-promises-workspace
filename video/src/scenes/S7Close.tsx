import React from "react";
import { AbsoluteFill, random, useCurrentFrame } from "remotion";
import { lerp, pop } from "../anim";
import { Backdrop, Words } from "../components/Stage";
import { at } from "../cues";
import data from "../data/video-data.json";
import { C, FONT, glow } from "../theme";

/** Cierre: el lema desde el primer fotograma; con "Proof, not promises" el título ocupa el centro y el vídeo acaba en él. */
export function S7Close() {
  const frame = useCurrentFrame();
  const titleAt = at("close", 1) - 4;
  const converge = lerp(frame, [0, 24], [0.35, 1]);
  const line = lerp(frame, [18, 32], [0, 1]);
  const lift = lerp(frame, [titleAt - 6, titleAt + 10], [0, 1]);
  const title = pop(frame, titleAt);
  return (
    <AbsoluteFill>
      <Backdrop drift={0.2} />
      {Array.from({ length: data.files }, (_, i) => {
        const sx = random(`cx${i}`) * 1920, sy = random(`cy${i}`) * 1080;
        const tx = 360 + (i / (data.files - 1)) * 1200, ty = 470 - 230 * lift;
        return <div key={i} style={{ position: "absolute", left: sx + (tx - sx) * converge, top: sy + (ty - sy) * converge, width: 8, height: 8, borderRadius: 4, background: i % 2 ? C.mint : C.cyan, opacity: 1 - line * 0.9 }} />;
      })}
      <div style={{ position: "absolute", left: 360, top: 472 - 230 * lift, width: 1200 * line, height: 4, background: `linear-gradient(90deg, ${C.mint}, ${C.cyan})`, boxShadow: glow(C.mint, 1) }} />
      <div style={{ position: "absolute", left: 0, right: 0, top: 330 - 230 * lift, transform: `scale(${1 - 0.35 * lift})` }}>
        <Words text="AI reviews. Humans stay accountable." start={-14} every={4} size={86} font={FONT.serif} weight={700} highlight={{ 0: C.mint, 1: C.mint, 2: C.cyan, 3: C.cyan, 4: C.cyan }} />
      </div>
      {frame >= titleAt && (
        <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", paddingTop: 40 }}>
          <div style={{ transform: `scale(${0.85 + 0.15 * title})`, opacity: title }}>
            <Words text="Proof, not promises" start={titleAt} every={4} size={150} font={FONT.serif} weight={700} highlight={{ 2: C.mint }} />
          </div>
          <div style={{ marginTop: 26, font: `500 24px ${FONT.sans}`, color: C.fg2, letterSpacing: 1, opacity: lerp(frame, [titleAt + 14, titleAt + 26], [0, 1]) }}>
            {data.team.join("  ·  ")}
          </div>
          <div style={{ marginTop: 8, font: `500 20px ${FONT.sans}`, color: C.fg2, letterSpacing: 2, opacity: lerp(frame, [titleAt + 18, titleAt + 30], [0, 0.8]) }}>
            Junction 2026 · Tieto — Earned Trust in AI Code
          </div>
        </AbsoluteFill>
      )}
    </AbsoluteFill>
  );
}
