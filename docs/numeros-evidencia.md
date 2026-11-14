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

## Coste

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
