import React from "react";
import { useCurrentFrame } from "remotion";
import { C, FONT } from "../theme";

export type CharacterKind = "human" | "robot" | "gemini" | "nemotron";

interface CharacterProps {
  kind: CharacterKind;
  x: number;
  y: number;
  scale?: number;
  label?: string; // placa bajo el personaje ("Alex — owner", "Prosecutor"...)
  talking?: boolean;
  mirrored?: boolean;
  calm?: boolean; // humano: preocupado (false) o tranquilo (true)
  blindfold?: boolean; // Defensor: no ve el diff
}

// Paleta de cada robot: [carcasa clara, carcasa oscura, acento, visor]. Colores de marca, sin logos.
const ROBOT: Record<Exclude<CharacterKind, "human">, { stops: string[]; trim: string; accent: string; badge: string }> = {
  robot: { stops: ["#a3abb8", "#7c8595"], trim: "#5d6575", accent: "#7fe3ff", badge: "AI" },
  gemini: { stops: ["#4796e3", "#9177c7", "#ca6673"], trim: "#3a5fb0", accent: "#bfe0ff", badge: "GEMINI" },
  nemotron: { stops: ["#86c80a", "#76b900", "#5a8f00"], trim: "#1a1a1a", accent: "#c8ff6a", badge: "NEMOTRON" },
};

/** Personaje en SVG: una persona realista o un robot con los colores de su marca. */
export function Character(props: CharacterProps) {
  const { kind, x, y, scale = 1, label, mirrored = false } = props;
  const frame = useCurrentFrame();
  const bob = Math.sin(frame / 9) * (kind === "human" ? 1.5 : 3);

  return (
    <div style={{ position: "absolute", left: x, top: y + bob, transform: `translate(-50%, -50%) scale(${scale})`, width: 240, textAlign: "center" }}>
      <svg width={240} height={280} viewBox="0 0 240 280" style={{ transform: mirrored ? "scaleX(-1)" : undefined, overflow: "visible" }}>
        {kind === "human" ? <Human {...props} frame={frame} /> : <Robot {...props} frame={frame} />}
      </svg>
      {label && (
        <div style={{ marginTop: 4, font: `600 24px ${FONT.sans}`, color: C.ink, background: C.sheet, border: `2px solid ${C.rule}`, borderRadius: 12, padding: "4px 14px", display: "inline-block" }}>
          {label}
        </div>
      )}
    </div>
  );
}

type PartProps = CharacterProps & { frame: number };

function Human({ calm = true, talking = false, frame }: PartProps) {
  const skin = "#e9bf9b";
  const skinShade = "#d8a47f";
  const hair = "#3b2a20";
  const blink = frame % 110 > 104; // parpadeo ocasional
  const talk = talking ? Math.abs(Math.sin(frame / 3)) * 5 : 0;
  // Cejas: preocupado = extremos interiores hacia arriba.
  const browIn = calm ? 0 : -5;

  return (
    <g>
      <defs>
        <linearGradient id="shirt" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#1590a8" />
          <stop offset="1" stopColor={C.accent} />
        </linearGradient>
        <radialGradient id="face" cx="0.45" cy="0.4" r="0.7">
          <stop offset="0" stopColor="#f3cfae" />
          <stop offset="1" stopColor={skin} />
        </radialGradient>
      </defs>
      {/* torso y hombros */}
      <path d="M28 280 C30 214 62 192 120 190 C178 192 210 214 212 280 Z" fill="url(#shirt)" />
      <path d="M96 196 L120 232 L144 196 L132 190 L120 206 L108 190 Z" fill="#f4f1ea" />
      {/* cuello */}
      <path d="M102 158 L102 196 Q120 210 138 196 L138 158 Z" fill={skinShade} />
      {/* orejas */}
      <ellipse cx={70} cy={112} rx={9} ry={15} fill={skinShade} />
      <ellipse cx={170} cy={112} rx={9} ry={15} fill={skinShade} />
      {/* cara: óvalo con mandíbula */}
      <path d="M72 96 C72 58 94 40 120 40 C146 40 168 58 168 96 C168 132 152 166 120 172 C88 166 72 132 72 96 Z" fill="url(#face)" />
      {/* pelo con volumen */}
      <path d="M68 104 C60 58 86 26 122 26 C158 26 182 52 172 104 C168 84 160 66 146 60 C130 70 100 72 84 64 C76 74 72 88 68 104 Z" fill={hair} />
      <path d="M84 64 C100 70 128 70 146 60 C136 50 112 46 96 52 Z" fill="#4a362a" />
      {/* cejas */}
      <path d={`M88 ${88 + 0} Q98 ${84 + browIn} 108 ${86 + browIn}`} stroke={hair} strokeWidth={4} fill="none" strokeLinecap="round" />
      <path d={`M132 ${86 + browIn} Q142 ${84 + browIn} 152 ${88}`} stroke={hair} strokeWidth={4} fill="none" strokeLinecap="round" />
      {/* ojos: blanco, iris, pupila, párpado */}
      {blink ? (
        <>
          <path d="M89 102 Q98 105 107 102" stroke="#5a3d2e" strokeWidth={3} fill="none" strokeLinecap="round" />
          <path d="M133 102 Q142 105 151 102" stroke="#5a3d2e" strokeWidth={3} fill="none" strokeLinecap="round" />
        </>
      ) : (
        <>
          <ellipse cx={98} cy={102} rx={10} ry={6.5} fill="#fff" />
          <ellipse cx={142} cy={102} rx={10} ry={6.5} fill="#fff" />
          <circle cx={99} cy={102} r={4.6} fill="#5b4636" />
          <circle cx={143} cy={102} r={4.6} fill="#5b4636" />
          <circle cx={99} cy={102} r={2.2} fill="#1b1410" />
          <circle cx={143} cy={102} r={2.2} fill="#1b1410" />
          <circle cx={100.5} cy={100.5} r={1.1} fill="#fff" />
          <circle cx={144.5} cy={100.5} r={1.1} fill="#fff" />
          <path d="M88 99 Q98 93 108 99" stroke="#5a3d2e" strokeWidth={2} fill="none" />
          <path d="M132 99 Q142 93 152 99" stroke="#5a3d2e" strokeWidth={2} fill="none" />
        </>
      )}
      {/* nariz */}
      <path d="M120 106 Q115 124 114 128 Q120 132 127 128" stroke={skinShade} strokeWidth={3} fill="none" strokeLinecap="round" />
      {/* boca */}
      {calm ? (
        <path d={`M106 144 Q120 ${152 + talk} 134 144`} stroke="#9c4f45" strokeWidth={4} fill={talk > 1 ? "#7a2f2a" : "none"} strokeLinecap="round" />
      ) : (
        <path d="M108 148 Q120 142 132 148" stroke="#9c4f45" strokeWidth={4} fill="none" strokeLinecap="round" />
      )}
      {/* sombra suave de mejillas y mandíbula */}
      <ellipse cx={92} cy={128} rx={9} ry={5} fill="#e59a86" opacity={0.25} />
      <ellipse cx={148} cy={128} rx={9} ry={5} fill="#e59a86" opacity={0.25} />
      <path d="M86 150 Q120 182 154 150 Q140 170 120 172 Q100 170 86 150 Z" fill={skinShade} opacity={0.35} />
    </g>
  );
}

