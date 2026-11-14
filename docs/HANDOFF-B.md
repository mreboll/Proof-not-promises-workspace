# Traspaso de la Línea B → A

Estado de todo lo que hizo la Línea B (triaje, interrogatorio, veredictos e informe), cómo funciona, qué queda
pendiente y cómo terminarlo. A partir de aquí **lo pendiente lo termina A**.

Estado al escribir esto (14/11/2026):

| Rama | Commit | Notas |
|---|---|---|
| `main` | `e1dfa4e` | Todo lo de B y todo lo de A **excepto** `0f24606` (Etapa 3 en paralelo) |
| `b/triage-report` | `e1dfa4e` | Igual que `main`. B no tiene nada sin subir |
| `a/evidence` | `0f24606` | Lleva un commit que aún no está en `main` (ver *Pendiente 1*) |

Tests: **284 en verde** en `main` (`.venv/Scripts/python -m pytest -q`, ~25 s, sin red ni claves).

---

## 1. Qué hace la Línea B, en una página

```
issues/<id>.md + git diff base→PR
        │
        ▼
 Etapa 1 · Triaje (T3) ─ ledger/triage/
   diff.py   → FileDiff por fichero (parse_diff pura + load_diff con git)
   rules.py  → riesgo LOW/MED/HIGH por reglas estáticas, sin LLM (rule_hits citan la línea)
   scope.py  → alcance IN/OUT con el LLM (rol flash), contra el texto LITERAL del issue
   stage.py  → triage_issue(): FileTriage por fichero
   scale.py  → triaje masivo + resumen con números (python -m ledger.triage.scale 2297)
        │
        ▼
 Etapa 2 · Evidencia (T1) ─ Línea A (ledger/evidence/)
        │
        ▼
 Etapa 3 · Interrogatorio (T2) ─ ledger/crossexam/
   fiscal.py     → Nemotron (rol fiscal): ≤3 objeciones testables
   defensor.py   → Gemini (rol pro): SOLO {test_name, test_code}, con la chuleta de Roslyn de A
   mutant_gen.py → Gemini (rol pro): {find, replace} sobre el código real; el diff lo hace difflib
   loop.py       → hasta 3 rondas por objeción: PR verde + mutante rojo = objeción válida
   stage.py      → judge_issue(): interroga IN/HIGH con evidencia ok y aplica la matriz a todo
        │
        ▼
 Veredictos ─ ledger/verdict.py (función pura, filas M1–M7)
        │
        ▼
 Informe ─ ledger/report/
   render.py + templates/report.html.j2 → out/report-<id>.html (+ .json)
   demo.py → demo/*.html para el jurado (python -m ledger.report.demo)
```

`pipeline.py` solo delega: `stage1_triage → triage.stage.triage_issue`, `stage3_and_verdicts →
crossexam.stage.judge_issue`, `render_report → report.render.render_report` (imports locales para no tocar
la cabecera compartida).

---

## 2. Módulo a módulo

### Etapa 1 · Triaje (`ledger/triage/`)

**`diff.py`**
- `parse_diff(text)`: pura. Modificados, añadidos, borrados, renombrados y binarios; quita CRLF y BOM.
- `load_diff(settings, issue_id)`: `git diff -M base pr` en `MSGPACK_REPO`, timeout 120 s, `DiffError` (es un
  `ValueError`, la CLI lo muestra limpio).
- `read_file_at(settings, issue_id, side, path)`: `git show ref:path` (lo usa el generador de mutantes).
- `FileDiff` vive aquí, no en `models.py`: no cruza la frontera A↔B.

**`rules.py`** (decision-log D1, D11)

