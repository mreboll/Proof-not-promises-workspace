import React from "react";
import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";
import { C, FONT } from "../theme";

/** Fondo común: degradado petróleo, rejilla de plano técnico que se desplaza y viñeta. */
export function Backdrop({ drift = 0.4, spot }: { drift?: number; spot?: { x: number; y: number } }) {
  const frame = useCurrentFrame();
  const sx = spot?.x ?? 50;
  const sy = spot?.y ?? 42;
  return (
    <AbsoluteFill style={{ background: `radial-gradient(ellipse at ${sx}% ${sy}%, ${C.bg2} 0%, ${C.bg} 68%)` }}>
      <AbsoluteFill
        style={{
          backgroundImage: `linear-gradient(${C.grid} 1px, transparent 1px), linear-gradient(90deg, ${C.grid} 1px, transparent 1px)`,
          backgroundSize: "64px 64px",
          backgroundPosition: `0 ${frame * drift}px`,
        }}
      />
      <AbsoluteFill style={{ background: "radial-gradient(ellipse at center, transparent 55%, rgba(0,0,0,.55) 100%)" }} />
    </AbsoluteFill>
  );
}

/** Palabras que entran de una en una desde una máscara (tipografía cinética). */
export function Words({
  text, start, every = 4, size = 72, color = C.fg, weight = 800, font = FONT.sans, highlight = {}, align = "center", lineHeight = 1.12,
}: {
  text: string; start: number; every?: number; size?: number; color?: string; weight?: number; font?: string;
  highlight?: Record<number, string>; align?: "left" | "center"; lineHeight?: number;
}) {
  const frame = useCurrentFrame();
  const words = text.split(" ");
  return (
    <div style={{ font: `${weight} ${size}px/${lineHeight} ${font}`, color, textAlign: align, display: "flex", flexWrap: "wrap", justifyContent: align === "center" ? "center" : "flex-start", gap: `0 ${size * 0.28}px` }}>
      {words.map((w, i) => {
        const p = interpolate(frame, [start + i * every, start + i * every + 14], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.out(Easing.cubic) });
        return (
          <span key={`${w}-${i}`} style={{ display: "inline-block", overflow: "hidden", paddingBottom: size * 0.08 }}>
            <span style={{ display: "inline-block", transform: `translateY(${(1 - p) * 105}%)`, color: highlight[i] ?? color }}>{w}</span>
          </span>
        );
      })}
    </div>
  );
}

/** Trazo SVG que se dibuja solo (stroke-dashoffset). `length` aproximada del trazo. */
export function Draw({ d, start, duration = 30, length = 1200, color = C.mint, width = 4, fill = "none", glowOn = true }: {
  d: string; start: number; duration?: number; length?: number; color?: string; width?: number; fill?: string; glowOn?: boolean;
}) {
  const frame = useCurrentFrame();
  const p = interpolate(frame, [start, start + duration], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.inOut(Easing.cubic) });
  return (
    <path
      d={d}
      fill={fill}
      stroke={color}
      strokeWidth={width}
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeDasharray={length}
      strokeDashoffset={length * (1 - p)}
      style={glowOn ? { filter: `drop-shadow(0 0 6px ${color})` } : undefined}
    />
  );
}

/** Etiqueta pequeña en mayúsculas espaciadas (rótulos técnicos). */
export function Eyebrow({ children, color = C.fg2, style }: { children: React.ReactNode; color?: string; style?: React.CSSProperties }) {
  return <div style={{ font: `700 20px ${FONT.mono}`, letterSpacing: 4, textTransform: "uppercase", color, ...style }}>{children}</div>;
}
