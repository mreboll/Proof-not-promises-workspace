import { loadFont as loadCaveat } from "@remotion/google-fonts/Caveat";
import { loadFont as loadInter } from "@remotion/google-fonts/Inter";
import { loadFont as loadMono } from "@remotion/google-fonts/JetBrainsMono";
import { loadFont as loadSerif } from "@remotion/google-fonts/SourceSerif4";

// Serif para lo que se firma, sans para la interfaz, mono para lo que se verifica, manuscrita para la firma.
export const FONT = {
  sans: loadInter("normal", { weights: ["400", "600", "700", "800"], subsets: ["latin"] }).fontFamily,
  mono: loadMono("normal", { weights: ["400", "600"], subsets: ["latin"] }).fontFamily,
  serif: loadSerif("normal", { weights: ["600", "700"], subsets: ["latin"] }).fontFamily,
  hand: loadCaveat("normal", { weights: ["600"], subsets: ["latin"] }).fontFamily,
};

// Lienzo oscuro tipo plano técnico. Los dos colores de la paleta, como luz: verde azulado (mint) y azul verdoso (cyan).
// Los veredictos siguen siendo verde/ámbar/rojo: tienen significado.
export const C = {
  bg: "#051a22",
  bg2: "#0b3341",
  grid: "rgba(34,211,180,.07)",
  fg: "#e6f5f3",
  fg2: "#8db2b4",
  line: "rgba(141,178,180,.28)",
  mint: "#22d3b4", // verde azulado
  cyan: "#2a93c9", // azul verdoso
  panel: "#0c2c38",
  green: "#4cc26a",
  amber: "#e7a72a",
  red: "#ef5b4c",
  terminal: "#03141a",
  terminalBar: "#0a2a35",
  codeAdd: "#7fe0cf",
  codeDel: "#ffa59b",
  captionBg: "rgba(3,20,26,.88)",
  // Compatibilidad con los personajes y widgets anteriores (mismos papeles, valores para fondo oscuro).
  paper: "#051a22",
  sheet: "#0c2c38",
  ink: "#e6f5f3",
  ink2: "#8db2b4",
  rule: "rgba(141,178,180,.35)",
  accent: "#2a93c9",
  accent2: "#22d3b4",
  terminalInk: "#d6ecea",
  shadow: "0,0,0",
  modal: "#22d3b4",
};

/** Brillo de neón para texto o bordes. */
export const glow = (color: string, strength = 1): string =>
  `0 0 ${8 * strength}px ${color}, 0 0 ${22 * strength}px ${color}66`;

// Voz en off (scripts/make_voice.py, ElevenLabs) y música (scripts/make_music.py, compuesta por código). null = sin audio.
export const AUDIO: { voice: string | null; music: string | null } = { voice: "voice/vo.wav", music: "music/score.wav" };
// Volumen de la música: más alto sin voz y más bajo mientras se habla (con rampas cortas para que no se note el corte).
export const MUSIC_VOLUME = { open: 0.32, underVoice: 0.13, rampFrames: 8 };

export const FPS = 30;
export const W = 1920;
export const H = 1080;