| Regla | Riesgo | Qué detecta |
|---|---|---|
| R-LOW-01..05 | LOW | `tests/`, `.md`, `.csproj`, `.editorconfig`, snapshots `tests/**/Resources/**.g.cs` |
| R-MED-01 | MED | código en `src/` (`.cs`, `.tt`) |
| R-HIGH-01 | HIGH + `touches_public_api` | línea `public` añadida o quitada en `src/**/*.cs` |
| R-HIGH-02 | HIGH | `Span<`, `unsafe`, `stackalloc` |
| R-HIGH-03 | HIGH | `src/MessagePack.SourceGenerator/(CodeAnalysis\|Transforms)/` |
| R-DEFAULT | MED | ninguna regla encaja (por prudencia) |

- Riesgo = máximo de las reglas disparadas. Cada hit: `"<id>: <descripción> → +`línea``".
- Las reglas de línea solo miran `src/**/*.cs`, sin comentarios ni literales de cadena (si no, los
  `public async Task` de los tests y el texto de las plantillas `.tt` contarían como API pública).
- `SNAPSHOT_PATH` se comparte con `scope.py`.

**`scope.py`** (D10, D13, D14)
- `classify_scope(issue_text, fd)` → `(Scope, justification)`. Rol **flash**; issue y diff delimitados como
  datos no fiables (anti prompt injection). Diff recortado a 6000 caracteres.
