import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { lerp, pop } from "../anim";
import { Backdrop, Eyebrow, Words } from "../components/Stage";
import { at } from "../cues";
import { C, FONT, glow } from "../theme";

const BAR_X = 1020;
const BARS = Array.from({ length: 11 }, (_, i) => ({ y: 250 + i * 36, w: 220 + ((i * 97) % 240) }));

/** El crash se movió: en el minimapa de TypeCollector.cs el marcador salta de una línea a otra. */
function Minimap({ frame }: { frame: number }) {
  const fixed = frame > 10;
  const jump = lerp(frame, [18, 46], [0, 1]);
  const from = { x: BAR_X + BARS[3].w + 50, y: BARS[3].y + 8 };
  const to = { x: BAR_X + BARS[8].w + 50, y: BARS[8].y + 8 };
  const mx = from.x + (to.x - from.x) * jump;
  const my = from.y + (to.y - from.y) * jump - Math.sin(jump * Math.PI) * 150;
  const pulse = 1 + 0.15 * Math.sin(frame / 2.5);
  return (
    <>
      <div style={{ position: "absolute", left: BAR_X, top: 136, transform: "rotate(-2deg)", padding: "6px 18px", border: `4px solid ${C.red}`, borderRadius: 10, color: C.red, font: `800 24px ${FONT.sans}`, letterSpacing: 3, boxShadow: glow(C.red, 0.5) }}>REAL FINDING · #2283 · found by cross-examination</div>
      <Eyebrow style={{ position: "absolute", left: BAR_X, top: 214 }}>TypeCollector.cs · minimap</Eyebrow>
      {BARS.map((b, i) => (
        <div key={i} style={{ position: "absolute", left: BAR_X, top: b.y, width: b.w, height: 16, borderRadius: 8, background: i === 3 && fixed ? C.mint : C.line, boxShadow: i === 3 && fixed ? glow(C.mint, 0.5) : undefined }} />
      ))}
      {fixed && <div style={{ position: "absolute", left: BAR_X - 130, top: BARS[3].y - 6, font: `700 22px ${FONT.mono}`, color: C.mint }}>AI fix ▶</div>}
      <div style={{ position: "absolute", left: mx, top: my, transform: `translate(-50%, -50%) scale(${pulse})`, font: `800 60px ${FONT.sans}`, textShadow: glow(C.red, 1) }}>💥</div>
      <div style={{ position: "absolute", left: from.x + 46, top: from.y - 20, font: `700 23px ${FONT.mono}`, color: jump > 0.2 ? C.fg2 : C.red, textDecoration: jump > 0.2 ? "line-through" : undefined }}>IndexOutOfRange <span style={{ font: `500 18px ${FONT.sans}`, color: C.fg2 }}>before</span></div>
      {jump >= 1 && (
        <div style={{ position: "absolute", left: to.x + 46, top: to.y - 20, opacity: pop(frame, 46), font: `700 23px ${FONT.mono}`, color: C.red }}>InvalidOperation <span style={{ font: `500 18px ${FONT.sans}`, color: C.fg2 }}>after · line 1013</span></div>
      )}
      {frame > 44 && (
        <div style={{ position: "absolute", left: BAR_X, top: 680, width: 820 }}>
          <Words text={"The AI fix didn't remove the crash. It moved it."} start={44} every={2} size={44} font={FONT.serif} weight={700} align="left" highlight={{ 7: C.red }} />
        </div>
      )}
    </>
  );
}

/** Parte A · Lo que vería una revisión rápida de #2283: la primera evidencia, toda en verde. */
const FIRST_EVIDENCE = ["Change test: red on base, green on PR", "Invariance: 21/21 general cases identical"];

/** Parte A · La primera evidencia sale verde; el contrainterrogatorio encuentra el crash desplazado. */
function FirstEvidence({ frame, crashAt, wrongAt }: { frame: number; crashAt: number; wrongAt: number }) {
  const crossed = lerp(frame, [wrongAt, wrongAt + 16], [0, 1]);
  const card = pop(frame, 0);
  return (
    <>
      <div style={{ position: "absolute", left: 120, top: 230, width: 800, opacity: card, transform: `translateY(${(1 - card) * 30}px)`, padding: "30px 36px", borderRadius: 22, background: C.panel, border: `3px solid ${crossed > 0.5 ? C.red : C.mint}`, boxShadow: glow(crossed > 0.5 ? C.red : C.mint, 0.6) }}>
        <Eyebrow color={C.cyan}>pr #2283 · the first evidence</Eyebrow>
        {FIRST_EVIDENCE.map((t, i) => (
          <div key={t} style={{ display: "flex", gap: 16, alignItems: "center", marginTop: 20, opacity: pop(frame, 6 + i * 8) }}>
            <span style={{ font: `800 34px ${FONT.sans}`, color: C.mint }}>✓</span>
            <span style={{ font: `600 30px ${FONT.sans}`, color: C.fg }}>{t}</span>
          </div>
        ))}
        <div style={{ font: `${crossed > 0.5 ? 700 : 500} 24px/1.4 ${FONT.sans}`, color: crossed > 0.5 ? C.red : C.fg2, marginTop: 20, opacity: lerp(frame, [24, 36], [0, 1]) }}>
          {crossed > 0.5 ? "True, but not enough: a reviewer reading only this would approve it." : "A reviewer reading only this would approve it."}
        </div>
      </div>
      {frame >= crashAt && <Minimap frame={frame - crashAt} />}
      {frame >= wrongAt + 10 && (
        <div style={{ position: "absolute", left: 520, top: 700, transform: "translateX(-50%)", whiteSpace: "nowrap" }}>
          <Words text="Green, and still wrong." start={wrongAt + 10} every={4} size={52} font={FONT.serif} weight={700} highlight={{ 3: C.red }} />
        </div>
      )}
    </>
  );
}

