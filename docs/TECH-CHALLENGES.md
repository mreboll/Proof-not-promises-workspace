# Tech Challenges (bounties) sumados a Tieto

Son acumulables con el reto principal. Están ordenados por **valor esperado ÷ esfuerzo**, tomando los requisitos de la web de Junction.

| Prio | Bounty | Premio | Rol en el concepto | Dueño | Esfuerzo | Estado |
|---|---|---|---|---|---|---|
| **1** | **Gemini API** | **4.000 / 2.000 / 1.000 €** | Los agentes que **producen evidencia**: test independiente del issue, Defensor, mutantes y triaje de alcance | A + B | Ya incluido | ✅ `llm.py` roles `pro` y `flash` |
| **2** | **Modal** | **$2.000 en efectivo** + $3.000 en créditos | **Sandboxes** sin red para ejecutar tests escritos por IA, que son código no fiable. Además, base, PR y mutantes se ejecutan en paralelo | A | 3–4 h | ⏳ `ModalTestRunner` |
| **3** | **NVIDIA Nemotron** | RTX 5080 (gana 2 equipos) | El **Fiscal**. Al ser otra familia de modelos, acusación y defensa no comparten puntos ciegos | B | 1–2 h | ✅ `llm.py` rol `fiscal` · ⏳ prompts |
| **4** | **CRACI** | LEGO, Red Bull o comida con OpenAI en Slush | CI en `runs-on: craci`: la build registra qué entra en el software. Es la misma tesis aplicada a nosotros | B | 1 h | ✅ `.github/workflows/ci.yml` · ⏳ subir el repo a GitHub |
| **5** | **Entire** | Proyector portátil | Sessions, Graph y Trails como flujo de trabajo de equipo | Cualquiera | 1–2 h | ⏸ solo si sobra tiempo tras la H11 |

**Por qué este orden:**
- **Gemini:** da el mayor premio y ya es nuestro LLM.
- **Modal:** es el único con efectivo y **reduce nuestro mayor riesgo**, que .NET no compile en Windows, porque el contenedor trae el SDK 8.
- **Nemotron y CRACI:** cuestan poco.
- **Entire:** obliga a alojar el repo en su forja y el premio es pequeño.

**Para no pisarnos en el pitch:** Gemini y Nemotron hacen roles **distintos y visibles**, y los jurados de cada bounty piden que su modelo sea "central".

- **Gemini genera la evidencia:** los tests y los mutantes.
- **Nemotron la ataca:** como Fiscal.
- **Regla de diseño (D7):** el que acusa y el que defiende no pueden ser el mismo modelo.

---

Los textos listos para pegar en los formularios de Gemini y NVIDIA están en [bounty-forms.md](bounty-forms.md).

## 1. Gemini API

- **Uso visible:** en el informe, cada pieza de evidencia indica el modelo que la produjo (test del cambio: `GEMINI_MODEL_PRO`).
- **Qué mostrar:** la salida estructurada (`response_schema`), el agente que **solo ve el issue**, los mutantes generados y el triaje masivo con flash sobre 237 ficheros (número de llamadas y coste).
- **Entrega:** el mismo repo y la misma demo. En el formulario, explicar por qué Gemini es central: produce la evidencia de la que nace la confianza.

## 2. Modal (Persona A)

`ledger/evidence/modal_runner.py` → `ModalTestRunner(settings, issue_id)` implementa `TestRunner`. Se activa con `LEDGER_RUNNER=modal`.

```python
import modal

app = modal.App.lookup("tieto-ledger", create_if_missing=True)
image = (
    modal.Image.from_registry("mcr.microsoft.com/dotnet/sdk:8.0")
    .apt_install("git")
    .run_commands(
        "git clone -c core.longpaths=true https://github.com/te-industry-tech-office/junction26-messagepack-csharp /repo",
        "cd /repo && git fetch origin '+refs/heads/ju26-*:refs/remotes/origin/ju26-*'",
        # Calienta la caché de NuGet en la imagen para poder ejecutar luego SIN red
        "cd /repo && dotnet restore tests/MessagePack.SourceGenerator.Tests",
    )
)
sb = modal.Sandbox.create(app=app, image=image, timeout=1800, block_network=True)
with sb.open(f"/repo/tests/MessagePack.SourceGenerator.Tests/Ledger/{test_name}.cs", "w") as f:
    f.write(test_code)
proc = sb.exec("bash", "-lc", f"cd /repo && git checkout -q {ref} && dotnet test ... --filter ...", timeout=900)
proc.wait()
# proc.returncode, proc.stdout.read(), proc.stderr.read() → TestRunResult
sb.terminate()
```

- **Seguridad:** el test generado por IA corre **sin red** (`block_network=True`) y en un contenedor desechable. Es la frase para el jurado de Modal.
- **Paralelismo:** base, PR y cada mutante van en sandboxes simultáneos. Hay que medir el tiempo total frente al local.
- Comprobad la API exacta (`Sandbox.create`, `open`, `exec`) contra la documentación de Modal en el stand o en el Discord; el bloque de arriba es el diseño, no código probado.
- **Prerrequisito:** `modal token new` en cada portátil.

## 3. NVIDIA Nemotron (Persona B)

- Rol `fiscal` en `ledger/llm.py`, con la API compatible con OpenAI `https://integrate.api.nvidia.com/v1`.
- **Requisito del bounty:** usar **Nemotron 3.5 Super VL**. Hay que poner su ID exacto en `NVIDIA_MODEL`; el ejemplo `nemotron-3.5-lightning-30b-a3b` de la web **no vale**.
- La versión gratuita está limitada a unas 40 peticiones por minuto: el backoff ya está en `llm.py` y cada uno usa su clave.
- **Qué hacemos para mejorar su salida** (lo pide el formulario):
  1. Esquema JSON en el prompt, validado con pydantic, y **una reparación** pasándole el error.
  2. Se quitan los bloques `<think>`.
  3. Como máximo 3 objeciones, y cada una **tiene que** acabar en un test que falle contra un mutante. Si no, no cuenta. Es un bucle de feedback objetivo.
- **Opcional VL:** pasarle el diagrama del embudo o una captura del informe para que audite la explicación. Solo si sobra tiempo.
- **Formulario (texto):** modelo usado, qué hace (Fiscal), por qué importa (diversidad de modelos frente a errores correlacionados) y cómo mejoramos su salida (los 3 puntos de arriba).

## 4. CRACI (Persona B)

1. Crear el repo en GitHub y subir `main`.
2. El workflow ya usa `runs-on: craci`. Hay que instalar o activar CRACI en el repo, siguiendo lo que diga su stand.
3. **Stretch, conectado con la tesis:** consultar la API de CRACI y añadir al informe una línea del tipo "dependencias de esta build: N, vulnerabilidades: M".

## 5. Entire (opcional)

- Requiere alojar el repo en Entire, que puede ser un segundo remoto, y usar Sessions, Graph y Trails.
- **Hilo narrativo:** Trails pregunta "¿coincide con la intención?", que es exactamente nuestra Etapa 1. Podríamos mostrar nuestro informe como revisión de un Trail.
- Hacerlo solo después de la H11.