function Robot({ kind, talking = false, blindfold = false, mirrored = false, frame }: PartProps) {
  const p = ROBOT[kind as Exclude<CharacterKind, "human">];
  const gid = `robot-${kind}`;
  const mouth = talking ? 5 + Math.abs(Math.sin(frame / 3)) * 9 : 4;
  const glow = 0.75 + Math.sin(frame / 6) * 0.25;
  const armSwing = talking ? Math.sin(frame / 5) * 8 : 0;

  return (
    <g>
      <defs>
        <linearGradient id={gid} x1="0" y1="0" x2="1" y2="1">
          {p.stops.map((c, i) => (
            <stop key={c} offset={i / (p.stops.length - 1)} stopColor={c} />
          ))}
        </linearGradient>
      </defs>
      {/* antena */}
      <line x1={120} y1={14} x2={120} y2={44} stroke={p.trim} strokeWidth={6} strokeLinecap="round" />
      <circle cx={120} cy={12} r={9} fill={p.accent} opacity={glow} />
      {/* brazos */}
      <g transform={`rotate(${armSwing} 52 196)`}>
        <rect x={30} y={190} width={26} height={70} rx={13} fill={`url(#${gid})`} stroke={p.trim} strokeWidth={3} />
      </g>
      <g transform={`rotate(${-armSwing} 188 196)`}>
        <rect x={184} y={190} width={26} height={70} rx={13} fill={`url(#${gid})`} stroke={p.trim} strokeWidth={3} />
      </g>
      {/* cuerpo con panel */}
      <rect x={58} y={170} width={124} height={110} rx={22} fill={`url(#${gid})`} stroke={p.trim} strokeWidth={4} />
      <rect x={74} y={196} width={92} height={34} rx={8} fill={p.trim} />
      {/* Si el personaje va en espejo, el texto se vuelve a girar para que se lea bien. */}
      <g transform={mirrored ? "translate(240 0) scale(-1 1)" : undefined}>
        <text x={120} y={219} textAnchor="middle" fill="#fff" style={{ font: `700 ${p.badge.length > 6 ? 13 : 16}px ${FONT.sans}`, letterSpacing: 1 }}>
          {p.badge}
        </text>
      </g>
      <circle cx={96} cy={252} r={6} fill={p.accent} opacity={glow} />
      <circle cx={120} cy={252} r={6} fill={p.trim} />
      <circle cx={144} cy={252} r={6} fill={p.accent} opacity={1 - glow + 0.5} />
      {/* cuello */}
      <rect x={104} y={150} width={32} height={24} rx={6} fill={p.trim} />
      {/* cabeza con visor */}
      <rect x={56} y={44} width={128} height={110} rx={30} fill={`url(#${gid})`} stroke={p.trim} strokeWidth={4} />
      <rect x={70} y={62} width={100} height={60} rx={18} fill="#0f141d" />
      {blindfold ? (
        <rect x={64} y={74} width={112} height={26} rx={10} fill={C.ink} stroke="#fff" strokeWidth={2} />
      ) : (
        <>
          <ellipse cx={98} cy={88} rx={9} ry={10} fill={p.accent} opacity={glow} />
          <ellipse cx={142} cy={88} rx={9} ry={10} fill={p.accent} opacity={glow} />
        </>
      )}
      <rect x={108} y={106} width={24} height={mouth} rx={3} fill={p.accent} />
      {/* tornillos */}
      <circle cx={64} cy={99} r={4} fill={p.trim} />
      <circle cx={176} cy={99} r={4} fill={p.trim} />
    </g>
  );
}
