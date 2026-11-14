# Números del motor de evidencia (Línea A)

Datos **medidos** en esta máquina (Windows 11, .NET SDK 8.0.428) y en Modal, el 14/11/2026. Fuente de cada
cifra: `fixtures/evidence_*.json`, `fixtures/report_2283_dotnet.json` y `docs/lessons-log.md`.

## Resultado por issue (Etapa 2)

| Issue | Tipo | Test del cambio (escrito solo desde el issue) | Invarianza de generación | Lectura |
|---|---|---|---|---|
| #2283 | bug fix | ✅ rojo en base → verde en PR | ✅ 21/21 generales idénticos, determinista | Evidencia completa |
| #2234 | bug fix | ❌ pasa también en base (aserción débil; el issue tiene una línea) | ❌ cambia `general-duplicate-int-keys-not-suppressed` | ROJO legítimo: sin prueba del bug y el fix cambia comportamiento fuera del issue |
| #2297 | feature | ✅ verde en PR (y rojo en base: mide algo nuevo) | ✅ 30/31 idénticos tras la **normalización declarada**; solo cambia su propio caso | Evidencia completa, con la transformación a la vista |
| #2129 | feature | ❌ falla también en PR (el test elige el fichero del resolver) | ✅ 21/21 generales idénticos; el formatter se genera en PR | Falso rojo de la IA; la invarianza señala que el fallo está en el test |

Corpus: 31 snippets (21 `general` + 10 de issues), ejecutados en **dos procesos aislados** (base dos veces, PR una).

## Etapa 3 (#2283, ejecución completa con dotnet)

Fiscal `nvidia/nemotron-3.5-super-vl-120b-a12b`; Defensor y mutantes `gemini-4-hydrogen`.

- Objeción 1: test **verde en PR y rojo contra el mutante** → válida (el PR cubre esa rama).
- Objeciones 2 y 3: el test del Defensor **falla en el PR** → defecto real: el fix **desplaza** el crash
  (`IndexOutOfRangeException` → `InvalidOperationException`, `TypeCollector.cs:1013`) para un tipo genérico de
  metadata con clave inválida, y el resolver sigue sin generarse. Reproducido aparte con `GeneratorProbe`.
- Resultado: `TypeCollector.cs` ROJO, "el sistema se niega a decidir", con la pregunta exacta del Fiscal.

## Tiempos

| Qué | Local (Windows) | Modal |
|---|---|---|
| Primera compilación del repo (frío) | ~2 min | imagen: 5,5 min **una vez** (8 worktrees precompilados) |
| Un `dotnet test` del test generado (incremental) | 10–25 s | 20–30 s por sandbox |
| Base + PR + mutante (`python -m ledger.evidence.bench --issue 2283`) | 54–63 s en secuencia | **28–29 s en paralelo** (3 sandboxes sin red) |
| Invarianza (31 casos, base ×2 + PR) | 35–70 s | (en local) |
| Test del cambio con el LLM (incluye 2 ejecuciones dotnet) | 0,8–5,5 min | — |
| Pipeline completo #2283 con Etapa 3 | 18–22 min | **11 min** (`LEDGER_RUNNER=modal`; un primer intento se quedó parado, ver lessons-log) |

## Pipeline completo en Modal (#2283)

`LEDGER_RUNNER=modal`, mismos modelos. Todo el código escrito por IA (test del cambio, tests del Defensor y
mutantes) se ejecuta en sandboxes sin red. Test del cambio rojo en base y verde en PR; invarianza ok;
Etapa 3 con **2 de 3 objeciones validadas** contra su mutante y la tercera rechazada por la antitrampa (el test
pasaba también contra el mutante). Las preguntas del Fiscal no coinciden con las de la ejecución local:
los LLM no repiten respuestas y los prompts cambiaron a inglés. Informe: `fixtures/report_2283_modal.json`;
comparativa: `fixtures/bench_2283.json`.

## Pipeline completo en Modal con la Etapa 3 en paralelo (14/11/2026)

`python -m ledger.evidence.measure <issue> par <dir>` con caché del LLM vacía; topes Gemini 32, Nemotron 16, Modal 60.

