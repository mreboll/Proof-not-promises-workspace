# Guion técnico del vídeo demo (Remotion) — 2:00

Prioridad: las ideas del equipo (humano entre dos IA → problemas → nuestra solución con las LLM como personajes →
secuencial frente a paralelo → lo que recibe el humano y cómo termina su trabajo). El guion anterior
([pitch-script.md](pitch-script.md)) se usa de apoyo para el texto. Voz en off **en inglés**; notas en español.
**Todas las cifras son reales**; la fuente de cada una está en la última columna de cada escena y en §6.

---

## 1. Especificación

| Parámetro | Valor |
|---|---|
| Resolución / fps | 1920×1080 · **30 fps** |
| Duración | **2:00 estricto = 3600 frames** |
| Herramienta | Remotion 4 (React + TypeScript), `@remotion/transitions`, `@remotion/google-fonts` |
| Tipografía | Serif para lo que se firma (Source Serif 4), sans para la interfaz (Inter), mono para código (JetBrains Mono) — la misma dirección que los informes |
| Voz | ~150 palabras/min → **≤ 290 palabras** en total. Grabada o TTS; se monta encima con `<Audio>` |
| Música | Base suave al −24 dB; un "golpe" en el cambio de secuencial a paralelo (escena 5) |
| Subtítulos | Quemados en pantalla (el jurado puede verlo sin sonido) |

**Paleta** (la de los informes, para que el vídeo y la demo se vean como una sola cosa):

| Token | Claro | Uso |
|---|---|---|
| `paper` | `#f6f4ef` | Fondo |
| `ink` / `ink2` | `#1c2330` / `#4a5363` | Texto |
| `accent` | `#2b4f8c` | Humano, firma, títulos |
| `green` / `yellow` / `red` | `#2f7d4f` / `#b8860b` / `#b23a3a` | Veredictos (siempre con texto o icono además del color) |

---

## 2. Personajes

| Personaje | Rol en la historia | Diseño |
|---|---|---|
| **El humano** ("Alex, owner") | Firma. Siempre en azul `accent`. Tiene nombre en una placa: la firma es de una persona concreta | Figura plana, sentada, con un bolígrafo |
| **El Agente** | Escribe el código del PR | Robot neutro gris, sin marca (en el reto es "un agente") |
| **El revisor de IA "clásico"** | Solo en la escena 1: dice "LGTM ✅" | El mismo robot gris en espejo: el mismo modelo revisándose a sí mismo |
| **Gemini — Defensor** | Escribe el test del cambio (solo con el issue), los tests del Defensor y los mutantes | Muñeco con la forma/colores del logo de Gemini |
| **Nemotron — Fiscal** | Plantea las objeciones | Muñeco con la forma/colores del logo de NVIDIA |
| **Sandboxes de Modal** | Ejecutan cada test aislado y sin red | Cajas verdes con el logo de Modal y un candado ("no network") |
| **El mutante** | La versión rota a propósito del código | El bloque de código con un "gemelo malvado" (cuernos/glitch) |

> **Logos:** son marcas registradas. Usar los logos oficiales de los kits de prensa (Google, NVIDIA, Modal), sin
> deformarlos, y como "insignia" sobre el muñeco en vez de redibujarlos. Los tres son partners del reto, pero conviene
> revisar sus guías de marca antes de publicar. Plan B si no se permite: muñecos de formas simples con los colores y el
> nombre debajo.

---

## 3. Escenas

Frames absolutos a 30 fps. Cada escena es un `<Sequence from={…} durationInFrames={…}>`; las transiciones de
`@remotion/transitions` (12–15 frames) restan del tramo de la escena siguiente.

### Escena 1 · "El viernes por la tarde" — 0:00–0:20 (frames 0–600)

**Imagen.** Pantalla dividida en tres.
- **Izquierda:** el Agente teclea. El código sube en cascada (`CodeStream`) y un contador de ficheros va subiendo: `1… 48… 237 files changed`.
- **Derecha:** el revisor de IA (el mismo robot, en espejo) escanea el diff a toda velocidad y sella **"LGTM ✅ 98% confident"** (sin nota al pie).
- **Centro:** el humano, con su placa *Alex — owner*, mira a un lado y a otro. Delante tiene un botón grande **[Approve]** y su firma pendiente.

**Animación.** El código entra con `interpolate` sobre el frame, a 4 líneas/frame. El sello entra con un `spring` y rebota. En el frame 480, zoom lento (`scale` de 1 a 1,15) sobre la cara del humano y el botón.

