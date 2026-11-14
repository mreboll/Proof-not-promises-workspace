import React from "react";
import { AbsoluteFill, Audio, Sequence, staticFile } from "remotion";
import { Captions } from "./components/Captions";
import { Reveal, RevealKind } from "./components/Reveal";
import { abs, at, CUES, sceneStart } from "./cues";
import { S0Intro } from "./scenes/S0Intro";
import { S1Friday } from "./scenes/S1Friday";
import { S2Problems } from "./scenes/S2Problems";
import { S3Command } from "./scenes/S3Command";
import { S4TriageEvidence } from "./scenes/S4TriageEvidence";
import { S5CrossExam } from "./scenes/S5CrossExam";
import { S6Owner } from "./scenes/S6Owner";
import { S7Close } from "./scenes/S7Close";
import { S7Finding } from "./scenes/S7Finding";
import { S8Product } from "./scenes/S8Product";
import { S9Sign } from "./scenes/S9Sign";
import { AUDIO, C, MUSIC_VOLUME } from "./theme";
import { SCENES, SceneKey, TRANSITION } from "./timeline";

const VOICE_SPANS = Object.values(CUES).flat();

/** Volumen de la música en cada frame: baja mientras suena una frase (ducking) y sube en los silencios. */
function musicVolume(frame: number): number {
  const { open, underVoice, rampFrames } = MUSIC_VOLUME;
  const near = Math.min(...VOICE_SPANS.map((c) => (frame < c.from ? c.from - frame : frame > c.to ? frame - c.to : 0)));
  const k = Math.min(1, near / rampFrames);
  return underVoice + (open - underVoice) * k;
}

const SCENE_COMPONENTS: Record<SceneKey, () => React.ReactElement> = {
  intro: S0Intro,
  friday: S1Friday,
  problems: S2Problems,
  command: S3Command,
  triage: S4TriageEvidence,
  crossExam: S5CrossExam,
  owner: S6Owner,
  finding: S7Finding,
  product: S8Product,
  sign: S9Sign,
  close: S7Close,
};

// Cada corte entra con una forma distinta (ver components/Reveal.tsx). La primera escena no tiene transición.
const ENTRY: Partial<Record<SceneKey, { kind: RevealKind; origin?: { x: number; y: number } }>> = {
  friday: { kind: "iris", origin: { x: 50, y: 48 } },
  problems: { kind: "blinds" },
  command: { kind: "zoom", origin: { x: 50, y: 50 } },
  triage: { kind: "zoom", origin: { x: 45, y: 31 } },
  crossExam: { kind: "diagonal" },
  owner: { kind: "shutter" },
  finding: { kind: "iris", origin: { x: 50, y: 45 } },
  product: { kind: "zoom", origin: { x: 50, y: 50 } },
  sign: { kind: "diagonal" },
  close: { kind: "rise" },
};

type Sfx = { at: number; file: string; volume: number };

// Efectos de sonido anclados a lo que pasa en pantalla (mismos tiempos que la animación: src/cues.ts).
function soundtrack(): Sfx[] {
  const list: Sfx[] = [];
  (Object.keys(SCENES) as SceneKey[]).forEach((k) => {
    if (k !== "intro") list.push({ at: sceneStart(k), file: "whoosh", volume: 0.35 });
  });
  list.push({ at: abs("friday", at("friday", 1) + 24), file: "thump", volume: 0.8 });
  [0, 1, 2, 3].forEach((i) => list.push({ at: abs("problems", at("problems", i) - 4), file: "pop", volume: 0.5 }));
  list.push({ at: abs("command", 34), file: "tick", volume: 0.7 });
  list.push({ at: abs("command", at("command", 1) - 6), file: "thump", volume: 0.9 });
  list.push({ at: abs("triage", at("triage", 2) + 6), file: "thump", volume: 0.6 });
  list.push({ at: abs("crossExam", at("crossExam", 1) + 48), file: "thump", volume: 0.7 });
  list.push({ at: abs("crossExam", at("crossExam", 1) + 70), file: "crack", volume: 0.6 });
  list.push({ at: abs("crossExam", at("crossExam", 1) + 132), file: "glitch", volume: 0.5 });
  for (let f = at("crossExam", 2); f < at("crossExam", 3) - 18; f += 8) list.push({ at: abs("crossExam", f), file: "tick", volume: 0.45 });
  list.push({ at: abs("crossExam", at("crossExam", 3) - 16), file: "thump", volume: 0.8 });
  list.push({ at: abs("owner", at("owner", 1) - 4), file: "thump", volume: 0.8 });
  list.push({ at: abs("finding", at("finding", 1) + 42), file: "thump", volume: 0.9 }); // el crash aterriza
  list.push({ at: abs("finding", at("finding", 2)), file: "crack", volume: 0.8 }); // el 98 % se rompe
  list.push({ at: abs("finding", at("finding", 3)), file: "thump", volume: 0.8 }); // ESCAPE
  list.push({ at: abs("finding", at("finding", 4) + 20), file: "thump", volume: 0.7 }); // WITHDRAWN
  list.push({ at: abs("sign", at("sign", 1) - 6 + 14), file: "scratch", volume: 0.55 });
  return list;
}

/** El vídeo completo: 11 escenas solapadas en sus transiciones, subtítulos, voz, música y efectos. */
export function Demo() {
  return (
    <AbsoluteFill style={{ background: C.bg }}>
      {(Object.keys(SCENES) as SceneKey[]).map((key) => {
        const Scene = SCENE_COMPONENTS[key];
        const entry = ENTRY[key];
        const lead = entry ? TRANSITION : 0;
        return (
          <Sequence key={key} name={key} from={SCENES[key].from - lead} durationInFrames={SCENES[key].duration + lead}>
            {entry ? (
              <Reveal kind={entry.kind} origin={entry.origin} duration={TRANSITION}>
                <Scene />
              </Reveal>
            ) : (
              <Scene />
            )}
          </Sequence>
        );
      })}
      <Captions />
      {AUDIO.voice && <Audio src={staticFile(AUDIO.voice)} />}
      {AUDIO.music && <Audio src={staticFile(AUDIO.music)} volume={musicVolume} />}
      {soundtrack().map((s, i) => (
        <Sequence key={`${s.file}-${i}`} from={Math.max(0, s.at)} durationInFrames={45} layout="none">
          <Audio src={staticFile(`sfx/${s.file}.wav`)} volume={s.volume} />
        </Sequence>
      ))}
    </AbsoluteFill>
  );
}
