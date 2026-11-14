# Guion completo: vídeo (2:00) y pitch en directo (3:00)

Frases que se dicen **en inglés**; notas de pantalla en español. Ritmo de referencia: ~150 palabras por minuto.
La parte técnica (1:10–1:45) y el minuto extra del pitch están detallados en [guion-demo-evidencia.md](guion-demo-evidencia.md);
aquí van completos para ensayar de corrido. Todas las cifras son reales y salen de `demo/`, `fixtures/` y `docs/`.

Qué tener abierto: `demo/index.html`, `demo/2283-dotnet.html`, `demo/2297.html` y `docs/lessons-log.md`.

---

## Vídeo — 2:00 estricto

### 0:00–0:30 · El problema (≈70 palabras)
Pantalla: el diff de #2297 en GitHub haciendo scroll (237 ficheros), luego un botón "Approve".

> "An AI agent can change two hundred files in a single pull request. But a human still has to sign it.
> Reading every line is impossible. Trusting the AI's own summary is negligent: it sounds just as sure when it is wrong.
> So the real question is not 'is this code good?'. It is: what evidence lets a person sign without reading every line?"

### 0:30–1:10 · El embudo (≈100 palabras)
Pantalla: `demo/2283-dotnet.html`, la tira del embudo T1 → T2 → T3; resaltar cada etapa al nombrarla.

> "Our answer is a funnel with one rule: no model approves anything by argument. Only executable proof counts.
> First, triage. Static rules, no AI, decide how risky each file is. A model checks whether the issue actually asked for it.
> Second, evidence. A model that never sees the fix writes a test from the issue alone: it must fail before and pass after.
> And we compare the generator's output across thirty-one cases: outside the issue, nothing may change.
> Third, cross-examination. A Prosecutor looks for what the tests missed. The Defender can only answer with a test."

### 1:10–1:45 · Demo sobre #2283 (≈85 palabras)
Seguir la tabla de [guion-demo-evidencia.md](guion-demo-evidencia.md#vídeo--110145-35-s-estricto): decisión, test del cambio,
invarianza, interrogatorio con "possible defect", firma y la cifra de 237 ficheros.

### 1:45–2:00 · Honestidad (≈35 palabras)
Pantalla: `docs/lessons-log.md` haciendo scroll, luego la Concept Card.

> "Every time an AI failed us during this hackathon, we logged it, with the rule that caught it.
> The system doesn't replace the signer. It tells them exactly what is proven, and what isn't."

---

## Pitch en directo — 3:00

| Tiempo | Bloque | Notas |
|---|---|---|
| 0:00–0:25 | El problema | Las mismas frases que el vídeo, un poco más lentas. Pregunta directa al jurado: "Would you sign a 237-file PR you can't read?" |
| 0:25–1:00 | El embudo | Igual que el vídeo. Señalar la tira del embudo en el informe. |
| 1:00–1:40 | Demo de #2283 | Igual que el vídeo, en el informe en directo. Detenerse en la salida desplegada del test: `InvalidOperationException … TypeCollector.GetObjectInfo`. |
| 1:40–2:40 | Minuto extra | El intercambio Fiscal/Defensor y dos lecciones, de [guion-demo-evidencia.md](guion-demo-evidencia.md#pitch-en-directo--minuto-extra-fiscal-frente-a-defensor--dos-lecciones). |
| 2:40–3:00 | Cierre | Frase de cierre, abajo. |

### 1:40 · Escala, si sobra tiempo dentro del minuto extra (≈35 palabras)
Pantalla: `demo/2297.html`, sección "What you need to read" y luego los 223 verdes plegados.

> "This one touches 237 files. The evidence approves 223 of them unread. At most fourteen need a human,
> and one of those is a change nobody asked for: it alters line breaks in the generated code."

### 2:40–3:00 · Cierre (≈45 palabras)
Pantalla: `demo/index.html`.

> "Other tools will give you an AI opinion about AI code. We don't trust opinions, ours included.
> On real AI-written pull requests, this funnel caught a fix that only moved the crash, while every green check said ship it.
> Proof, not promises."

---

## Notas de ensayo

- Cronometrar el vídeo: 2:00 es estricto. Si sobra texto, recortar primero el embudo (0:30–1:10), nunca la demo.
- "Prosecutor" y "Defender" siempre con el modelo la primera vez: Nemotron (NVIDIA) y Gemini (Google).
- No decir que Modal acelera el pipeline completo "2×", ni que el Fiscal en Modal encontró el crash desplazado
  (ver "No decir" en [guion-demo-evidencia.md](guion-demo-evidencia.md#no-decir)).
- Si preguntan por los números: "Every report in the demo folder is rebuilt from the recorded runs with one command."
