# Guion: demo técnica (vídeo 1:10–1:45 y minuto extra del pitch)

Las frases que se dicen van **en inglés** (jurado y reportes en inglés); las notas de pantalla, en español.
Todas las cifras son reales: fuentes en `docs/numeros-evidencia.md`, `fixtures/` y `docs/lessons-log.md`.

Qué tener abierto:
- El informe HTML de #2283 (`python -m ledger.report.render fixtures/report_2283_dotnet.json`, el del crash desplazado).
- Una terminal con `python -m ledger.evidence.bench --issue 2283` ya ejecutado (o `fixtures/bench_2283.json`).

---

## Vídeo — 1:10–1:45 (35 s, estricto)

| Tiempo | Pantalla | Se dice |
|---|---|---|
| 1:10 | Cabecera del informe: **"Manual audit required"** | "Here is the real report for issue 2283, produced end to end on the real repository." |
| 1:14 | **Change test**: base en rojo, PR en verde | "A model that never saw the fix wrote this test from the issue alone. It fails on the base and passes on the PR: the bug is reproduced and fixed." |
| 1:21 | **Generation invariance**: tabla de hashes iguales | "Thirty-one snippets through the generator, base twice, PR once, in isolated processes. Outside the issue, every hash is identical." |
| 1:28 | **Cross-examination**: objeción en rojo, "possible PR defect" | "Then the Prosecutor asks what the tests missed. The Defender must answer with a test, and here the test fails on the PR: the AI fix only moved the crash." |
| 1:37 | **Sign-off** + cifra de 237 ficheros | "So the system refuses to sign. And on the 237-file PR, static rules clear 223 low-risk files; only 14 get deeper scrutiny." |

> Si sobra un segundo, en 1:21: "All AI-written code ran in network-less Modal sandboxes."

---

## Pitch en directo — minuto extra (Fiscal frente a Defensor + dos lecciones)

**1. El intercambio (≈25 s)** — pantalla: *Cross-examination*, objeciones 1 a 3.
- "The Prosecutor is Nemotron. The Defender is Gemini. Different model families, so they don't share blind spots."
- "Objection one: the Defender's test passes on the PR and fails against a mutant that breaks that branch. Proven, closed."
- "Objections two and three: the Defender's tests fail on the PR itself. We reproduced it independently: for a generic type from another assembly with an invalid key, the fix turns an IndexOutOfRange into an InvalidOperation. The resolver is still not generated — exactly the damage the issue complains about. The change test and the invariance were both green. A reviewer reading only those would have approved it."

**2. Lección: el falso "bug reproducido" (≈15 s)** — pantalla: `lessons-log.md`, fila H5.
- "Our own pipeline lied to us once. In the sandbox there is no network, the AI test tried to download packages, and that failure looked exactly like a reproduced bug. Now infrastructure failures are marked INFRA and can never count as evidence."

**3. Lección: el issue pobre (≈15 s)** — pantalla: fila de #2234 en `numeros-evidencia.md`.
- "Issue 2234 is one sentence long. The AI picked the right scenario but a weak assertion, and the test passed on the base too. The rule 'a bug-fix test must fail on the base' caught it. A poor ticket gives poor evidence, and the system says so instead of approving."

**Cierre del minuto (≈5 s):** "Every number here is reproducible with one command."

---

## Modal (si el jurado de Modal está en la sala, 10 s)

Pantalla: terminal con el bench.
- "Base, PR and mutant run in parallel in Modal sandboxes with `block_network=True`: 28 seconds, against 63 sequentially on the laptop, with identical results. Building the image with all packages pre-downloaded is what makes no-network execution real."

---

## Preguntas probables del jurado (respuestas cortas)

| Pregunta | Respuesta |
|---|---|
| "What if the AI writes a trivial test?" | "It must fail against a mutant. Trivial tests pass against the mutant and are rejected — it happened in our Modal run." |
| "What if the test itself is wrong?" | "Issue 2129: the AI test failed on the PR, so no evidence and RED. The invariance, a separate oracle, showed the feature worked, pointing the human straight at the test." |
| "Why not compare serialized bytes?" | "All four PRs change the source generator and analyzer, not runtime serialization. We compare generated code and diagnostics." |
| "Isn't 2297 a diff everywhere?" | "Yes, by design it adds an attribute to all generated code. We declare that one transformation, normalize only it, and show it in the report. Everything else stays identical." |
| "Is it deterministic?" | "The base runs twice and must hash identically before any PR difference counts. LLM answers are cached on disk, so the demo replays without new calls." |
| "What doesn't it do?" | "It can't catch a wrong ticket, and it needs a differential oracle. Issue 2234 shows the first limit honestly." |

---

## No decir

- Que Modal acelera el pipeline completo "2×": el pipeline completo bajó de 18–22 min a 11 min, pero es una sola ejecución y la Etapa 3 de B es secuencial.
- Que el Fiscal en Modal encontró el crash desplazado: fue en la ejecución local; en la de Modal las preguntas fueron otras.
- Cifras de la Etapa 1 como propias: los 237 ficheros (223 en alcance/bajo, 12 en alcance/alto, 2 fuera de alcance) son del triaje de B (`fixtures/triage_2297.json`).
