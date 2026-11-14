// Escenas del vídeo, en frames absolutos a 30 fps. Total: 3600 = 2:00 exactos.
export const SCENES = {
  intro: { from: 0, duration: 205 },
  friday: { from: 205, duration: 335 },
  problems: { from: 540, duration: 300 },
  command: { from: 840, duration: 270 },
  triage: { from: 1110, duration: 510 },
  crossExam: { from: 1620, duration: 730 },
  owner: { from: 2350, duration: 300 },
  finding: { from: 2650, duration: 440 },
  product: { from: 3090, duration: 90 },
  sign: { from: 3180, duration: 285 },
  close: { from: 3465, duration: 135 },
} as const;

export const TOTAL_FRAMES = 3600;

// Cada escena (salvo la primera) empieza TRANSITION frames antes y entra por encima de la anterior con su forma.
export const TRANSITION = 22;

export type SceneKey = keyof typeof SCENES;

// Voz en off (inglés), por escena y por frase. La animación se sincroniza con el inicio de cada frase (src/cues.ts).
export const VOICE: Record<SceneKey, string[]> = {
  intro: ["AI agents now generate more tokens than humans.", "So who reviews all that code?"],
  friday: ["An AI agent just changed two hundred and thirty-seven files.", "Another AI reviewed it: ninety-eight percent confident.", "But the name on the approval is yours."],
  problems: ["Reading every line doesn't scale.", "Confident isn't correct.", "An AI grading an AI shares its blind spots.", "And nobody owns the merge."],
  command: ["Our answer: one rule.", "No model approves anything. Only executable evidence counts."],
  triage: [
    "First, static rules, not a model, rank the risk of every file.",
    "Then a model that never sees the fix writes a test from the issue alone.",
    "It must fail before, and pass after.",
    "Outside the issue, the generated code must not change, across twenty-one cases.",
  ],
  crossExam: [
    "Then a Prosecutor, Nemotron, attacks every high-risk file.",
    "The Defender, Gemini, can't argue: it must answer with a test that kills a broken mutant.",
    "One by one, that took over an hour.",
    "In parallel, every objection fans out to locked Modal sandboxes: seventeen minutes.",
    "And most objections don't close. That's the point: you see which.",
  ],
  owner: ["What lands on your desk isn't two hundred files. It's twelve.", "Where evidence is missing, it refuses to decide, and tells you exactly what to read."],
  finding: [
    "On another PR, the first evidence was all green.",
    "Then cross-examination tests showed the AI fix only moved the crash.",
    "Green, and still wrong.",
    "In another run, our evidence missed it.",
    "We logged it as an escape, and that area lost its trust.",
  ],
  product: ["The real report, traced to the issue."],
  sign: ["A sample, picked by hash, not by the AI, is read in full.", "Then you sign what was checked, what wasn't, and the risk you accept."],
  close: ["AI reviews. Humans stay accountable.", "Proof, not promises."],
};
