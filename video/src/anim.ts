import { Easing, interpolate, spring } from "remotion";
import { FPS } from "./theme";

const CLAMP = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

/** 0 → 1 entre `start` y `start + duration` (frames locales de la escena), con easing suave. */
export function progress(frame: number, start: number, duration: number): number {
  return interpolate(frame, [start, start + duration], [0, 1], { ...CLAMP, easing: Easing.inOut(Easing.cubic) });
}

/** Opacidad de entrada y salida de una escena completa (transición sin solapar escenas). */
export function sceneFade(frame: number, duration: number, edge = 12): number {
  return interpolate(frame, [0, edge, duration - edge, duration], [0, 1, 1, 0], CLAMP);
}

/** Entrada con rebote (sellos, tarjetas). */
export function pop(frame: number, start: number): number {
  return spring({ frame: frame - start, fps: FPS, config: { damping: 12, stiffness: 140, mass: 0.6 } });
}

/** Valor lineal acotado: atajo para posiciones y contadores. */
export function lerp(frame: number, input: number[], output: number[]): number {
  return interpolate(frame, input, output, CLAMP);
}