**Voz (≈45 palabras).**
> "An AI agent just changed two hundred and thirty-seven files. Another AI reviewed it, and says
> it's fine. Ninety-eight percent confident. But the name on the approval… is yours."

**Fuente:** 237 ficheros, rama `ju26-issue-2297` (`fixtures/triage_2297.json`). El "98 %" es ficticio a propósito, porque representa la confianza autodeclarada que el reto rechaza. Rotularlo como ejemplo.

### Escena 2 · Los problemas — 0:20–0:35 (frames 600–1050)

**Imagen.** La escena 1 se congela, se desatura y se encoge al fondo. Del humano salen 4 tarjetas, una cada ~90 frames, con un icono cada una:
1. 📄 **"Too much to read"**: "Nobody reads 237 files."
2. 🪞 **"AI grading AI"**: si el mismo modelo escribe y revisa, comparte sus puntos ciegos.
3. 🎲 **"Confident ≠ correct"**: el 98 % se rompe y se convierte en un signo de interrogación.
4. ✍️ **"Who owns the merge?"**: la firma tiembla.

Al final, las tarjetas se apartan y aparece en serif grande: **"What evidence lets a person sign without reading every line?"**

**Voz (≈50 palabras).**
> "Reading every line doesn't scale. Trusting the AI's summary is negligent: it sounds just as sure when it's wrong. And
> when an AI grades another AI, they share the same blind spots. So the question isn't 'is this code good?' It's: what
> evidence lets a person sign without reading it all?"

### Escena 3 · El comando — 0:35–0:45 (frames 1050–1350)

**Imagen.** Transición `slide` a un terminal oscuro centrado (`Terminal`). Se escribe con efecto de tecleo (`typewriter`, 2 caracteres por frame):

```text
$ LEDGER_RUNNER=modal python -m ledger run --issue 2297
```

Se pulsa Enter. Salen 3 líneas de log y el terminal se pliega hacia arriba para convertirse en la cabecera de un **embudo** de tres niveles: **T1 Triage → T2 Evidence → T3 Cross-examination** (en el vídeo se numeran en orden de aparición; en los informes del repo siguen siendo T3 → T1 → T2).

**Voz (≈30 palabras).**
> "Proof, not promises. One command, and one rule: no model approves anything by argument. Only executable evidence
> counts. When there isn't any, the system refuses to decide."

### Escena 4 · Triaje y evidencia — 0:45–1:05 (frames 1350–1950)

**4a · Triaje (frames 1350–1620).** Los 237 ficheros caen como fichas por el embudo y una **regla estática** (icono de regla, sin cerebro de IA) los separa en tres cubos con contador:
- **223 · low risk** (verde claro): 222 son snapshots generados;
- **12 · high risk** (rojo);
- **2 · out of scope** (amarillo); uno, `TransformUtilities.cs`, parpadea con el rótulo "nobody asked for this".

Un rótulo pequeño dice "risk: static rules · scope: a model reads the issue".

**4b · Evidencia (frames 1620–1950).**
- **El test del cambio:** el muñeco **Gemini** lleva una venda sobre el diff ("never sees the fix") y solo lee el issue. Escribe un test que se mete en dos cajas de Modal, BASE y PR. Sale ❌ rojo en BASE y ✅ verde en PR.
- **La invarianza:** al lado se lanzan 31 cartas (los casos de la invarianza). Cada una muestra un hash base = hash PR, y se van marcando con ✓.

**Voz (≈50 palabras).**
> "First, triage. Static rules, not a model, decide how risky each file is. Then evidence. A model that never sees the
> fix writes a test from the issue alone: it must fail before, and pass after. And outside the issue, the generated
> code must stay identical, across thirty-one cases."

**Fuentes:** 223/12/2 y `TransformUtilities.cs` OUT/HIGH (`fixtures/triage_2297.json`). Test rojo en base y verde en PR, e invarianza tras la normalización declarada (`fixtures/evidence_2297.json`). El corpus tiene 31 snippets (`harness/corpus`).

### Escena 5 · Fiscal contra Defensor, y de secuencial a paralelo — 1:05–1:30 (frames 1950–2700)

Es la escena clave para Modal y para la idea de "muñequitos".

