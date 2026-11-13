# Persona A: motor de evidencia (.NET + ejecución)

> Puedes pegar esta guía entera como brief en tu sesión de Claude Code.

**Tu entrega:** la Etapa 2 del embudo (evidencia ejecutable) y la implementación real de `TestRunner`, que B usa en la Etapa 3.
**Solo tocas** `ledger/evidence/`, `harness/` y `fixtures/evidence_*.json`. Los contratos están en `ledger/models.py`; si necesitas cambiarlos, avisa a B.

## Datos del repo del reto (ya comprobados)

- Clon en `../junction26-messagepack-csharp`. En Windows hay que activar `core.longpaths=true`, porque si no, el checkout falla.
- SDK: **.NET 8.0.402** (`global.json`, rollForward `patch`).
- Ramas `origin/ju26-issue-{2283,2234,2129,2297}`. **La base de cada una es `<rama>~1`** (commit `32258fdb`).
- **Los 4 PR tocan el generador de código fuente y el analizador** (`src/MessagePack.SourceGenerator`), no el serializador en ejecución. Por eso, la "invarianza binaria" es en realidad una **invarianza de generación**: código generado más diagnósticos.
- Tests del generador en `tests/MessagePack.SourceGenerator.Tests` (net8.0). Usan `CSharpSourceGeneratorVerifier<MessagePackGenerator>` (en `Verifiers/`) y snapshots en `Resources/`. Para ver el patrón, mira `GenericsFormatterTests.cs`.

## Pasos

### 0. H0–2 · BLOQUEANTE: que compile
```bash
winget install Microsoft.DotNet.SDK.8      # comprobar luego: dotnet --list-sdks muestra 8.0.4xx
cd ../junction26-messagepack-csharp
git checkout origin/ju26-issue-2283
dotnet test tests/MessagePack.SourceGenerator.Tests --filter "FullyQualifiedName~GenericsFormatterTests"
```
- Si en 2 h no compila, prueba WSL o el contenedor `mcr.microsoft.com/dotnet/sdk:8.0` y avisa a B.
- Apunta en `docs/lessons-log.md` todo lo que haya fallado.

### 1. `ledger/evidence/workspace.py`
- `ensure_worktree(settings, issue_id, side) -> Path` crea `git worktree add .work/<issue>/<side> <ref>` usando `settings.ref(issue_id, side)`.
- Tiene que ser idempotente: si el worktree ya existe, se reutiliza.
- `disposable_worktree(...)` es un context manager para los mutantes: crea un worktree temporal y lo borra al salir.

### 2. `ledger/evidence/dotnet.py` → `DotnetTestRunner(settings, issue_id)`
- Implementa el Protocol `TestRunner` de `models.py`. La CLI ya lo importa por ese nombre.
- `run_tests(side, test_code, test_name)`:
  1. Escribe el test en `tests/MessagePack.SourceGenerator.Tests/Ledger/<test_name>.cs` dentro del worktree.
  2. Ejecuta `dotnet test ... --filter FullyQualifiedName~<test_name> --logger trx`.
  3. Parsea el `.trx` y devuelve un `TestRunResult`. Si la compilación falla, `build_ok=False`; la salida de error de compilación también hay que capturarla.
- `run_against_mutant(...)`: dentro de un worktree desechable, `git apply` del parche y luego `run_tests`.
- Pon un timeout en cada `subprocess.run` (por ejemplo, 15 min) y, si salta, devuelve un `TestRunResult` con `build_ok=False` y el motivo.

### 3. `harness/GeneratorProbe` + `ledger/evidence/invariance.py`
- `GeneratorProbe` es una app de consola net8.0 con `ProjectReference` a `src/MessagePack.SourceGenerator`. Se compila **dentro de cada worktree**, así cada proceso carga su propia versión.
- Corpus (`Corpus.cs` o `.cs` sueltos en `harness/corpus/`): unos 20 snippets etiquetados.
  - Casos `general`: int keys, string keys, unions, genéricos, enums, nullable, colecciones, tipos anidados…
  - Casos `issue-<id>`: los que reproducen cada issue. Para #2283, un tipo de **otro ensamblado** con problemas de keys.
- Por cada snippet: ejecutar `CSharpGeneratorDriver` y el analizador (`CompilationWithAnalyzers`), y escribir en `out/<case>.txt` las fuentes generadas ordenadas por `HintName` más los diagnósticos ordenados (`Id`, `Severity`, `Location.GetLineSpan()`).
- Desde Python:
  - Ejecutar la base dos veces y el PR una vez.
  - Calcular el SHA-256 por caso.
  - Construir `InvarianceEvidence`.
- **Normalización declarada para #2297:** quitar las líneas `[global::System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverage]` antes del hash del PR y anotarlo en `InvarianceCase.normalization`.

### 4. `ledger/evidence/change_test.py`
- Recibe **solo** `issues/<id>.md` (lo descarga B) y el ejemplo de test de `GenericsFormatterTests.cs` como plantilla de estilo. **Nunca el diff.**
- Usa `llm.complete(system, user, GeneratedTest, "pro")` (Gemini) con el esquema `{test_name, test_code}`. Es una de las piezas centrales del bounty de Gemini.
- Se ejecuta en base y en PR, y devuelve un `ChangeTestEvidence`. La regla de bug fix y feature ya está en `ChangeTestEvidence.ok`.
- Si no compila, se reintenta **una vez** pasándole el error de compilación al LLM. Si vuelve a fallar, se devuelve tal cual: será ROJO, "se niega a decidir".

### 4b. 🏆 Bounty Modal (prio 2): `ledger/evidence/modal_runner.py`
- `ModalTestRunner(settings, issue_id)` implementa el mismo `TestRunner` que `DotnetTestRunner`. La CLI lo usa con `LEDGER_RUNNER=modal`.
- La imagen es `mcr.microsoft.com/dotnet/sdk:8.0` con el repo clonado y `dotnet restore` hecho. Los tests generados por IA se ejecutan con `block_network=True`.
- Base, PR y mutantes van en sandboxes **en paralelo**. Mide el tiempo frente al local, porque es el dato para el jurado de Modal.
- El diseño y un snippet están en [TECH-CHALLENGES.md §2](TECH-CHALLENGES.md).
- **Si en el paso 0 .NET falla en Windows, empieza por aquí:** Modal pasa a ser tu runner principal.
- Comparte el parseo del `.trx` con `dotnet.py` mediante una función común; no lo dupliques.

### 5. Conectar con `pipeline.py` (H8, junto con B)
- Sustituye los `NotImplementedError` de `stage2_change_test` y `stage2_invariance` por llamadas a tus módulos.
- Sustituye `fixtures/evidence_2283.json` por la salida real.

### 6. H8–11
- #2234 de principio a fin.
- Limpieza de `.work/`.
- Medir los tiempos de build. Son el coste del concepto y van a la Concept Card.

## Definición de "hecho"
- `pytest` en verde, con tests de `invariance.py` (hashing y normalización) y del parseo de `.trx` usando un fixture de `.trx` real.
- `python -m ledger run --issue 2283` muestra el test del cambio rojo en base y verde en PR, `deterministic=true` y ningún caso `general` distinto.
