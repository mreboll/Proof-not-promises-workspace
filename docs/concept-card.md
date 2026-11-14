# Concept Card — Proof, not promises

**Risk-Scoped Evidence Ledger** · Junction 2026 · Tieto challenge *Earned Trust in AI Code*
Tested on four real AI-written pull requests to MessagePack-CSharp (#2283, #2234, #2129, #2297).

> **Borrador de la Línea A.** Los números son reales (fuentes en `docs/numeros-evidencia.md`); el texto de
> negocio (problema, quién firma, ahorro) está para que lo ajuste quien lleve la Concept Card.

## The problem

An AI agent changes hundreds of files; a human signs the approval. Reading everything is infeasible, and trusting
the AI's own summary is negligent. The question is not "is the code good?" but **"what evidence lets a person sign
without reading every line?"**

## Principles

1. **Proportional, deterministic risk.** Static, auditable rules (paths, `public` signatures, core namespaces)
   decide how much scrutiny a file gets. Never a model's intuition. Same diff, same risk.
2. **Evidence over eloquence.** No model approves anything by argument. Trust comes only from executable checks.
3. **Disagreement only produces tests.** The Defender cannot answer the Prosecutor with text, only with a test that
   passes on the PR **and fails against a mutant**. Otherwise the system **refuses to decide** and a human signs.

## The funnel

| Stage | What it does | Who / what |
|---|---|---|
| **T3 Scope & risk** | Each file: in or out of the issue's scope (LLM, judged against the literal issue) × risk by static rules | Gemini flash + rules |
| **T1 Executable evidence** | (a) A **change test** written by an agent that sees only the issue, never the diff: must fail on base and pass on PR. (b) **Generation invariance**: a corpus of 31 snippets through the source generator in two isolated processes; outside the issue, generated code and diagnostics must hash identically (base run twice for determinism) | Gemini/Nemotron + .NET + Modal |
| **T2 Cross-examination** | High-risk, in-scope files: up to 3 Prosecutor objections, each answered only by a Defender test validated against a mutant | Nemotron (Prosecutor) vs Gemini (Defender) |

## Decision matrix

| Outcome | When | The human |
|---|---|---|
| 🟢 **Green** | In scope, low/medium risk, evidence passed — or every objection closed by a valid test | Reads a summary of claims and hashes, **not the code** |
| 🟡 **Yellow** | Out of scope but low/medium risk with justification, or a `public` signature after a passed cross-examination | Reviews only that file or signature |
| 🔴 **Red** | Out of scope and high risk, a differential failure, or the system refuses to decide | Audits the exact lines plus the unresolved question |

## What it found on real AI-written PRs

- **#2283 (bug fix):** change test red on base, green on PR; 21/21 general cases identical. Then the Prosecutor's
  questions led to Defender tests that **failed on the PR**: the AI fix *moved* the crash
  (`IndexOutOfRange` → `InvalidOperation`) for a generic type from another assembly with an invalid key, and the
  resolver is still not generated. Change test and invariance were green — a reviewer reading only those would have
  approved it.
- **#2234 (bug fix):** RED, for two real reasons: the one-sentence issue produced a test that also passes on base,
  and the invariance shows the fix changes behaviour **outside** the issue (duplicate keys without the option).
- **#2297 (feature, 237 files):** static rules rank 223 in-scope files as low risk (222 of them generated snapshots,
  scoped by rule with no LLM call), and the passing evidence approves them without anyone reading them; invariance
  identical everywhere except its own case, after one **declared** normalization shown in the report. The scope check
  also caught an **unrequested change**: `TransformUtilities.cs` alters line breaks in the generated code, which the
  issue never asks for (out of scope, high risk → red).
- **#2129 (feature):** the AI's own test was wrong (false red); the independent invariance oracle showed the feature
  worked and pointed the human at the test.

## Trade-offs (measured)

| Cost | Value |
|---|---|
| One test run (incremental build) | 10–25 s local · 20–30 s per Modal sandbox |
| Base + PR + mutant | 63 s sequential local · **28 s parallel on Modal** |
| Invariance, 31 cases | 35–70 s |
| Full pipeline with cross-examination (#2283) | 18–22 min local · **11 min on Modal** |
| Scope triage of a 237-file PR | 57 s, 15 Gemini calls |
| Modal compute for the whole hackathon | **$0.21** in credits |

Against that: on the 237-file PR, static rules rank **223** files as low risk and the passing evidence approves them
unread; **12** high-risk files go to cross-examination and stay with a human until every objection is closed by a
valid test; the **2** out-of-scope files go straight to a human (one yellow, one red). At most **14 of 237** files
need human eyes. On #2283 the human gets **the unresolved questions with the exact failing tests**. We did not
measure reviewer time; we measured where the reading goes.

## Limits (honest)

- **A badly written ticket gives weak evidence** (#2234). The system says so; it does not fix the ticket.
- **It needs a differential oracle.** Here it is "generated code + diagnostics"; areas without one get less.
- **LLMs are not reproducible run to run**; the disk cache makes the demo repeatable, not the models.
- The invariance check runs locally; AI-written code runs isolated only with `LEDGER_RUNNER=modal`.
- Every AI failure we hit is in `docs/lessons-log.md`, each tied to the funnel layer that caught it.

## Reproduce

```bash
python -m ledger run --issue 2283                       # full pipeline, HTML report with sign-off block
LEDGER_RUNNER=modal python -m ledger run --issue 2283    # same, AI-written code in network-less sandboxes
python -m ledger.evidence.regen --issue 2283             # regenerate the evidence with provenance
python -m ledger.evidence.bench --issue 2283             # Modal vs local benchmark
```