**5a · Una objeción (frames 1950–2250).** Plano cercano de un fichero de riesgo alto (`FormatterTemplate.cs`).
- **Nemotron (Fiscal)** sube a un estrado y lanza un bocadillo: *"What if the type is generic and comes from another assembly?"*.
- **Gemini (Defensor)** intenta responder con un bocadillo de texto, que se tacha con una ✗ y el rótulo **"No arguments. Only tests."**. Entonces entrega una **tarjeta de test**.
- Aparece el **mutante**, el gemelo malvado del código.
- El test entra en dos cajas de Modal a la vez: PR ✅ y MUTANT ❌. Rótulo: **"A test counts only if it kills the mutant."**

**5b · Secuencial (frames 2250–2430).** Se abre el plano y se ven los **12 ficheros × 3 objeciones = 36 tarjetas** en **una sola fila**, avanzando de una en una por una única caja de Modal. Un reloj arriba corre muy deprisa: `0:10… 0:35… 1:00… 1:05` y se tacha con el sello rojo **"over 1 hour — cancelled"**.

**5c · Paralelo (frames 2430–2700).** Golpe musical. La fila se rompe: las 36 tarjetas saltan a la vez, cada una hacia su propia caja. Se forma una cuadrícula de sandboxes (muestra 16 a la vez, el pico real) y varios muñecos de Gemini y Nemotron trabajan a la vez en las 12 calles. El reloj se para en **"~17 min"**. Debajo, en pequeño y en mono:
`36 objections · 126 sandboxes · peak 16 · 0 rate-limit errors · $2.86 of Modal for the whole hackathon`

**Voz (≈60 palabras).**
> "Then the cross-examination. A Prosecutor, Nemotron, attacks every high-risk file. The Defender, Gemini, cannot argue:
> it can only answer with a test, and the test must kill a deliberately broken mutant. Done one by one, that took over
> an hour. In parallel, each test in its own network-less sandbox: about seventeen minutes."

**Fuentes y frases que no se pueden decir:**
- **Más de 1 h en secuencia, y se canceló:** `PROJECT-CONTEXT.md` §10.
- **~17 min en paralelo:** es la primera ejecución completa de #2297 (en pantalla, el sello dice "14–20 min over 4 runs"; `fixtures/measure_2297_par_v1.json`: 1024 s, 36 objeciones, 126 sandboxes, pico 16, 0 errores 429). Las cuatro ejecuciones dieron entre 14 y 20 min. **No decir "4× más rápido"** ni ninguna cifra única como si fuera definitiva; "about seventeen minutes" es honesto.
- **El texto de la pregunta del Fiscal** es ilustrativo. Si se quiere una pregunta literal, hay que sacarla de `fixtures/report_2297_modal.json`.
- **Coste:** 2,86 $, según `modal billing report` (`docs/numeros-evidencia.md`).

### Escena 6 · Lo que recibe el humano, y cómo termina su trabajo — 1:30–1:52 (frames 2700–3360)

**6a · El informe (frames 2700–2970).** Transición a una maqueta del informe real (`ReportCard`: captura de `demo/2297.html` o recreación en React con los mismos datos). Aparece de arriba abajo:
- **Decision:** sello rojo **"Manual audit required"**;
- **barra de veredictos:** casi toda verde, con una franja fina amarilla y roja;
- **contador "What you need to read":** **12 of 237**, el dato de la ejecución que se muestra (los otros 225 se pliegan y quedan aprobados por la evidencia, sin leer);
- **cada fichero a leer**, con su motivo en una línea. Por ejemplo, *"refused to decide: 2 tests fail on the PR"*.

**6b · El hallazgo (frames 2970–3120).** Inserto rápido de #2283, con sello "REAL FINDING": dos líneas de código.
`IndexOutOfRangeException  →  InvalidOperationException`
Rótulo: **"The AI fix didn't remove the crash. It moved it."** Debajo, en pequeño: *its own test and the invariance were green.*

**6c · La firma (frames 3120–3360).** Vuelve el humano de la escena 1, ahora tranquilo. Delante tiene el bloque de firma con sus **tres listas**, que se van marcando:
- ✅ **What was checked, and by what**
- ⚠️ **What was NOT checked, and why**
- ✍️ **Residual risk I accept**

Lee 2 spot-checks ("Spot-checks assigned: 2 green files, picked by hash") y escribe su nombre: *Alex Kim*. Marca **[✓] APPROVED / REJECTED** sin elegir todavía. El bolígrafo se queda sobre "REJECTED / fix first": la decisión es suya. Termina con un comando breve:
`python -m ledger.trust record-change report-2297.json --owner "Alex Kim"`
y un panel *Trust by area* donde un área aparece como **"withdrawn after an escape"**.

