# tieto-ledger: Risk-Scoped Evidence Ledger

Junction 2026, reto de Tieto *Earned Trust in AI Code*. El diseño está en [docs/ARQUITECTURA.md](docs/ARQUITECTURA.md). Ojo: su "invarianza binaria" se convirtió en **invarianza de generación**; el motivo está en [docs/decision-log.md](docs/decision-log.md), D2.

## Puesta en marcha (los dos)

```bash
# 1. Repo del reto, al lado de este (con rutas largas activadas en Windows)
git clone -c core.longpaths=true https://github.com/te-industry-tech-office/junction26-messagepack-csharp.git ../junction26-messagepack-csharp

# 2. Python
py -3 -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"
cp .env.example .env        # y pon tu GEMINI_API_KEY

# 3. Comprobaciones
.venv/Scripts/python -m pytest -q
.venv/Scripts/python -m ledger llm-ping
.venv/Scripts/python -m ledger run --issue 2283 --fixtures --fake-runner
```

## Quién hace qué

| Persona | Guía | Carpetas propias |
|---|---|---|
| A: motor de evidencia (.NET) | [docs/PERSONA-A.md](docs/PERSONA-A.md) | `ledger/evidence/`, `harness/`, `fixtures/evidence_*.json` |
| B: triaje, interrogatorio e informe | [docs/PERSONA-B.md](docs/PERSONA-B.md) | `ledger/triage/`, `ledger/crossexam/`, `ledger/verdict.py`, `ledger/report/`, `issues/`, `fixtures/triage_*.json` |
| Los dos (avisar antes de tocar) | | `ledger/models.py`, `ledger/llm.py`, `ledger/config.py`, `ledger/pipeline.py` |

Ramas: `a/evidence` y `b/triage-report`. Hay que hacer merge a `main` como mínimo en la H5 y en la H8.

## Hitos

| Hora | Hito |
|---|---|
| H5 | B hace el triaje real de #2283; A tiene el test del cambio rojo en base y verde en PR |
| **H8** | `python -m ledger run --issue 2283` funciona de principio a fin con dotnet real |
| H11 | Feature freeze: #2234 funcionando y números reales de #2297 |
| H11–14 | Docs, vídeo de 2:00 y pitch de 3:00 |

Cada vez que la IA os falle, apuntad una línea en [docs/lessons-log.md](docs/lessons-log.md).

## Tech Challenges (bounties)

Detalle, requisitos de entrega y responsables en [docs/TECH-CHALLENGES.md](docs/TECH-CHALLENGES.md).

| Prio | Bounty | Dueño | Cuándo |
|---|---|---|---|
| 1 | Gemini API (4.000 €) | A + B | Ya incluido (roles `pro` y `flash`) |
| 2 | Modal ($2.000) | A | Tras el paso 2 de A (H5–H8); es también el plan B si .NET falla en Windows |
| 3 | NVIDIA Nemotron (RTX 5080) | B | Con el Fiscal (H5–H8); rol `fiscal` ya cableado |
| 4 | CRACI | B | En cuanto exista el repo en GitHub (1 h) |
| 5 | Entire | Cualquiera | Solo después de la H11 |

`python -m ledger llm-ping` comprueba Gemini **y** Nemotron.
