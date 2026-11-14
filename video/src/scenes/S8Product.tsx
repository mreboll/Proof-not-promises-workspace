import React, { useCallback, useEffect, useRef, useState } from "react";
import { AbsoluteFill, IFrame, continueRender, delayRender, interpolate, staticFile, useCurrentFrame } from "remotion";
import { ReqTag } from "../components/Props";
import { Backdrop, Eyebrow } from "../components/Stage";
import { C, FONT, glow } from "../theme";

const WIN = { x: 210, y: 130, w: 1500, h: 810 };
const SWITCH = 52; // de la cabecera "Manual audit required" al bloque de firma

/** Elementos del informe en los que se detiene la cámara. */
function targets(doc: Document): HTMLElement[] {
  const decision = doc.querySelector<HTMLElement>("section.decision");
  const signHeading = Array.from(doc.querySelectorAll<HTMLElement>("h2")).find((h) => h.textContent?.trim() === "Sign-off");
  return [decision, signHeading?.parentElement ?? null].filter((e): e is HTMLElement => e !== null);
}

/**
 * Escena 8 · El producto real: el informe HTML de ESTA ejecución de #2297 (public/report-2297.html). Dos paradas con un
 * recuadro de luz: la decisión ("Manual audit required") y el bloque de firma. Zoom lento en cada una.
 */
export function S8Product() {
  const frame = useCurrentFrame();
  const ref = useRef<HTMLIFrameElement>(null);
  const [handle] = useState(() => delayRender("Cargando el informe real"));
  const [ready, setReady] = useState(false);
  const onLoad = useCallback(() => {
    setReady(true);
    continueRender(handle);
  }, [handle]);

  const stop = frame < SWITCH ? 0 : 1;
  const local = stop === 0 ? frame : frame - SWITCH;
  const zoom = interpolate(local, [0, 60], [1, 1.12], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  useEffect(() => {
    const doc = ref.current?.contentDocument;
    const win = ref.current?.contentWindow;
    if (!ready || !doc || !win) return;
    const els = targets(doc);
    els.forEach((el, i) => {
      el.style.outline = i === stop ? `5px solid ${C.mint}` : "none";
      el.style.outlineOffset = "8px";
      el.style.boxShadow = i === stop ? `0 0 0 14px rgba(34,211,180,.18)` : "";
    });
    const el = els[stop];
    if (el) win.scrollTo(0, Math.max(0, el.getBoundingClientRect().top + win.scrollY - 40));
  }, [ready, stop]);

  return (
    <AbsoluteFill>
      <Backdrop />
      <div style={{ position: "absolute", left: WIN.x, top: WIN.y, width: WIN.w, height: WIN.h, borderRadius: 18, overflow: "hidden", border: `2px solid ${C.line}`, boxShadow: `${glow(C.cyan, 0.5)}, 0 40px 90px rgba(0,0,0,.6)` }}>
        <div style={{ height: 46, background: C.terminalBar, display: "flex", alignItems: "center", gap: 10, padding: "0 18px", position: "relative", zIndex: 2 }}>
          {["#ff5f57", "#febc2e", "#28c840"].map((c) => <span key={c} style={{ width: 13, height: 13, borderRadius: 7, background: c }} />)}
          <span style={{ marginLeft: 18, font: `500 20px ${FONT.mono}`, color: C.fg2 }}>report-2297.html · the sign-off report this run produced</span>
        </div>
        <div style={{ transform: `scale(${zoom})`, transformOrigin: "50% 0%" }}>
          <IFrame ref={ref} src={staticFile("report-2297.html")} onLoad={onLoad} style={{ width: WIN.w, height: WIN.h - 46, border: "none", background: "#fff" }} />
        </div>
      </div>
      <Eyebrow color={C.mint} style={{ position: "absolute", left: WIN.x, top: 70 }}>
        the real product · {stop === 0 ? "the decision" : "the sign-off block"}
      </Eyebrow>
      <ReqTag style={{ right: 210, top: 64 }} />
    </AbsoluteFill>
  );
}