**Voz (≈55 palabras).**
> "What lands on your desk isn't two hundred files. In this run, it's twelve, each with the reason it needs your eyes, and the
> failing tests to prove it. On another PR, this caught an AI fix that only moved the crash. You sign three things:
> what was checked, what wasn't, and the risk you accept."

**Fuentes:**
- **"12 of 237"** sale de la ejecución que se muestra (`fixtures/report_2297_modal.json`: 225 verdes, 1 amarillo y 11 rojos). El 14 de la Concept Card es el máximo posible (12 de riesgo alto + 2 fuera de alcance); en esta ejecución, 2 de riesgo alto se cerraron con tests válidos. No mezclar el máximo con la barra de una ejecución concreta.
- **El crash desplazado** salió de la ejecución local de #2283 (`demo/2283-dotnet.html`). **No decir que lo encontró la ejecución de Modal.**
- **El área retirada** viene del escape real de #2283, guardado en `trust/track_record.json`.
- **El nombre "Alex Kim"** es ficticio. Rotularlo como ejemplo o usar el nombre real de quien firma en el equipo.

### Escena 7 · Cierre — 1:52–2:00 (frames 3360–3600)

**Imagen.** Fundido a fondo `paper`.
1. En serif grande, palabra a palabra: **"AI reviews. Humans stay accountable."**
2. Durante un segundo, una tira con el log de lecciones haciendo scroll: "24 real AI failures, each with the layer that caught it" (`docs/lessons-log.md`).
3. **Proof, not promises** y, en pequeño, "Junction 2026 · Tieto — Earned Trust in AI Code" (sin enlace al repo).

**Voz (≈20 palabras).**
> "Trust isn't the AI being confident. It's evidence a person can check, and own. Proof, not promises."

---

## 4. Presupuesto de tiempo y de palabras

| # | Escena | Frames | Duración | Palabras de voz |
|---|---|---|---|---|
| 1 | Viernes por la tarde | 0–600 | 20 s | ~45 |
| 2 | Los problemas | 600–1050 | 15 s | ~50 |
| 3 | El comando | 1050–1350 | 10 s | ~30 |
| 4 | Triaje y evidencia | 1350–1950 | 20 s | ~50 |
| 5 | Fiscal/Defensor y paralelo | 1950–2700 | 25 s | ~60 |
| 6 | Lo que recibe el humano | 2700–3360 | 22 s | ~55 |
| 7 | Cierre | 3360–3600 | 8 s | ~20 |
| | **Total** | **3600** | **2:00** | **~310** |

~310 palabras a 150 por minuto son unos 2:04. **Recortes previstos**, por orden, si la voz no cabe:
1. La frase sobre el 98 % en la escena 1.
2. "And when an AI grades another AI…" en la escena 2; la tarjeta ya lo dice.
3. El inserto de #2283 (6b), solo el texto de voz; la imagen se queda.

**Nunca se recorta la escena 5** (paralelismo) ni la 6c (la firma): son las dos ideas del equipo.

---

## 5. Implementación en Remotion

### Estructura del proyecto (repo aparte o carpeta `video/`)

```text
video/
  package.json                  # remotion, @remotion/cli, @remotion/transitions, @remotion/google-fonts
  remotion.config.ts
  public/
    logos/{gemini,nvidia,modal}.svg   # de los kits de prensa oficiales
    voice/vo.mp3                       # voz en off montada
    music/bed.mp3
  src/
    Root.tsx                     # <Composition id="Demo" width={1920} height={1080} fps={30} durationInFrames={3600} />
    Demo.tsx                     # <Series> con las 7 escenas y <Audio> de voz y música
    data/video-data.json         # cifras generadas desde fixtures/ (ver abajo): nada se teclea a mano
    theme.ts                     # tokens de color y tipografía (§1)
    scenes/
      S1Friday.tsx  S2Problems.tsx  S3Command.tsx  S4TriageEvidence.tsx
      S5CrossExam.tsx  S6Owner.tsx  S7Close.tsx
    components/
      Character.tsx              # muñeco base: cuerpo + insignia (logo) + estados: idle | talk | type | stamp
      CodeStream.tsx             # cascada de líneas de diff (interpolate por frame)
      Terminal.tsx               # tecleo con cursor
      Funnel.tsx                 # embudo T3 → T1 → T2
      FileChips.tsx              # 237 fichas que caen a los cubos (spring por índice, con stagger)
      Sandbox.tsx                # caja de Modal con candado y resultado ✅/❌
      Mutant.tsx                 # gemelo con glitch
      Lanes.tsx                  # 5b/5c: fila única → cuadrícula paralela
      Clock.tsx                  # reloj acelerado con sello "cancelled" / "~17 min"
      ReportCard.tsx             # maqueta del informe con decisión, barra y contador
      SignOff.tsx                # tres listas + firma
      Caption.tsx                # subtítulos quemados
```