| | #2297 (237 ficheros) |
|---|---|
| Tiempo total | **1024 s (17 min)**; en secuencia pasó de 1 h y se canceló |
| Interrogatorio | 12 ficheros, **36 objeciones**: 12 válidas, 12 con test que falla en el PR (posible defecto o test erróneo), 12 con test que también pasa contra el mutante |
| Veredictos | 223 M4 + 2 M5 verdes · 10 M7 (se niega a decidir) · `TransformUtilities.cs` M1 · `README.md` M2 |
| Modal | 126 sandboxes, **pico real 16** (tope 60), 0 fallos |
| Gemini | 131 peticiones, pico 32 (= tope), **0 errores 429**, 1 timeout (300 s), 39 s de espera por hueco en total |
| Nemotron | 12 peticiones (una por fichero), pico 12 |

Fuentes: `fixtures/measure_2297_par_v1.json`, `fixtures/report_2297_modal.json`. Lectura: el tope de Gemini se llegó a
llenar pero solo costó 39 s de espera; el tiempo lo marca la cadena más lenta de llamadas largas (hasta 300 s cada
una), no la concurrencia.

**#2283 en paralelo.** Medida limpia (sola, con variantes del Defensor, D15): **622 s (10,4 min)**; 0/3 objeciones
válidas y `TypeCollector.cs` rojo (`fixtures/measure_2283_par.json`). Referencia: 11 min en secuencia con parte de la
caché caliente. Las dos primeras mediciones se lanzaron por error a la vez y compartieron caché (447 s y 796 s;
`fixtures/measure_2283_par_overlap_{a,b}.json`, lessons-log H8): no valen como cifra, pero muestran que dos ejecuciones
del mismo PR dan resultados distintos (3/3 válidas en una, 1/3 en otra).

### Optimización de #2297: cuatro versiones, una ejecución cada una

| Versión | Tiempo | Objeciones válidas | Gemini: peticiones · errores · espera por hueco | Respaldos (útiles) | p90 de las respuestas |
|---|---|---|---|---|---|
| v1: topes 32/16 (`_v1`) | 1024 s (17,1 min) | 12/36 | 131 · 1 timeout · 39 s | — | 456 s |
| v2: + etapas 1 y 2 a la vez, triaje en paralelo, variantes adaptativas (D15) (`_v2`) | 1054 s (17,6 min) | 8/36 | 142 · 2 × 504 · 48 s | — | 396 s |
| v3: + hedging con la mediana por proveedor (`_v3`, lessons-log H9) | **833 s (13,9 min)** | 3/36 | 232 · 0 · 8983 s | 79 (6) | 595 s |
| v4: + hedging por modelo y solo con cupo libre (`_v4`) | 1192 s (19,9 min) | 6/36 | 195 · 6 × 504 · 449 s | 40 (4) | 591 s |

Fuentes: `fixtures/measure_2297_par_v{1,2,3,4}.json`.

**Conclusión (lo que se puede afirmar y lo que no):**
- Lo demostrado: subir el tope de Gemini de 8 a 32 quitó la cola (más de 1 h en secuencia frente a 17 min), y Modal
  nunca fue el límite (pico real de 14–16 sandboxes de 60).
- En #2297, el final lo marca **una llamada rezagada del Defensor**: en v2, el 90 % de las respuestas había llegado a
  los 396 s y la última llegó a los 1006 s.
- La variación de latencia de Gemini entre ejecuciones (p90 de 396 a 595 s; de 0 a 6 errores 504) es **mayor que el
  efecto de cada mejora**. Con una ejecución por versión no se puede atribuir la diferencia al código. Por eso el
  hedging queda **desactivado por defecto** (`LEDGER_HEDGE=1` lo activa): gasto de más sin beneficio probado.
- Las objeciones válidas oscilan entre 3 y 12 de 36. No sabemos si es ruido del LLM o rondas perdidas por 504.
- Para bajar de verdad el tiempo hace falta otra palanca: un modelo más rápido para el Defensor (a costa de calidad)
  o más cupo en el proveedor. Medirlo bien exigiría ~3 ejecuciones por versión (15–20 min y ~0,5 $ de Modal cada una).

