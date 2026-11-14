import cues from "./data/voice-cues.json";
import { SCENES, SceneKey, TRANSITION } from "./timeline";

export interface Cue {
  from: number;
  to: number;
  text: string;
}

// Tiempos reales de cada frase de la voz (los genera scripts/make_voice.py). Todo lo que se anima "cuando la voz
// dice X" se ancla aquí, así la imagen nunca va por delante ni por detrás de la voz.
export const CUES = cues as Record<SceneKey, Cue[]>;

/** Frame absoluto en que empieza la secuencia de una escena (las escenas con transición empiezan antes). */
export function sceneStart(scene: SceneKey): number {
  return SCENES[scene].from - (scene === "intro" ? 0 : TRANSITION);
}

/** Inicio de la frase `i` de la escena, en frames LOCALES de esa escena (lo que devuelve useCurrentFrame()). */
export function at(scene: SceneKey, i: number): number {
  return CUES[scene][i].from - sceneStart(scene);
}

/** Fin de la frase `i`, en frames locales. */
export function end(scene: SceneKey, i: number): number {
  return CUES[scene][i].to - sceneStart(scene);
}

/** Frame absoluto a partir de un frame local de una escena (para colocar efectos de sonido). */
export function abs(scene: SceneKey, local: number): number {
  return sceneStart(scene) + local;
}