### Patrones clave

- **Animar todo con `useCurrentFrame()`**, más `interpolate`/`spring`, nunca con CSS animations: si no, el render no es determinista.
- **Stagger de las 237 fichas:** cada ficha `i` arranca en `start + i * 0.6` frames, y su destino depende de su cubo real.
- **Secuencial → paralelo (5b→5c):** la misma lista de 36 tarjetas.
  - En 5b, la posición es `x = laneStart + (frame - i * step)`, en una sola fila.
  - En 5c, cada tarjeta interpola hacia su celda de la cuadrícula con un `spring` y `delay = i % 12`.
  - Usar las mismas tarjetas hace que el salto se lea como "lo mismo, pero a la vez".
- **Muñecos:** una sola componente `Character` con props `{ badge, color, pose }`. Las poses son rotaciones y escalas sencillas de brazos y cabeza: no hace falta Lottie.
- **Subtítulos:** un array `{ from, to, text }` alineado con la voz. Lo más práctico es grabar la voz primero y sacar los tiempos de su transcripción.
- **Cifras desde los fixtures** (coherente con la tesis: nada inventado). Un script pequeño genera `video-data.json`:

  ```bash
  python -c "import json; t=json.load(open('fixtures/triage_2297.json')); m=json.load(open('fixtures/measure_2297_par_v1.json')); print(json.dumps({'files': len(t), 'wall_s': m['wall_s'], 'objections': m['objections'], 'sandboxes': m['sandboxes']}))" > video/src/data/video-data.json
  ```

### Comandos

```bash
npx create-video@latest video        # plantilla "Blank" con TypeScript
```

```bash
npx remotion studio                  # previsualizar y ajustar frames
```

```bash
npx remotion render Demo out/demo.mp4 --codec=h264 --crf=18
```

```bash
npx remotion still Demo out/thumbnail.png --frame=2600   # miniatura: la cuadrícula paralela
```

---

## 6. Comprobación final (antes de exportar)

- [ ] Dura **exactamente 2:00** (3600 frames).
- [ ] Cada cifra está en esta tabla y en `video-data.json`:
  - 237, 223/12/2 (`fixtures/triage_2297.json`);
  - 31 casos (`harness/corpus`);
  - más de 1 h en secuencia, cancelada (`docs/PROJECT-CONTEXT.md` §10);
  - ~17 min, 36 objeciones, 126 sandboxes, pico 16 y 0 errores 429 (`fixtures/measure_2297_par_v1.json`);
  - 2,86 $ (`docs/numeros-evidencia.md`);
  - 14 de 237 (Concept Card);
  - crash desplazado (`demo/2283-dotnet.html`);
  - 24 fallos (`docs/lessons-log.md`).
- [ ] Nada de "N× más rápido", y nada de "Modal encontró el crash" (ver "No decir" en [guion-demo-evidencia.md](guion-demo-evidencia.md)).
- [ ] El 98 % y "Alex Kim" están rotulados como ejemplo.
- [ ] Logos según las guías de marca (o el plan B de §2).
- [ ] Se entiende sin sonido: hay subtítulos y los veredictos llevan texto además de color.
- [ ] El humano toma la decisión final en pantalla: el vídeo nunca muestra a la IA aprobando.

---

## 7. Proyecto implementado (`video/`)

Las 7 escenas están construidas en Remotion 4.0.539 dentro de `video/`. Las cifras salen de `video/src/data/video-data.json`, que genera `python video/scripts/make_data.py` a partir de `fixtures/`. La objeción del Fiscal que aparece en pantalla es una pregunta real de la ejecución de #2297.

```bash
cd video && npm install
```

```bash
npx remotion studio
```

```bash
npx remotion render Demo out/demo.mp4 --codec=h264 --crf=18
```

