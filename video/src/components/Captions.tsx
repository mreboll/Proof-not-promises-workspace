import React from "react";
import { useCurrentFrame } from "remotion";
import { CUES } from "../cues";
import { C, FONT } from "../theme";

const ALL = Object.values(CUES).flat();

/**
 * Subtítulos tipo karaoke: la palabra que se está diciendo se resalta (dan ritmo aunque se vea sin sonido).
 * Usa el frame ABSOLUTO y los tiempos reales de cada frase (src/data/voice-cues.json), repartidos por longitud de palabra.
 */
export function Captions() {
  const frame = useCurrentFrame();
  const cue = ALL.find((c) => frame >= c.from && frame < c.to + 6);
  if (!cue) return null;
  const words = cue.text.split(" ");
  const weights = words.map((w) => w.length + 2);
  const total = weights.reduce((a, b) => a + b, 0);
  const progress = Math.min(1, (frame - cue.from) / Math.max(1, cue.to - cue.from));
  let acc = 0;
  const current = words.findIndex((_, i) => {
    acc += weights[i] / total;
    return progress < acc;
  });
  return (
    <div style={{ position: "absolute", left: 0, right: 0, bottom: 40, display: "flex", justifyContent: "center", pointerEvents: "none" }}>
      <div style={{ maxWidth: 1500, background: C.captionBg, font: `500 32px/1.35 ${FONT.sans}`, padding: "10px 26px", borderRadius: 10, borderLeft: `5px solid ${C.mint}`, textAlign: "center" }}>
        {words.map((w, i) => {
          const said = current === -1 || i < current;
          const now = i === current;
          return (
            <span key={`${w}-${i}`} style={{ color: now ? C.mint : said ? "#fff" : "rgba(255,255,255,.55)", fontWeight: now ? 700 : 500 }}>
              {w}
              {i < words.length - 1 ? " " : ""}
            </span>
          );
        })}
      </div>
    </div>
  );
}