- Snapshots `.g.cs`: **sin LLM**. IN si el issue habla del código generado, OUT si no (222 de 237 en #2297).
- Si flash no devuelve JSON válido → reintento con **pro**; si vuelve a fallar → **OUT "human review"**
  (lo que no se puede clasificar no se aprueba ni tumba el triaje). Visto en real: Nemotron Lightning devolvió
  el propio JSON Schema (lessons-log H4).
- `complete` es inyectable: los tests no gastan cuota.
- Justificaciones **en inglés** (el prompt lo pide).

**`stage.py`**: `triage_file` (reglas + alcance → `FileTriage`) y `triage_issue`.

**`scale.py`**: `python -m ledger.triage.scale <id>` → escribe `fixtures/triage_<id>.json` y
`out/scale-<id>.json` (ficheros, tiempo, llamadas al LLM, matriz alcance×riesgo, resultado de la Etapa 1).

### Etapa 3 · Interrogatorio (`ledger/crossexam/`)

- **`fiscal.py`**: rol `fiscal` (Nemotron 3.5 Super VL). Máx. `MAX_OBJECTIONS=3`, se cortan en código. Ve
  issue, diff y el resumen de evidencia (`verdict.evidence_lines`). Preguntas en inglés.
- **`defensor.py`**: rol `pro`. Esquema **solo** `{test_name, test_code}` (no puede argumentar). El nombre de
  clase lo fija el bucle (`Ledger_<id>_Objection<n>`). El prompt incluye `ROSLYN_GUIDE`, **importada** del
  `SYSTEM_PROMPT` de `ledger/evidence/change_test.py` desde `"- The file is compiled inside"` (si A cambia ese
  marcador, un test lo detecta).
- **`mutant_gen.py`**: el LLM da `{find, replace, explanation}` sobre el código real del PR; `build_patch` hace el
  diff con difflib, así que **siempre aplica**. `find` tiene que aparecer exactamente una vez; si es ambiguo, el
  error enseña cada aparición con contexto. `MAX_MUTANT_ATTEMPTS=3`. Ventanas de ±40 líneas alrededor de cada hunk.
- **`loop.py`**: `cross_examine(...)`. Por objeción: un mutante (sin ver el test) y hasta `MAX_ROUNDS=3` rondas
  del Defensor. Feedback: salida del build si falla en el PR; la *explicación* del mutante (nunca el parche) si el
  test pasa también contra él. Sin mutante no se gasta Defensor ni dotnet.
- **`stage.py`**: `judge_issue(...)`. Solo interroga IN/HIGH y solo si la evidencia de la Etapa 2 pasó. Si no puede
  ejecutarse (sin repo, sin clave, LLM caído) → **M7 con el motivo**; el pipeline nunca se cae. **Con
  `FakeTestRunner` la Etapa 3 no se ejecuta** (lessons-log H6: antes "validaba" objeciones sin ejecutar nada).

### Veredictos (`ledger/verdict.py`, D12)

| Fila | Alcance | Riesgo | Condición | Veredicto |
|---|---|---|---|---|
| M1 | OUT | HIGH | — | 🔴 |
| M2 | OUT | MED/LOW | justificación del agente | 🟡 |
| M3 | IN | cualquiera | falta evidencia, o falla test del cambio/invarianza | 🔴 |
| M4 | IN | LOW/MED | evidencia ok | 🟢 |
| M5 | IN | HIGH | todas las objeciones con test válido, sin `public` (o el Fiscal no objetó) | 🟢 |
| M6 | IN | HIGH | igual que M5 pero toca `public` | 🟡 |
| M7 | IN | HIGH | alguna objeción sin test válido, o sin interrogatorio | 🔴 "the system refuses to decide" |

- La primera razón empieza siempre por la fila (`"M4: ..."`).
- Si el test del Defensor **compila y falla en el PR** → "possible defect in the PR, check the test output".
- Si falla el test del cambio pero la invarianza está limpia (#2129) → pista "check the generated test before the code".
- Todas las razones están **en inglés**.

### Informe (`ledger/report/`)

- **`render.py`**: `render_html`, `write_report` (HTML + JSON al lado), `render_report` (punto de entrada del pipeline).
  - `python -m ledger.report.render <json> [--translate] [--recompute]`
    - `--recompute`: vuelve a aplicar la matriz actual a las entradas grabadas y refresca la redacción de las reglas por id.
    - `--translate`: traduce SOLO el texto escrito por los LLM (alcance, preguntas/razones del Fiscal) en una
      llamada, con aviso visible; si el modelo devuelve otro número de elementos, no toca nada.
  - `base_view`: la base se lee distinto en bug fix ("no reproduce el bug") y en feature ("red on base: the test measures something new").
  - `funnel`: la tira T3 → T1 → T2 con el resultado de cada etapa.
- **`templates/report.html.j2`**: autocontenido (sin CDN ni JS), imprimible, modo oscuro, en inglés. Orden:
  decisión con sello y barra de proporción → embudo → **"What you need to read"** (solo 🟡/🔴) → ficheros (los verdes
  plegados) → evidencia (test del cambio, invarianza, normalización declarada) → transcripción Prosecutor/Defender
  (salida desplegada si hay *possible defect*) → modelos por rol → firma.
- **`demo.py`**: `python -m ledger.report.demo` → `demo/index.html` + 5 informes:

| Informe | Fuente | Modelos que muestra |
|---|---|---|
| `2283-dotnet.html` | `fixtures/report_2283_dotnet.json`, traducido + recalculado | flash `gemini-3.5-flash`, pro `gemini-4-hydrogen`, fiscal Nemotron |
| `2283-modal.html` | `fixtures/report_2283_modal.json`, recalculado | los mismos |
| `2234.html` / `2297.html` / `2129.html` | `triage_<id>.json` + `evidence_<id>.json`; **sin Etapa 3** (aviso en el informe) | flash `gemini-3.8-flash`; pro = quien escribió el test del cambio; fiscal "not run" |

  Los modelos son los de **la ejecución que produjo cada informe**, no los del `.env` de quien regenera.

---

## 3. Cambios de B en ficheros compartidos

| Fichero | Cambio | Acordado con A |
|---|---|---|
| `pipeline.py` | cuerpos de `stage1_triage`, `stage3_and_verdicts`, `render_report` (imports locales) | sí (excepción pactada) |
| `config.py` | resumen de #2283 = título real; modelos por defecto `gemini-4-hydrogen` / `gemini-3.8-flash` | sí |
| `models.py` | `InvarianceEvidence.issue_id` (propuesta de A) | sí |
| `llm.py` / `llm_backends.py` | timeout 300 s (Gemini en ms vía `HttpOptions`, OpenAI en s); `_is_timeout` + `MAX_TIMEOUT_ATTEMPTS=2` | sí (petición de A) |
| `.env.example` | modelos de Gemini, `LEDGER_NVIDIA_FOR_ALL=0`, comentarios en inglés | sí |
| `tests/test_pipeline_fixtures.py` | doble del interrogatorio; lee el `.json` junto al `.html` | avisado |
| `README.md` / `docs/TEAM.md` | README público de A como principal; el de arranque → `docs/TEAM.md`; sección Team con nombres | sí |
| `docs/concept-card.md`, `README.md`, `docs/guion-demo-evidencia.md` | "static rules clear 223" → la evidencia los aprueba; hallazgo de `TransformUtilities.cs` | revisión pedida por A |

---

## 4. Números reales de la Línea B (para Concept Card, pitch y formularios)

Triaje con `gemini-3.8-flash` (fixtures actuales, justificaciones en inglés):

| PR | Ficheros | Llamadas LLM | Tiempo | Resultado de la Etapa 1 | Ojos humanos |
|---|---|---|---|---|---|
| #2283 | 4 | 4 | ~20 s | 2 OUT/LOW (docs), 1 IN/HIGH (`TypeCollector.cs`), 1 IN/LOW (tests) | 3 |
| #2234 | 4 | 4 | ~25 s | `TypeCollector.cs` **OUT/HIGH** (coherente con la diferencia de invarianza de A) | 3 |
| #2129 | 28 | 28 | ~130 s | 6 docs OUT, 9 HIGH (4 con API `public`) | 15 |
| #2297 | 237 | 15 | ~55 s | 223 IN/LOW, 12 IN/HIGH, 1 OUT/LOW (README), **1 OUT/HIGH (`TransformUtilities.cs`)** | ≤ 14 |

- `TransformUtilities.cs` (#2297): cambia `"{"` por `"{\r\n"` en el código generado; el issue no lo pide.
- Gemini flash frente a Nemotron Lightning en #2297: **57 s vs 214 s**, y **0 falsos positivos vs 2**.
- Defecto real en #2283 (ejecución de A con dotnet): el fix **desplaza** el crash
  (`IndexOutOfRange` → `InvalidOperation` en `TypeCollector.GetObjectInfo`); 2 objeciones con el test del Defensor
  fallando en el PR. En Modal: 2 de 3 objeciones validadas, 1 abierta.

Decisiones de B en `docs/decision-log.md`: **D10–D14**. Lecciones de B en `docs/lessons-log.md`: H1 (resumen
inventado de #2283), H3 (B sin TDD en `stage.py`), H4/H5 (fallos de Nemotron Lightning), H6 (runner falso).

---

## 5. Pendiente (lo termina A)

### Pendiente 1 · Llevar `0f24606` (Etapa 3 en paralelo) a `main` + escritura atómica de la caché

B revisó `0f24606`. Cumple: guard del runner falso, mutante especulativo descartado si el PR no sale verde, orden
determinista (`ordered_map`), semáforo fuera del backoff, tests de B sin tocar. **Falta una cosa:**

- **Escritura atómica de la caché en `llm.complete`**. Con varios hilos, uno puede leer un fichero de caché a medio
  escribir y fallar al validar el JSON. Arreglo propuesto (en `llm.py`, al final de `complete`):

```python
tmp = cache_file.with_suffix(f".{os.getpid()}.{threading.get_ident()}.tmp")
tmp.write_text(text, encoding="utf-8")
os.replace(tmp, cache_file)          # atómico en el mismo sistema de ficheros
```

  Test sugerido: escribir la caché desde varios hilos con el mismo prompt y comprobar que todas las lecturas validan.
- Opcional (más tiempo ahorrado): lanzar `make_mutant` a la vez que la primera ronda del Defensor; no dependen entre sí.
- Para llevarlo a `main`: `git checkout main && git merge --ff-only origin/a/evidence` (si `a/evidence` contiene
  `main`) y `git push origin main`.

### Pendiente 2 · Fixture de #2129 con `issue_id` y regenerar la demo

```bash
# tras regenerar fixtures/evidence_2129.json con issue_id:
.venv/Scripts/python -m ledger.report.demo        # reescribe demo/*.html con los fixtures actuales
.venv/Scripts/python -m pytest -q tests/test_report_demo.py
```

- `2283-dotnet.html` necesita una llamada a Gemini para traducir (está en la caché `.cache/llm/`; si se pierde,
  hace falta `GEMINI_API_KEY`).
- Si se añade o cambia un informe de la demo, editar `DEMOS` en `ledger/report/demo.py` (con los **modelos de esa
  ejecución**).

### Pendiente 3 · CI (CRACI o `ubuntu-latest`)

`.github/workflows/ci.yml` usa `runs-on: craci`; sin el runner de CRACI conectado al repo, el job se queda
"Queued" para siempre.
- Opción bounty: activar CRACI en el repo siguiendo su stand (necesita admin del repo).
- Opción rápida: cambiar a `runs-on: ubuntu-latest` (una línea) para que el CI salga en verde.
- El CI ejecuta `pytest` (sin claves) y `ledger run --issue 2283 --fixtures --fake-runner`, que es instantáneo y no
  llama a ningún LLM (la Etapa 3 se salta con el runner falso).

### Pendiente 4 · Vídeo (2:00) y pitch (3:00)

- Guion completo: `docs/pitch-script.md` (envuelve `docs/guion-demo-evidencia.md`). Frases en inglés.
- Abrir para grabar: `demo/index.html`, `demo/2283-dotnet.html`, `demo/2297.html`, `docs/lessons-log.md`.
- Cronometrar: 2:00 es estricto; si sobra texto, recortar el bloque del embudo, nunca la demo.
- La sección Team del README reparte roles entre los cuatro: quien lleve cada parte debe poder responder sobre ella.

### Pendiente 5 · Formularios de bounties

- Textos listos en `docs/bounty-forms.md` (Gemini y NVIDIA, inglés) y `docs/bounty-form-modal.md` (de A).
- Si la ejecución paralela en Modal da números nuevos (tiempo de #2297, pico real de sandboxes), actualizar el de Modal
  y la tabla de costes de `docs/concept-card.md`.

### Pendiente 6 · Concept Card

Borrador de A en `docs/concept-card.md`, ya revisado por B (cifras de la Etapa 1 correctas). Falta pasada final de quien
la presente.

---

## 6. Cosas que conviene saber (para no tropezar)

- **Modelos de Gemini**: `gemini-2.5-*` da 404 con claves nuevas. Los que funcionan: `gemini-4-hydrogen` (pro),
  `gemini-3.8-flash` (flash); también responde `gemini-3.5-flash`. Hydrogen puede tardar **hasta ~215 s** por llamada:
  el timeout es 300 s a propósito.
- **`LEDGER_NVIDIA_FOR_ALL=1`** manda pro y flash a Nemotron y rompe D7. Dejarlo en 0.
- **Caché del LLM** (`.cache/llm/`, se sube a git a propósito): la clave es el hash del prompt + modelo. Cambiar un
  prompt invalida su caché (hubo que regenerar el triaje al pasar a inglés).
- **Informes antiguos**: un JSON grabado con la redacción antigua se actualiza con `--recompute` sin inventar nada
  (la matriz es pura). El texto de los LLM en español se traduce con `--translate`, con aviso en el informe.
- **`render` y `demo` escriben donde se les dice**: `python -m ledger.report.render <json>` escribe junto al JSON
  (no ejecutarlo sobre `fixtures/`, o deja HTML ahí).
- **Comando rápido sin claves**: `python -m ledger run --issue 2283 --fixtures --fake-runner` → `out/report-2283.html`.
- **Tests de B**: `tests/test_triage_*.py`, `test_verdict.py`, `test_crossexam*.py`, `test_report*.py`,
  `test_llm_timeout.py`. Todos sin red.