**Pendiente para el montaje final:**
- **Voz:** grabar la voz en off con los textos de `video/src/timeline.ts`, dejarla en `video/public/voice/` y poner su ruta en `AUDIO` de `video/src/theme.ts`.
- **Subtítulos:** reajustar los tiempos a la voz grabada. Ahora se reparten por número de palabras, así que en la escena 4 el subtítulo de "evidence" llega antes que la imagen.
- **Logos:** los oficiales van a `video/public/logos/`, y se activan rellenando `LOGOS` en `video/src/theme.ts`. Hasta entonces, los personajes llevan su nombre como insignia (plan B).
- **Música:** opcional, en `AUDIO.music`.

## 8. Rediseño visual (versión actual)

La voz, los tiempos y las cifras son los mismos; cambia cómo se cuenta cada idea. Ya no hay cuadros de texto: cada idea es una metáfora animada.

| Escena | Metáfora | Transición de entrada |
|---|---|---|
| 1 | El Agente apila 237 hojas en una torre que deja diminuto a Alex; el revisor la barre con un haz de luz y proyecta un holograma "LGTM 98%" | — |
| 2 | Los cuatro problemas, como frases gigantes con pictogramas que se dibujan solos (documento sin fin, robots ante un espejo, velocímetro, firma en "?"); después, la pregunta palabra a palabra | Persianas |
| 3 | El terminal colapsa en una línea de luz que dibuja un embudo de neón de tres anillos (T1, T2, T3) | Iris |
| 4 | Tamiz: 237 partículas, un escáner de reglas estáticas y un Sankey hacia 223/12/2 · dos mundos BASE y PR que reciben el test · panal de 31 hexágonos cuyas mitades coinciden | Zoom a través del embudo |
| 5 | Juicio con focos: el argumento del Defensor se hace añicos y su test revienta al mutante (glitch) · cola de 36 cápsulas por una sola puerta, con el reloj hasta "cancelled" · la cola explota en un panal de 36 sandboxes | Barrido diagonal con filo de luz |
| 6 | Mosaico de 237 puntos del que saltan los 12 que necesitan ojos humanos · el crash que salta de una línea a otra del minimapa de `TypeCollector.cs` · firma manuscrita "Alex Kim" | Cortinas horizontales |
| 7 | Los 237 puntos convergen en una línea de luz y aparece el lema | Persianas que suben |

**Notas:**
- Lienzo oscuro tipo plano técnico, con verde azulado y azul verdoso como luz. Los veredictos siguen en verde, ámbar y rojo.
- Componentes nuevos: `Stage.tsx` (fondo, tipografía cinética y trazos que se dibujan) y `Reveal.tsx` (las seis transiciones). Las escenas se solapan 22 frames (`TRANSITION`) para que la siguiente entre por encima de la anterior.
- El minimapa de la escena 6 no reproduce código real: es una representación abstracta. Solo son reales los nombres de las excepciones, el fichero y la línea 1013.

### Escena 0 · Introducción (0:00–0:08, frames 0–240)

- **Qué se ve:** dos líneas de luz, "humans" (azul verdoso) y "AI agents" (verde azulado), avanzan y se cruzan con un anillo de luz en **"February 2026 · agents pass humans"**. La de los agentes se dispara hasta un contador **7.3T · AI agent tokens · August 2026**. Aparece la pregunta **"So who reviews all that code?"** y, por último, el título **Proof, not promises** con el subtítulo "Earned trust in AI code". La escena 1 entra con un iris.
- **Voz:** "AI agents now write more than humans: seven point three trillion tokens by August. So who reviews all that code?"
- **Fuente:** el apartado *Background* del enunciado del reto: OpenRouter, gráfico de a16z. En pantalla aparece como "Source: OpenRouter data, via a16z". Las curvas son esquemáticas: no tienen ejes ni valores y solo se rotulan los dos hechos del enunciado.
- **De dónde salen los 8 s:** 4 s del zoom final de la escena 1 (ahora 480 frames) y 2 s de cada una de las escenas 5 y 6, que ya habían terminado su animación. El total sigue siendo 3600 frames.
- **Voz de la escena 3:** pasa a "Our answer: one command, and one rule.", para no repetir el título justo después de la introducción.

## 9. Revisión (versión actual): 11 escenas sincronizadas con la voz

**Estructura (3600 frames):**

