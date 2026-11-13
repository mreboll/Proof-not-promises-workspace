# Persona B: triaje, interrogatorio e informe (Python + Gemini)

> Puedes pegar esta guía entera como brief en tu sesión de Claude Code.

**Tu entrega:**
- Etapa 1 (alcance y riesgo).
- Etapa 3 (Fiscal y Defensor).
- La matriz de veredictos.
- El informe HTML con el bloque de firma.
- El análisis de escala sobre el PR de 237 ficheros.

**Solo tocas** `ledger/triage/`, `ledger/crossexam/`, `ledger/verdict.py`, `ledger/report/`, `issues/` y `fixtures/triage_*.json`.

**No necesitas .NET:** trabaja con `ledger.fakes.FakeTestRunner` y `fixtures/evidence_2283.json` hasta la integración de la H8.

## Datos del repo del reto (ya comprobados)

- Base = `<rama>~1`. Diff de cada PR: `git -C ../junction26-messagepack-csharp diff origin/ju26-issue-2283~1 origin/ju26-issue-2283`.
- Ficheros por PR: #2283 = 4, #2234 = 4, #2129 = 28, #2297 = 237 (casi todos snapshots `.g.cs` en `tests/MessagePack.SourceGenerator.Tests/Resources/`).
- El código de los cambios vive en `src/MessagePack.SourceGenerator/` (el generador y el analizador).

## Pasos

### 0. H0–1
- Descarga el texto de los 4 issues a `issues/<id>.md` con el formato `# #<n>: <título>` + cuerpo. Desde la IP del hackathon, la API de GitHub sin autenticar da *rate limit*; usa `gh issue view <n> -R MessagePack-CSharp/MessagePack-CSharp` o cópialos del navegador.
- A los necesita para el agente de tests independiente.

### 1. `ledger/triage/diff.py`
- `load_diff(settings, issue_id) -> tuple[FileDiff, ...]` usa `git diff <base> <pr>` y `unidiff`.
- Cada `FileDiff` es frozen y contiene el path, los hunks, las líneas añadidas y las quitadas.

### 2. `ledger/triage/rules.py`, sin LLM y 100 % auditable
- Es una tabla declarativa de reglas `Rule(id, risk, description, path_regex | added_line_regex)`.
- El riesgo final de un fichero es el máximo de las reglas que se disparan, y cada regla disparada va a `FileTriage.rule_hits`.

| Nivel | Reglas |
|---|---|
| LOW | `tests/`, `.md`, `.csproj`, `.editorconfig`, snapshots `Resources/**.g.cs` |
| MED | `private` o `internal` en `src/` |
| HIGH | Línea añadida o quitada con `public` (firma) → `touches_public_api=True`; `Span<`, `unsafe`, `stackalloc`; namespace núcleo (`src/MessagePack.SourceGenerator/CodeAnalysis`, `Transforms`) |

### 3. `ledger/triage/scope.py`
- `classify_scope(issue_text, file_diff) -> (Scope, justification)` con `llm.complete(system, user, ScopeAnswer, "flash")` (Gemini flash).
- Para no gastar tokens, los ficheros **LOW** de snapshots `.g.cs` no pasan por el LLM: se marcan IN si el issue habla del código generado. Documenta esta decisión en `decision-log`.

### 4. `ledger/verdict.py`, función pura y con un test por fila
Implementa las tablas §2 y §3 de [ARQUITECTURA.md](ARQUITECTURA.md):

| Alcance | Riesgo | Evidencia e interrogatorio | Veredicto |
|---|---|---|---|
| OUT | HIGH | — | 🔴 |
| OUT | MED o LOW | — | 🟡 con justificación |
| IN | cualquiera | Falla el test del cambio o la invarianza | 🔴 |
| IN | LOW o MED | Evidencia ok | 🟢 |
| IN | HIGH | Todas las objeciones válidas, sin `public` | 🟢 |
| IN | HIGH | Todas las objeciones válidas, con `public` | 🟡 |
| IN | HIGH | Alguna objeción sin test válido | 🔴 "se niega a decidir", con la pregunta del Fiscal |

### 5. `ledger/crossexam/`
- **`fiscal.py`:** 🏆 bounty Nemotron (prio 3).
  - Llama a `llm.complete(system, user, Objections, "fiscal")`, que va a **NVIDIA Nemotron 3.5 Super VL**.
  - Recibe el fragmento, el issue y la evidencia, y devuelve como máximo 3 objeciones (`null`, buffers vacíos, genéricos anidados, tipos de otro ensamblado, compatibilidad…).
  - `llm.py` ya inyecta el esquema en el prompt, quita los bloques `<think>` y repara el JSON una vez.
  - Guarda en el informe qué modelo hizo cada papel.
- **`defensor.py`:** usa `llm.complete(..., "pro")` (Gemini) y devuelve **solo** `{test_name, test_code}`. Nunca texto argumentativo.
- **`mutant_gen.py`:** usa `llm.complete(..., "pro")` (Gemini) y genera un diff unificado que rompe el caso límite en el código del PR.
- **`loop.py`:** para cada objeción, hasta 3 rondas de `runner.run_tests("pr", ...)` y `runner.run_against_mutant(...)`. Construye la `Objection`; su campo `valid` ya implementa la regla antitrampa.
- Hay que testear con `FakeTestRunner` que un `Assert.True(true)` se rechaza.

### 6. `ledger/report/render.py` + `templates/report.html.j2`
Un HTML estático e imprimible con:
- Cabecera: issue, tipo, rama y commits.
- Contador 🟢/🟡/🔴.
- Una tabla por fichero.
- La evidencia: test del cambio en base y PR, y tabla de hashes.
- La transcripción del interrogatorio.
- El **bloque de firma** de §3.

Sustituye el `render_report` de `pipeline.py`, que hoy vuelca JSON.

### 6b. 🏆 Bounty CRACI (prio 4, 1 h): en cuanto exista el repo
- Crear el repo en GitHub y subir `main`. El workflow `.github/workflows/ci.yml` ya usa `runs-on: craci`.
- Activar CRACI en el repo siguiendo lo que indique su stand y comprobar que el job sale en verde.
- **Stretch:** leer la API de CRACI y añadir al informe "dependencias de esta build: N, vulnerabilidades: M".

### 7. H8–11: escala
- Etapa 1 sobre #2297 con los números reales: cuántos ficheros 🟢/🟡/🔴, el tiempo y las llamadas al LLM.
- Es la diapositiva de "escala" del pitch.

## Definición de "hecho"
- `pytest` en verde, con tests de `rules.py` (diffs de fixture), de cada fila de `verdict.py` y del rechazo de tests triviales.
- `python -m ledger run --issue 2283 --fixtures --fake-runner` genera `out/report-2283.html` con el bloque de firma.
