# Proof, not promises

**A Risk-Scoped Evidence Ledger for AI-written code.** Junction 2026 · Tieto challenge *Earned Trust in AI Code*.

An AI agent changes hundreds of files and a human signs the approval. Reading every line is infeasible; trusting
the AI's own summary is negligent. We replace line-by-line review with a funnel where **no model approves anything
by argument**: trust comes only from executable evidence, and when the evidence is missing the system **refuses to
decide** and tells the human exactly what to look at.

We ran it on the four real AI-written pull requests of the challenge (MessagePack-CSharp #2283, #2234, #2129, #2297).

## What it found

- **#2283 — the AI fix moved the crash instead of removing it.** The change test (written by a model that only saw
  the issue) is red on base and green on the PR; generated code is identical outside the issue. A reviewer reading
  that would approve. Then the Prosecutor (Nemotron) raised edge cases, the Defender (Gemini) answered with tests,
  and those tests **failed on the PR**: for a generic type from another assembly with an invalid key, the generator
  still crashes (`IndexOutOfRange` became `InvalidOperation`) and the resolver is still not generated. Verdict: RED,
  with the exact failing test.
- **#2234 — RED for two real reasons.** The one-sentence issue produced a test that also passes on base, and the
  invariance check shows the fix changes behaviour **outside** the issue.
- **#2297 — 237 files.** At most 14 need human eyes: static rules rank 223 files as low risk and the passing evidence
  approves them unread. Generated code is identical everywhere after one **declared** normalization (the feature adds
  an attribute to all generated code), shown in the report. The scope check flagged one unrequested change:
  `TransformUtilities.cs` alters line breaks in generated code, which the issue never asks for.
- **#2129 — the AI's own test was wrong.** The system did not approve; the independent invariance oracle showed the
  feature works and pointed the human at the test.

**See the reports.** Clone the repo and open [`demo/index.html`](demo/index.html) in a browser: one self-contained
sign-off report per pull request, including the full #2283 runs (local dotnet and Modal) where the defect shows up.
They are rebuilt from the recorded runs in `fixtures/` with `python -m ledger.report.demo`.

## How it works

| Stage | Check | Models / tools |
|---|---|---|
| **T1 · Scope & risk** | Each file: in or out of the issue's scope × risk from static, auditable rules | Gemini flash + rules |
| **T2 · Executable evidence** | **Change test** written from the issue alone (never the diff): red on base, green on PR. **Generation invariance**: 31 snippets through the source generator in two isolated processes, base run twice; outside the issue, generated code and diagnostics must hash identically | Gemini / Nemotron · .NET 8 · Modal |
| **T3 · Cross-examination** | Up to 3 objections per high-risk file; each closes only with a test that passes on the PR **and fails against a mutant** | Nemotron (Prosecutor) vs Gemini (Defender) |
| **Trust · Track record** | Trust is earned per area from signed changes and withdrawn after an escape (green goes back to a human). Every report lists a deterministic sample of green files for a human to spot-check | Rules + `trust/track_record.json`, written only by people |

All AI-written code (change tests, Defender tests, mutants) can run in **Modal Sandboxes with no network**:
base, PR and mutant in parallel take 28 s vs 63 s sequential on a laptop; the 237-file PR runs end to end in 14–20 min
(over 1 h sequentially), for $2.86 of compute during the whole hackathon.

## Try it

**In seconds, no API keys, no .NET** (uses the recorded evidence in `fixtures/`):

```bash
python -m venv .venv && .venv/Scripts/python -m pip install -e ".[dev]"   # macOS/Linux: .venv/bin/python
.venv/Scripts/python -m ledger run --issue 2283 --fixtures --fake-runner  # → out/report-2283.html
.venv/Scripts/python -m pytest -q
```

**For real** (needs .NET SDK 8.0.4xx, the challenge repo cloned next to this one, and keys in `.env` — see `.env.example`):

```bash
git clone -c core.longpaths=true https://github.com/te-industry-tech-office/junction26-messagepack-csharp.git ../junction26-messagepack-csharp
python -m ledger run --issue 2283                        # full pipeline with dotnet on this machine
LEDGER_RUNNER=modal python -m ledger run --issue 2283     # AI-written code in network-less Modal Sandboxes
python -m ledger.evidence.regen --issue 2283              # regenerate the evidence, with provenance
python -m ledger.evidence.bench --issue 2283              # Modal (parallel) vs local (sequential)
python -m ledger.trust status                             # trust per area: escapes per approved file, how they were found
python -m ledger.trust record-change out/report-2283.json --owner "Full Name"   # after signing
```

## Read more

| Document | What's in it |
|---|---|
| [Concept Card](docs/concept-card.md) | Principles, decision matrix, measured trade-offs, limits |
| [Measured numbers](docs/numeros-evidencia.md) | Every timing and result, with its source |
| [Decision log](docs/decision-log.md) | Why static rules, isolated processes, issue-only tests, mutants, model diversity |
| [Lessons log](docs/lessons-log.md) | Every real AI failure we hit, and the funnel layer that caught it |
| [Architecture](docs/ARQUITECTURA.md) | The full design (Spanish) |
| Bounty write-ups | [Gemini & Nemotron](docs/bounty-forms.md) · [Modal](docs/bounty-form-modal.md) |
| Real reports | [demo/index.html](demo/index.html) (HTML, open locally) · recorded runs: `fixtures/report_2283_dotnet.json` (local), `fixtures/report_2283_modal.json` (Modal) |

## Honest limits

A badly written ticket gives weak evidence (#2234) — the system says so, it doesn't fix the ticket. It needs a
differential oracle (here: generated code + diagnostics). LLMs aren't reproducible run to run; the disk cache makes
the demo repeatable, not the models.

## Team

| Name | Role |
|---|---|
| **Víctor Verdú García** | Scope and risk triage, verdict matrix |
| **Martín Reboll Gómez** | Evidence engine: .NET test runner and generation invariance |
| **Javier de Paz Figueras** | Cross-examination (Prosecutor, Defender, mutants) and sign-off report; Concept Card, decision log and measured trade-offs |
| **Marco García López** | Independent change tests and Modal sandboxes; lessons log, demo video and live pitch |

Internal team notes (Spanish): [docs/TEAM.md](docs/TEAM.md), [docs/PERSONA-A.md](docs/PERSONA-A.md), [docs/PERSONA-B.md](docs/PERSONA-B.md).