| Escena | Duración | Qué cuenta |
|---|---|---|
| Intro | 8 s | Curvas ya a media carrera en el primer fotograma, el cruce de febrero de 2026, 7.3T y la pregunta |
| Torre | 15 s | 237 hojas antes de que la voz diga la cifra; personajes más grandes y zoom lento (Ken Burns); el holograma "LGTM 98%" |
| Problemas | 9 s | En el orden de la voz, un solo estilo de icono (el pictograma) y una fila para "Who owns the merge?" |
| Comando + regla | 8 s | Comando rápido, embudo T1/T2/T3 y la regla a pantalla completa |
| Triaje y evidencia | 18 s | Sankey, dos mundos y panal de 31, cada parte entrando con su frase |
| Juicio y paralelo | 21 s | El Fiscal pregunta sobre `CompositeResolverTemplate.cs`; los relojes van a la par de la voz; **resultados reales: 12 ✓, 12 ✗ (posibles defectos) y 12 ?** |
| Mesa de Alex | 10 s | La misma torre se encoge, caen 12 tarjetas y aparece **REFUSED TO DECIDE** con la objeción abierta real (la misma pregunta del juicio) |
| Hallazgo | 12 s | El crash se mueve; **el holograma del 98 % vuelve, se agrieta y se pone rojo** (escape #2283); confianza **WITHDRAWN** |
| Informe real | 3 s | `public/report-2297.html`, el informe de esta ejecución, desplazándose hasta la firma |
| Firma | 10 s | 5 spot-checks reales elegidos por hash (los nombres salen del ledger), etiqueta del requisito y firma |
| Cierre | 6 s | Lema desde el primer fotograma, repositorio y equipo |

**Sincronía:**
- Cada animación se ancla al inicio de su frase en `src/data/voice-cues.json` (vía `src/cues.ts`).
- Ahora mismo esos tiempos vienen del borrador sintetizado (`scripts/make_voice.py`, voz Microsoft Zira).
- Con la voz definitiva grabada, solo hay que medir de nuevo los tiempos con el mismo formato.

**Audio:**
- Por decisión del equipo, el vídeo va de momento **sin voz y sin música**. `AUDIO` vale `null` en `src/theme.ts`, y los ficheros generados están en `.gitignore`.
- Solo suenan los efectos sintetizados de `scripts/make_sfx.py`: golpes, cristal roto, glitch, barridos, bolígrafo y tics de reloj.

**Trazabilidad:** la etiqueta "REQ · issue #2297" aparece en el embudo, en la tarjeta refused, en el informe y en la firma.

**Datos:** todas las cifras y textos salen de `fixtures/` y del ledger (`scripts/make_data.py`): los 36 resultados, la objeción abierta, los spot-checks y el equipo del README.

**Numeración unificada:**
- Etapas: **T1 Triage, T2 Evidence, T3 Cross-examination**, también en los informes, el README y la Concept Card.
- El veredicto de confianza retirada pasa de "T1" a "TR", para no chocar con la etapa T1.

## 10. Segunda revisión

**Tiempos:**

| Escena | Duración |
|---|---|
| Intro | 9,5 s, con entrada desde el fondo |
| Torre | 12 s |
| Problemas | 9 s |
| Comando + regla | 7 s |
| Triaje | 18 s |
| Juicio | 22 s |
| Mesa | 10 s |
| **Hallazgo** | **15 s** |
| Informe real | 3 s |
| Firma | 9 s |
| Cierre | 5,5 s |

**Hallazgo, separado en dos ideas:**
- **A · El revisor de IA clásico.** "Remember that ninety-eight percent? / On another PR, the AI fix only moved the crash. / Confident, and wrong." Vuelve el holograma LGTM 98 % junto al robot gris, el crash salta en el minimapa y el holograma se agrieta.
- **B · Nuestro sistema.** "Our own evidence missed it once too. / We logged it as an escape, and that area lost its trust." Nuestro ✓ GREEN sobre `TypeCollector.cs` pasa a ESCAPE, y la tarjeta de confianza pasa de **PROBATION** a WITHDRAWN. Es el estado real: esa área nunca tuvo la confianza ganada.

**Otros cambios:**
- **Comando:** "Our answer: one rule. / No model approves anything. Only executable evidence counts."
- **Cierre:** "AI reviews. Humans stay accountable. / Proof, not promises." El vídeo termina sobre el título, con el equipo en pequeño y sin enlace.
- **Torre:** sin zoom final, así que nada se sale del encuadre.
- **Juicio:** sello **REJECTED** sobre el bocadillo del Defensor antes de "No arguments. Only tests."
- **Informe real:** dos paradas con un recuadro de luz y zoom lento: la decisión ("Manual audit required") y el bloque de firma.
- **Firma:** los 5 spot-checks aparecen casi a la vez, y el nombre se escribe durante ~1,3 s nada más empezar la firma.
- **Subtítulos tipo karaoke:** la palabra que se está diciendo se resalta.
- **Informes regenerados** (`demo/*.html` y `video/public/report-2297.html`) con T1/T2/T3.

## 11. Tercera revisión

**Tiempos:**

| Escena | Duración |
|---|---|
| Intro | 7,5 s |
| Torre | 12 s |
| Problemas | 10 s |
| Comando | 7 s |
| Triaje | 18 s |
| Juicio + Modal | 23 s |
| Mesa | 10 s |
| Hallazgo | 15 s |
| Informe | 3 s |
| Firma | 10 s |
| Cierre | 4,5 s |

**Cambios:**
- **Firma:** gana 1 s del cierre; ya no es la escena más rápida.
- **Problemas:** "Who owns the merge?" se queda en pantalla con su frase antes de la transición.
- **Hallazgo:** la tarjeta de nuestro veredicto entra por la izquierda justo antes de "Our own evidence missed it once too", y el sello ESCAPE cae al empezar la frase. "It moved it." va unido con espacios duros.
- **Intro:** recortada en lo menos importante. La voz ya no lee "seven point three trillion tokens by August": la cifra se ve en pantalla.

**Modal, orientado a lo que valora su track** ("Modal does the heavy lifting"; sandboxes seguros para el código del agente; fan-out; todo en Python):
- **Voz:** "On Modal, every test runs at once, each in its own locked sandbox: seventeen minutes."
- **Panel "Powered by Modal"** en la parte paralela:
  - los sandboxes ejecutan todo el código escrito por IA, sin red;
  - un sandbox por ejecución (base, PR y mutante): 126 en abanico, pico de 16;
  - prueba de carga: 60 a la vez, 0 fallos;
  - imagen definida en Python (.NET 8 y 8 worktrees precompilados), sin Dockerfile;
  - 2,86 $ de cómputo en todo el hackathon.
- Los mundos BASE y PR se rotulan como "Modal sandbox".
- Todas las cifras salen de `fixtures/` (medición v1, barrido de capacidad y facturación).

## 12. Cuarta revisión (revisión de mensaje para el track)

**Honestidad:**
- **Hallazgo, parte A.** Ya no vuelve el revisor ficticio del 98 %: nunca existió un revisor que aprobara #2283. Ahora se ve la primera evidencia real de #2283 (test del cambio rojo→verde, invarianza 21/21), que es cierta pero no basta; el contrainterrogatorio encuentra el crash desplazado ("REAL FINDING · #2283 · found by cross-examination"). Voz: "On another PR, the first evidence was all green. / Then cross-examination tests showed the AI fix only moved the crash. / Green, and still wrong. / In another run, our evidence missed it. / We logged it as an escape, and that area lost its trust."
- **El 98 % de la escena 1** lleva el rótulo "illustrative example", y el holograma se separa del contador "FILES CHANGED".
- **Firma:** "signed by · named owner (example)" en vez de "approved by". "Alex Kim" es un nombre ficticio (lo propuso Claude al escribir el guion).
- **Invarianza:** 30 casos fuera del issue idénticos y 1 (el del propio issue) marcado ≠, "changed as asked". Voz: "across thirty cases". Coincide con el informe (30/30).
- **Paralelismo:** "One by one: 36 objections in one queue" (antes "36 tests through 1 sandbox"). Voz: "In parallel, every objection fans out to locked Modal sandboxes: seventeen minutes." El rótulo y el panel de Modal dan las cifras reales: 126 sandboxes, pico de 16 a la vez.
- **Triaje:** "risk: static rules, not a model · scope: Gemini reads the literal issue".
- **Mutante:** la línea real de los mutantes de esa objeción (`#if !NETSTANDARD2_0`, en `fixtures/report_2297_modal.json`), no una inventada.
- **Intro:** "AI agents now generate more tokens than humans", que es lo que muestra el gráfico.

**Claridad:**
- El panel de resultados del juicio lleva "36 objections · result of each", para no confundir el 12 de objeciones con el 12 de ficheros.
- `TransformUtilities.cs` pasa a una tarjeta destacada ("Nobody asked for this change · out of scope + high risk → red"), dentro del encuadre.
- **Cierre:** "Tested on 4 real AI-written PRs · same funnel for backend, frontend and security, with a different oracle".

**Pendiente:** grabar la voz con estos textos (`src/timeline.ts`) y volver a medir `src/data/voice-cues.json`. El karaoke se mantiene.
