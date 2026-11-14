import React from "react";
import { useCurrentFrame } from "remotion";
import { C, FONT } from "../theme";

// Fragmentos con la forma de un diff de un generador de código C# (ilustrativos, no copiados del PR).
const LINES = [
  "+ [ExcludeFromCodeCoverage]",
  "+ internal sealed class FormatterResolver",
  "  {",
  "+     private static readonly object Gate = new();",
  "-     var t = refs[0];",
  "+     var t = refs.FirstOrDefault();",
  "+     if (t is null) return;",
  "      writer.WriteArrayHeader(count);",
  "+     context.AddSource(name, text);",
  "  }",
  "+ #if NETSTANDARD2_0",
  "+ #endif",
];

/** Cascada de líneas de diff que suben; `speed` = líneas por frame. */
export function CodeStream({ x, y, w, h, speed = 0.6, start = 0 }: { x: number; y: number; w: number; h: number; speed?: number; start?: number }) {
  const frame = useCurrentFrame();
  const shown = Math.max(0, Math.floor((frame - start) * speed));
  const visible = Math.floor(h / 34);
  const first = Math.max(0, shown - visible);
  const rows = Array.from({ length: Math.min(shown, visible) }, (_, i) => LINES[(first + i) % LINES.length]);
  return (
    <div style={{ position: "absolute", left: x, top: y, width: w, height: h, overflow: "hidden", background: C.terminal, borderRadius: 16, padding: "14px 18px", boxSizing: "border-box" }}>
      {rows.map((line, i) => (
        <div key={i} style={{ font: `400 22px/34px ${FONT.mono}`, whiteSpace: "pre", color: line.startsWith("+") ? C.codeAdd : line.startsWith("-") ? C.codeDel : C.terminalInk }}>
          {line}
        </div>
      ))}
    </div>
  );
}

/** Terminal con tecleo carácter a carácter y salida opcional. */
export function Terminal({ command, start, outputs = [], x, y, w, charsPerFrame = 2 }: { command: string; start: number; outputs?: { at: number; text: string }[]; x: number; y: number; w: number; charsPerFrame?: number }) {
  const frame = useCurrentFrame();
  const typed = command.slice(0, Math.max(0, Math.floor((frame - start) * charsPerFrame)));
  const cursor = Math.floor(frame / 15) % 2 === 0 ? "▌" : " ";
  return (
    <div style={{ position: "absolute", left: x, top: y, width: w, transform: "translate(-50%, -50%)", background: C.terminal, borderRadius: 18, boxShadow: "0 24px 60px rgba(0,0,0,.25)", overflow: "hidden" }}>
      <div style={{ height: 40, background: C.terminalBar, display: "flex", alignItems: "center", gap: 10, padding: "0 16px" }}>
        {["#ff5f57", "#febc2e", "#28c840"].map((c) => <span key={c} style={{ width: 14, height: 14, borderRadius: 7, background: c, display: "inline-block" }} />)}
      </div>
      <div style={{ padding: "26px 30px", font: `400 30px/1.6 ${FONT.mono}`, color: C.terminalInk, minHeight: 200 }}>
        <div><span style={{ color: C.codeAdd }}>$ </span>{typed}{typed.length < command.length ? cursor : ""}</div>
        {outputs.filter((o) => frame >= o.at).map((o) => <div key={o.text} style={{ color: "#8fb5b3", fontSize: 24 }}>{o.text}</div>)}
      </div>
    </div>
  );
}
