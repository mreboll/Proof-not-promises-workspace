# Contexto del proyecto (documento único de traspaso)

> **Para quien retome el proyecto (persona o sesión nueva de IA):** lee este documento entero antes de tocar nada.
> Resume dónde está todo, qué se ha hecho, qué se ha medido, qué falta y cómo hacerlo. Los detalles viven en los
> documentos enlazados; este es el mapa. Estado a **14/11/2026, ~08:25**, al cerrar la sesión de trabajo de la
> antigua Línea A. Desde ahora se trabaja **desde un solo sitio** (ya no hay reparto Línea A / Línea B).
> **El prompt para arrancar una sesión nueva está al final (§12).**

---

## 1. Qué es y a dónde queremos llegar

**Proof, not promises** — *Risk-Scoped Evidence Ledger*. Junction 2026, reto de Tieto **"Earned Trust in AI Code"**.
Repo público: `github.com/mreboll/Proof-not-promises`.

- **Problema:** un agente de IA cambia cientos de ficheros y una persona tiene que firmar la aprobación. Leerlo todo es
  inviable; fiarse del resumen de la IA es negligente.
- **Tesis:** ningún modelo aprueba nada con argumentos. La confianza solo sale de **evidencia ejecutable**; si falta,
  el sistema **se niega a decidir** y le dice al humano exactamente qué mirar.
- **Sujeto de prueba:** los 4 PR escritos por IA del reto sobre MessagePack-CSharp: **#2283, #2234** (bug fixes) y
  **#2129, #2297** (features). Ramas `origin/ju26-issue-<id>`; la base de cada una es `<rama>~1` (commit `32258fdb`).
- **Objetivo de la entrega:** repo público funcionando + informe HTML con bloque de firma + Concept Card + registros
  de decisiones y lecciones + **vídeo de 2:00** + **pitch de 3:00** + formularios de bounties (Gemini, NVIDIA
  Nemotron, Modal; CRACI opcional).

## 2. Estado en una tabla