## Límite de concurrencia (barrido de capacidad, 14/11/2026)

`python -m ledger.evidence.capacity <modal|llm pro|llm fiscal> <niveles>`: N trabajos idénticos a la vez por nivel, cada
recurso por separado. Fuentes: `fixtures/capacity_modal.json`, `fixtures/capacity_llm_pro.json`, `fixtures/capacity_llm_fiscal.json`.

| N a la vez | Modal: test real de #2283 (total / máx.) | Gemini pro `gemini-4-hydrogen`, ping (total / máx.) | Nemotron, ping (total) |
|---|---|---|---|
| 1 | 18,7 s / 18,4 s | 5,9 s | 4,3 s |
| 8 | 20,0 s / 19,7 s | 5,5 s | 1,3 s |
| 16 | 23,1 s / 22,5 s | 5,9 s | 1,3 s |
| 32 | 32,1 s / 30,9 s | 9,6 s / 9,2 s | 1,7 s |
| 48 | — | 11,8 s / 11,7 s | — |
| 60 / 64 | **27,4 s / 27,0 s (60)**, 0 fallos | **29,9 s / 29,2 s (64)**: el rendimiento cae a la mitad | — |

- **Modal no es el límite:** 60 sandboxes a la vez (pico real 60) terminan en 27 s sin un solo fallo: 131 ejecuciones/min frente a 3,2 con una.
- **Gemini pro es el techo:** ningún 429 en todo el barrido, pero a partir de 48 las peticiones se encolan en el
  proveedor y en 64 el rendimiento se hunde (243 → 129 por minuto). El ping mide concurrencia, no tokens: los prompts
  reales pesan mucho más, así que el tope por defecto queda en **32** (antes 8, que era el verdadero cuello de botella).
- **Nemotron** escala sin problema hasta 32; el Fiscal hace una llamada por fichero, así que el tope queda en **16**.
- Además, el primer Defensor se pide **a la vez** que el mutante (no lo ve): una llamada "pro" menos en el camino crítico de cada objeción.

## Coste

- Modal, total del hackathon a las 10:00 (`modal billing report --for "this month"`): **2,86 $ en créditos**, 0 $ de cargos. Antes:
- Modal: **0,13 $ en créditos** para construir la imagen dos veces, depurar y validar (tope de uso 30 $, sin cargos).
- LLM: con caché en disco por hash del prompt; repetir la demo no hace llamadas nuevas.

## Fallos de la IA que el embudo paró (detalle en `docs/lessons-log.md`)

| Fallo | Capa que lo paró |
|---|---|
| Nemotron se inventa la API de Roslyn (#2283) | T1: un test que no compila no cuenta |
| Aserción débil que pasa en base (#2234) | T1: en un bug fix, el test tiene que fallar en la base |
| Test que mira el fichero equivocado (#2129) | T1: un test que no pasa en el PR no cuenta; la invarianza apunta al test |
| El fix de #2283 desplaza el crash en vez de eliminarlo | T2: el test del Defensor falla en el PR |
| Un fallo de red se contaba como "bug reproducido" (sandbox sin red) | T1: los fallos de infraestructura se marcan `INFRA` y nunca son evidencia |
| El diseño del scaffold usaba `Sandbox.open`, que no existe en Modal 1.6.4 | Comprobar la API instalada antes de implementar |

## Límites conocidos (honestidad)

- La **invarianza** se ejecuta en local (el probe no pasa por el `TestRunner`); en Modal va todo el código escrito por IA.
- `InvarianceEvidence.unexpected_diffs` (contrato compartido) solo cuenta casos `general`: si un PR cambiara
  un caso de **otro** issue no se marcaría. En los cuatro PR no ocurre (comprobado); propuesta para `models.py`.
- El runner local ejecuta tests y mutantes de la IA **sin aislamiento** (por eso los mutantes se limitan a
  `src/**/*.cs`); para código no fiable, `LEDGER_RUNNER=modal`.
- Un issue mal escrito produce evidencia pobre (#2234): el sistema lo dice, no lo arregla.