/** Parte B · Nuestro sistema: nuestro verde sobre TypeCollector.cs pasa a ESCAPE y el área pierde la confianza. */
function Ours({ frame, logAt, escapeAt }: { frame: number; logAt: number; escapeAt: number }) {
  const escaped = frame > escapeAt;
  const flip = frame > logAt + 20;
  const card = pop(frame, 0);
  const trust = pop(frame, logAt);
  return (
    <>
      <div style={{ position: "absolute", left: 140, top: 230, width: 760, opacity: card, transform: `translateY(${(1 - card) * 30}px)`, padding: "30px 36px", borderRadius: 22, background: C.panel, border: `3px solid ${escaped ? C.red : C.mint}`, boxShadow: glow(escaped ? C.red : C.mint, 0.7) }}>
        <Eyebrow color={C.cyan}>evidence ledger · another run of ours</Eyebrow>
        <div style={{ font: `700 32px ${FONT.mono}`, color: C.fg, marginTop: 14 }}>TypeCollector.cs</div>
        <div style={{ display: "flex", alignItems: "center", gap: 18, marginTop: 18 }}>
          <div style={{ padding: "8px 22px", borderRadius: 999, font: `800 28px ${FONT.sans}`, letterSpacing: 2, color: escaped ? "#fff" : C.bg, background: escaped ? C.red : C.mint, textDecoration: escaped ? "line-through" : undefined }}>✓ GREEN</div>
          <span style={{ font: `500 24px ${FONT.sans}`, color: C.fg2 }}>all 3 objections closed</span>
        </div>
        {escaped && (
          <div style={{ marginTop: 22, display: "inline-block", transform: `rotate(-4deg) scale(${0.7 + 0.3 * pop(frame, escapeAt)})`, padding: "6px 24px", border: `5px solid ${C.red}`, borderRadius: 10, color: C.red, font: `800 44px ${FONT.sans}`, letterSpacing: 4 }}>ESCAPE</div>
        )}
        <div style={{ font: `500 22px/1.4 ${FONT.sans}`, color: C.fg2, marginTop: 16, opacity: lerp(frame, [escapeAt + 10, escapeAt + 22], [0, 1]) }}>The moved crash was inside. Our evidence approved it.</div>
      </div>
      {frame >= logAt && (
        <div style={{ position: "absolute", left: 1000, top: 270, width: 780, opacity: trust, transform: `translateX(${(1 - trust) * 60}px)`, padding: "30px 36px", borderRadius: 22, background: C.panel, border: `3px solid ${flip ? C.amber : C.line}`, boxShadow: flip ? glow(C.amber, 0.8) : undefined }}>
          <Eyebrow color={C.fg2}>trust · track record</Eyebrow>
          <div style={{ font: `700 30px ${FONT.mono}`, color: C.fg, marginTop: 12 }}>SourceGenerator/CodeAnalysis</div>
          <div style={{ display: "flex", gap: 16, alignItems: "center", marginTop: 18 }}>
            <div style={{ padding: "8px 22px", borderRadius: 999, font: `800 28px ${FONT.sans}`, letterSpacing: 2, color: flip ? C.bg : C.cyan, background: flip ? C.amber : "transparent", border: `3px solid ${flip ? C.amber : C.cyan}` }}>
              {flip ? "WITHDRAWN" : "PROBATION"}
            </div>
            <span style={{ font: `600 26px ${FONT.sans}`, color: C.fg }}>{flip ? "escape logged" : "no track record yet"}</span>
          </div>
          <div style={{ font: `500 26px/1.4 ${FONT.sans}`, color: C.fg2, marginTop: 18, opacity: lerp(frame, [logAt + 30, logAt + 44], [0, 1]) }}>
            Green files here go back to a human until 5 clean signed changes earn it back.
          </div>
        </div>
      )}
    </>
  );
}

/** Escena 7 · La primera evidencia de #2283 sale verde y el contrainterrogatorio encuentra el crash; después, nuestro propio escape y la confianza retirada. */
export function S7Finding() {
  const frame = useCurrentFrame();
  const oursAt = at("finding", 3) - 8; // deja terminar "Green, and still wrong." y entra justo antes de la frase
  const part = frame < oursAt ? 0 : 1;
  const wipe = part === 1 ? lerp(frame - oursAt, [0, 10], [0, 100]) : 100;
  const startA = at("finding", 0) - 4;
  return (
    <AbsoluteFill>
      <Backdrop spot={{ x: 45, y: 45 }} />
      <AbsoluteFill style={{ clipPath: `inset(0 ${100 - wipe}% 0 0)` }}>
        {part === 0 ? (
          <FirstEvidence frame={frame - startA} crashAt={at("finding", 1) - startA} wrongAt={at("finding", 2) - startA} />
        ) : (
          <Ours frame={frame - oursAt} logAt={at("finding", 4) - oursAt} escapeAt={at("finding", 3) - oursAt} />
        )}
      </AbsoluteFill>
      {part === 1 && wipe < 100 && <div style={{ position: "absolute", left: `${wipe}%`, top: 0, width: 5, height: "100%", background: C.red, boxShadow: glow(C.red, 1.4) }} />}
    </AbsoluteFill>
  );
}