| Qué | Estado |
|---|---|
| Pipeline de punta a punta (T3 → T1 → T2 → informe) | ✅ con dotnet local y con Modal |
| Evidencia real de los 4 issues | ✅ `fixtures/evidence_<id>.json` (#2129 pendiente de regenerar con `issue_id`) |
| Informe estrella de #2283 (crash desplazado) | ✅ `demo/2283-dotnet.html` |
| Etapa 3 en paralelo con Modal | ✅ **validada en real**: #2297 completo en **14–20 min** en 4 ejecuciones (antes >1 h), 36 objeciones, 0 errores 429, pico real 14–16 sandboxes; #2283 en 10,4 min. Límite medido (§5). Falta llevarla a `main` |
| Concept Card, README público, guiones, formularios | ✅ borradores revisados; falta pasada final de quien presenta |
| Vídeo y pitch | ❌ guiones listos, falta grabar/ensayar |
| CI | ⚠️ `runs-on: craci` se queda en cola; sin runner CRACI activo |
| Bloque de firma | ✅ qué se comprobó y con qué / qué NO y por qué / riesgo residual (`ledger/report/signoff.py`), en las 5 demos |
| Tests | ✅ **350 en verde**, sin red ni claves (`.venv/Scripts/python -m pytest -q`, ~65 s) |

**Ramas:** se trabaja **desde `main`** (unificada el 14/11 a las ~10:15 por avance rápido desde `a/evidence`, sin
reescribir nada). `a/evidence` y `b/triage-report` ya no aportan nada y se pueden borrar (pedir confirmación antes).

**Fuera del repo:** 115 respuestas del LLM sin seguimiento en `.cache/llm/` de la máquina de A (de las ejecuciones en
Modal); la demo no las necesita. Los resultados de las mediciones canceladas quedaron en una carpeta temporal y no valen.

## 3. Cómo funciona (mapa del código)

```
issues/<id>.md + git diff base→PR
 │
 ├─ Etapa 1 · Triaje (T3) ─ ledger/triage/      alcance IN/OUT con LLM (flash) × riesgo por reglas estáticas
 ├─ Etapa 2 · Evidencia (T1) ─ ledger/evidence/
 │     change_test.py  test del cambio escrito SOLO desde el issue (rol pro); rojo en base, verde en PR
 │     invariance.py   GeneratorProbe en base (×2) y PR: código generado + diagnósticos, SHA-256 por caso
 │     dotnet.py       DotnetTestRunner (local, worktrees en .work/)   ┐ mismo Protocol TestRunner
 │     modal_runner.py ModalTestRunner (sandboxes sin red)            ┘ LEDGER_RUNNER=local|modal
 │     trx.py · workspace.py · _proc.py · regen.py · bench.py
 ├─ Etapa 3 · Interrogatorio (T2) ─ ledger/crossexam/
 │     fiscal.py (Nemotron) · defensor.py (Gemini, solo {test_name, test_code}) · mutant_gen.py (Gemini)
 │     loop.py (≤3 rondas; válida = verde en PR + rojo contra mutante) · stage.py · concurrency.py
 ├─ Veredictos ─ ledger/verdict.py (matriz M1–M7, función pura)
 └─ Informe ─ ledger/report/ (render.py, templates/report.html.j2, demo.py → demo/*.html)

harness/GeneratorProbe  app .NET que se copia y compila DENTRO de cada worktree (cada lado carga su generador)
harness/corpus/*.cs     31 snippets (21 `general` + 10 `issue-<id>`), cabecera //@tag:, secciones //@library //@main
```

Descripción módulo a módulo de triaje, interrogatorio, veredictos e informe: [`docs/HANDOFF-B.md`](HANDOFF-B.md) §1–2.
Diseño original: [`docs/ARQUITECTURA.md`](ARQUITECTURA.md). Guía del motor de evidencia: [`docs/PERSONA-A.md`](PERSONA-A.md).

### Comandos

```bash
.venv/Scripts/python -m pytest -q                                          # 350 tests, sin red ni claves
.venv/Scripts/python -m ledger run --issue 2283 --fixtures --fake-runner   # segundos, sin claves ni .NET (sin Etapa 3)
.venv/Scripts/python -m ledger run --issue 2283                            # real, dotnet local (18–22 min)
LEDGER_RUNNER=modal .venv/Scripts/python -m ledger run --issue 2283        # real, Modal (11 min en secuencia)
.venv/Scripts/python -m ledger.evidence.regen --issue <id> [--runner modal] [--only-invariance]   # fixture con procedencia
.venv/Scripts/python -m ledger.evidence.bench --issue 2283                 # Modal paralelo vs local secuencial
.venv/Scripts/python -m ledger.evidence.capacity modal 1,8,32,60          # límite de concurrencia (también: llm pro / llm fiscal)
.venv/Scripts/python -m ledger.report.demo                                 # regenera demo/*.html desde fixtures
.venv/Scripts/python -m ledger.report.render <json> [--recompute] [--translate]
.venv/Scripts/python -m ledger.triage.scale <id>                           # triaje masivo con números
.venv/Scripts/python -m ledger llm-ping                                    # comprueba Gemini y Nemotron
```

## 4. Entorno (lo que hace falta para ejecutar de verdad)

- **Windows 11**, Git Bash/PowerShell. Python 3.14 en `.venv` (`pip install -e ".[dev]"`).
- **.NET SDK 8.0.4xx** (instalado 8.0.428; `global.json` pide 8.0.402 con `rollForward: patch`). La consola de dotnet
  sale en español: **nunca se parsea**; solo el `.trx` (si hay `.trx`, compiló).
- **Repo del reto** en `../junction26-messagepack-csharp`, clonado con `-c core.longpaths=true`.
- **`.env`** (no se sube; plantilla en `.env.example`): `GEMINI_API_KEY`, `NVIDIA_API_KEY`, modelos, `LEDGER_RUNNER`
  y los topes de concurrencia. **Modelos que funcionan:** `gemini-4-hydrogen` (pro, hasta ~215 s por llamada; timeout
  300 s), `gemini-3.8-flash` (flash); `gemini-2.5-*` da 404 con claves nuevas. Fiscal:
  `nvidia/nemotron-3.5-super-vl-120b-a12b`. `LEDGER_NVIDIA_FOR_ALL=0` siempre (D7: Fiscal y Defensor de familias distintas).
- **Modal:** token en `~/.modal.toml` (`modal token new`), workspace `rebollmartin`, plan Starter (100 contenedores
  simultáneos, 30 $/mes de créditos). **Usage limit = 30 $** puesto a propósito: cargos posibles = 0 $. Gastado hasta
  ahora: ~0,21 $ en créditos. La imagen (SDK 8 + 8 worktrees precompilados + caché de ReferenceAssemblies) tarda 5,5 min
  la primera vez y luego se reutiliza.
- **Caché del LLM** en `.cache/llm/` (se sube a git a propósito): clave = hash de modelo + prompt. Hace repetible la demo;
  cambiar un prompt invalida su caché.

## 5. Resultados reales (lo que se cuenta al jurado)

| Issue | Tipo | Test del cambio (solo desde el issue) | Invarianza (31 casos) | Lectura |
|---|---|---|---|---|
| #2283 | bug fix | ✅ rojo en base → verde en PR | ✅ 21 generales idénticos | Evidencia completa; la Etapa 3 encontró un defecto |
| #2234 | bug fix | ❌ pasa también en base (issue de una frase) | ❌ cambia `general-duplicate-int-keys-not-suppressed` | ROJO legítimo: el fix cambia comportamiento fuera del issue |
| #2297 | feature, 237 ficheros | ✅ verde en PR (y rojo en base) | ✅ tras la normalización **declarada** (`#if/[ExcludeFromCodeCoverage]/#endif`) | 223 ficheros de riesgo bajo aprobados por la evidencia; `TransformUtilities.cs` OUT/HIGH |
| #2129 | feature | ❌ falla también en PR (el test mira el fichero del resolver) | ✅ el formatter se genera | Falso rojo de la IA; la invarianza apunta al test |

- **El hallazgo estrella (#2283):** el fix escrito por IA **desplaza** el crash (`IndexOutOfRange` →
  `InvalidOperation` en `TypeCollector.cs:1013`) para un tipo genérico de otro ensamblado con clave inválida; el resolver
  sigue sin generarse. El test del cambio y la invarianza salían en verde. Reproducido aparte con GeneratorProbe.
- **Modal:** base + PR + mutante en **28 s en paralelo vs 63 s en secuencia local**, mismos resultados
  (`fixtures/bench_2283.json`). Pipeline completo de #2283: **11 min en Modal (secuencial)** vs 18–22 min local; 2 de 3
  objeciones validadas (`fixtures/report_2283_modal.json`).
- **Límite de concurrencia** (`ledger.evidence.capacity`): Modal escala sin fallos hasta 60 sandboxes; Gemini pro no
  da 429 hasta 48 y se hunde en 64; Nemotron sobrado hasta 32. Topes por defecto ahora **Gemini 32, Nemotron 16**
  (antes 8, que era el cuello de botella). El `.env` local no fija topes (usa estos por defecto) y tiene `LEDGER_RUNNER=modal`. Con estos topes el tiempo
  lo marca la cadena más lenta de llamadas largas a Gemini (hasta 300 s), no la concurrencia. El primer Defensor se
  pide a la vez que el mutante.
- Coste Modal total: **2,86 $** en créditos (`modal billing report --for "this month"`).
- **Optimización (D15, D16):** etapas 1 y 2 a la vez con Modal, triaje en paralelo, variantes del Defensor solo con cupo
  libre, y hedging (desactivado por defecto). Cuatro versiones medidas en `docs/numeros-evidencia.md`: a partir de
  ~17 min, la variación de latencia de Gemini pesa más que cualquier mejora. **Se paró de optimizar aquí a propósito.**
- Todas las cifras con su fuente: [`docs/numeros-evidencia.md`](numeros-evidencia.md). Números de la Etapa 1:
  [`docs/HANDOFF-B.md`](HANDOFF-B.md) §4.

## 6. Decisiones y lecciones

- [`docs/decision-log.md`](decision-log.md): D1–D14. Las que más se defienden: reglas estáticas para el riesgo (D1),
  invarianza de **generación** y no de bytes (D2), procesos aislados (D3), test escrito solo desde el issue (D4),
  mutantes (D5), Fiscal y Defensor de familias distintas (D7), código de IA en sandboxes sin red (D8).
- [`docs/lessons-log.md`](lessons-log.md): 16 fallos reales de la IA, cada uno con la capa que lo paró. Los mejores
  para el pitch: el crash desplazado (#2283), la aserción débil (#2234), el test del fichero equivocado (#2129) y el
  **falso "bug reproducido" por falta de red en el sandbox** (ahora se marca `INFRA` y nunca cuenta como evidencia).

## 7. Entregables

| Entregable | Dónde | Estado |
|---|---|---|
| README público (inglés) | `README.md` (las notas internas pasaron a `docs/TEAM.md`) | ✅ con equipo y roles |
| Informes para el jurado | `demo/index.html` + 5 informes | ✅ (#2129 se rehace tras Pendiente 3) |
| Concept Card | `docs/concept-card.md` | ✅ borrador revisado; pasada final pendiente |
| Guion vídeo 2:00 y pitch 3:00 | `docs/pitch-script.md` (+ `docs/guion-demo-evidencia.md`) | ✅ guion; ❌ grabación/ensayo |
| Formularios de bounties | `docs/bounty-forms.md` (Gemini, Nemotron), `docs/bounty-form-modal.md` | ✅; Modal se actualiza tras Pendiente 2 |
| Registro de decisiones y de lecciones | `docs/decision-log.md`, `docs/lessons-log.md` | ✅ |
| CI | `.github/workflows/ci.yml` | ⚠️ ver Pendiente 4 |

## 8. Pendientes, en orden (con instrucciones)

**1. ✅ HECHO (10:15): `a/evidence` unificada en `main`** por avance rápido. Queda opcional borrar las ramas
`a/evidence` y `b/triage-report` (confirmar antes).

**2. ✅ HECHO (10:00): #2297 y #2283 en paralelo medidos solos; cifras y conclusión en `docs/numeros-evidencia.md`.** Texto original: Solo está probada
con tests simulados. Una ejecución con Modal, Gemini y Nemotron reales puede destapar errores 429 de Gemini con 8
peticiones a la vez, problemas con muchos sandboxes simultáneos o condiciones de carrera.
```bash
LEDGER_RUNNER=modal GEMINI_MODEL_PRO=gemini-4-hydrogen timeout 7200 .venv/Scripts/python -m ledger.evidence.measure 2283 par <carpeta-temporal>
```
(~5–8 min estimados; caché del LLM nueva, así que mide el tiempo real). Guarda tiempo total, **pico real de sandboxes**
(`modal_runner.sandbox_stats()`), objeciones válidas y veredictos en `<carpeta>/2283-par/summary.json`. Referencia
"antes": #2283 en Modal en secuencia tardó **11 min** (con parte de la caché caliente). Si se quiere el ejemplo grande
para el pitch: `measure 2297 par` (estimado 10–20 min, frente a >1 h en secuencia). La medición `seq` con caché vacía es
opcional (comparación más limpia). Después, actualizar `docs/bounty-form-modal.md`, `docs/numeros-evidencia.md` y la
tabla de costes de `docs/concept-card.md` con **el pico real**, no el tope. Si aparecen 429, bajar
`LEDGER_MAX_CONCURRENT_GEMINI` (por defecto 8). Ejecutar las mediciones **una detrás de otra**, nunca a la vez.

**3. Fixture de #2129 con `issue_id` y regenerar la demo.**
```bash
.venv/Scripts/python -m ledger.evidence.regen --issue 2129 --only-invariance   # conserva el test del cambio
.venv/Scripts/python -m ledger.report.demo
.venv/Scripts/python -m pytest -q tests/test_report_demo.py
```
(`--only-invariance` reescribe el fixture con un bloque `provenance`; el test del cambio de #2129 lo escribió
`gemini-3.8-flash`. `2283-dotnet.html` necesita la traducción en caché o `GEMINI_API_KEY`.)

**4. CI.** `runs-on: craci` se queda en cola sin el runner de CRACI. Para el bounty: activarlo en el repo (admin).
Si no da tiempo: `runs-on: ubuntu-latest` (una línea). El CI corre `pytest` y el comando de fixtures, sin claves.

**5. Vídeo y pitch.** Guion completo en `docs/pitch-script.md`; abrir `demo/index.html`, `demo/2283-dotnet.html`,
`demo/2297.html` y `docs/lessons-log.md`. 2:00 es estricto: recortar el embudo, nunca la demo. **No ejecutar el
pipeline completo en directo**: enseñar informes ya generados; en directo, como mucho el comando de fixtures (segundos)
o el bench (~2 min). La sección "No decir" de `docs/guion-demo-evidencia.md` evita exagerar.

**6. Formularios y Concept Card.** Pasada final de quien presenta; actualizar cifras de Modal tras el Pendiente 2.

**7. Al final del hackathon: limpiar `.work/`** (worktrees compilados, varios GB). Desde `../junction26-messagepack-csharp`:
`git worktree list` y `git worktree remove --force <ruta>` para cada uno bajo `tieto-ledger/.work/`, luego
`git worktree prune`. Confirmar antes de borrar.

**8. Stash del usuario.** Hay un stash `usuario-modelos-gemini-locales-0640` (`afaf663…`) con cambios locales antiguos
de modelos en `config.py`/`.env.example`, superados por `3aba969`. Decidir si se descarta (`git stash drop`, tras
comprobar el índice con `git stash list`).

**Mejoras opcionales:** el triaje (Etapa 1) hace sus ~15 llamadas en secuencia (42 s en #2297; en paralelo serían ~5 s). Con más ficheros de riesgo alto que huecos (12), convendría que entrasen primero los que tocan API pública. (Lo de lanzar el mutante a la vez que el primer Defensor ya está hecho.)

## 9. Trampas conocidas (ya nos han pasado)

- **Runner local y paralelismo:** dos ejecuciones sobre el mismo worktree se pisan `Ledger/`. Por eso
  `parallel_enabled()` solo es cierto con `ModalTestRunner`; en local todo va en secuencia.
- **Filtro de tests:** `test_name` tiene que empezar por `Ledger` y el filtro es exacto (`FullyQualifiedName~X.`); si no,
  podría ejecutar tests existentes del repo y dar un verde falso.
- **Mutantes:** solo pueden tocar `src/**/*.cs` existentes (`mutant_patch_problem`); se normalizan a LF y se reintentan
  con `--ignore-whitespace`. En bash, el reintento va agrupado: `cd X && { A || B; }`.
- **Fallos de red/NuGet** en un test → `INFRA`, nunca evidencia. La imagen de Modal precalienta ReferenceAssemblies con
  `TMPDIR=/opt/ledger-tmp`.
- **Git Bash convierte rutas:** `git show origin/rama:ruta` falla; usar `MSYS_NO_PATHCONV=1`.
- **El LLM no repite respuestas:** dos ejecuciones dan objeciones distintas. La demo usa la caché/fixtures.
- **`ledger run` sobrescribe `out/report-<id>.*`**; `ledger.report.render <json>` escribe junto al JSON (no sobre `fixtures/`).
- **Procesos en segundo plano lanzados desde una sesión de IA** pueden quedar congelados si la sesión se pausa (un
  pipeline se quedó parado una hora; causa no confirmada). Envolver ejecuciones largas en `timeout`.
- **Modal Starter:** 100 contenedores simultáneos; tope configurable `LEDGER_MODAL_MAX_SANDBOXES=60`.
- **En Windows, `ps` de Git Bash no ve los `python.exe`:** usar `tasklist`. Por fiarse de `ps` se lanzaron dos mediciones a la vez (H8).
- **Contratos compartidos:** `ledger/models.py` es inmutable (pydantic frozen); `TestRunner` es un Protocol. Cambiarlos
  rompe fixtures y tests de las dos partes.

## 10. Ejecuciones en Modal de #2234, #2297 y #2129 (cerrado)

Se lanzaron con `LEDGER_RUNNER=modal`, Defensor/mutantes `gemini-4-hydrogen`, Fiscal Nemotron y la Etapa 3 **en
secuencia** (código anterior a `0f24606`). Resultado:

| Issue | Tiempo | Resultado |
|---|---|---|
| #2234 | 3,5 min | ✅ `fixtures/report_2234_modal.json`: `TypeCollector.cs` RED (la evidencia de la Etapa 2 falla, así que no hay Etapa 3) |
| #2297 | **cancelada** tras ~1 h | En secuencia interroga 12 ficheros de riesgo alto: más de 1 h. Se canceló para priorizar el paralelismo; su tiempo no servía de referencia (reaprovechaba caché de un intento anterior) |
| #2129 | no llegó a ejecutarse | La demo enseña #2129 sin Etapa 3, que es suficiente: lo importante de #2129 es la Etapa 2 |

Las mediciones con caché vacía (§8, Pendiente 2) también se cancelaron sin resultados válidos.

## 11. Índice de documentos

| Documento | Para qué |
|---|---|
| `README.md` | Presentación pública para el jurado (inglés) |
| `docs/PROJECT-CONTEXT.md` | **Este documento**: estado global y pendientes |
| `docs/HANDOFF-B.md` | Detalle de triaje, interrogatorio, veredictos e informe |
| `docs/PERSONA-A.md` / `docs/PERSONA-B.md` / `docs/TEAM.md` | Guías internas originales y reparto |
| `docs/ARQUITECTURA.md` | Diseño completo del embudo (v2.1) |
| `docs/numeros-evidencia.md` | Todas las cifras medidas, con fuente |
| `docs/concept-card.md` | Concept Card (inglés) |
| `docs/pitch-script.md` · `docs/guion-demo-evidencia.md` | Guiones de vídeo y pitch, preguntas del jurado, "no decir" |
| `docs/bounty-forms.md` · `docs/bounty-form-modal.md` | Textos de los formularios de bounties |
| `docs/decision-log.md` · `docs/lessons-log.md` | Decisiones (D1–D14) y fallos reales de la IA |
| `docs/TECH-CHALLENGES.md` | Bounties: requisitos y prioridades |
| `fixtures/` | Evidencia, triajes, informes reales y bench (lo que usa la demo) |

## 12. Prompt para arrancar una sesión nueva

Copiar y pegar tal cual en una sesión nueva de Claude Code abierta en la carpeta del repo (`tieto-ledger`):

```text
Retomamos el proyecto "Proof, not promises" (Junction 2026, reto de Tieto "Earned Trust in AI Code").
Ya no hay reparto por personas: trabajamos todo desde un solo sitio.

Antes de nada, lee docs/PROJECT-CONTEXT.md entero: es el documento de traspaso con el estado, el mapa del código,
los comandos, los resultados medidos, los pendientes en orden y las trampas conocidas. Si necesitas detalle de
triaje, interrogatorio, veredictos o informe, lee docs/HANDOFF-B.md. No re-derives lo que ya está decidido ahí
(docs/decision-log.md) salvo que encuentres un fallo real.

Entorno: Windows 11, Python en .venv (.venv/Scripts/python), .NET SDK 8.0.4xx, el repo del reto en
../junction26-messagepack-csharp, claves en .env (no se sube). Modal ya tiene token; el workspace tiene un tope de
uso de 30 $ (los créditos gratis): no lo cambies.

Reglas de trabajo:
- Comprueba primero que todo está en verde: .venv/Scripts/python -m pytest -q (296 tests, sin red ni claves).
- TDD donde haya lógica: el test primero y velo fallar. No hagas commit si algún test falla: comprueba el resultado
  de pytest antes de commitear, no encadenes "pytest | tail && git commit".
- Cada fallo real de una IA (también tuyo) va como una línea a docs/lessons-log.md, con la capa que lo paró.
- No toques ledger/models.py (contratos inmutables) sin explicar antes por qué.
- Pídeme confirmación antes de borrar algo, de hacer push a main o de cualquier acción difícil de deshacer.
- Las ejecuciones largas (pipeline completo, mediciones) en segundo plano, envueltas en timeout, y nunca dos a la vez
  contra Modal/Gemini. No ejecutes nunca el pipeline completo con el runner local en paralelo.
- Modelos que funcionan: gemini-4-hydrogen (pro), gemini-3.8-flash (flash), Nemotron
  nvidia/nemotron-3.5-super-vl-120b-a12b (fiscal). gemini-2.5-* da 404. LEDGER_NVIDIA_FOR_ALL siempre a 0.

Empieza por los pendientes de la sección 8, en orden:
1. Unificar a/evidence en main (fast-forward) — pídeme el OK antes del push a main.
2. Validar la Etapa 3 en paralelo con una ejecución real en Modal (ledger.evidence.measure 2283 par) y actualizar
   con el pico real de sandboxes docs/bounty-form-modal.md, docs/numeros-evidencia.md y docs/concept-card.md.
3. Regenerar el fixture de #2129 con issue_id y la demo (ledger.report.demo).
4. CI: decidir CRACI o ubuntu-latest.
Después, ayudar con el vídeo (2:00) y el pitch (3:00) usando docs/pitch-script.md, y con los formularios.

Al terminar cada pendiente, actualiza docs/PROJECT-CONTEXT.md (estado y pendientes) para que siga siendo el
documento de traspaso, y dime en una línea qué queda.
```
