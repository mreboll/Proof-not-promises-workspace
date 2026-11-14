# Concept Card — Proof, not promises

**Risk-Scoped Evidence Ledger** · Junction 2026 · Tieto challenge *Earned Trust in AI Code*
Tested on four real AI-written pull requests to MessagePack-CSharp (#2283, #2234, #2129, #2297).

Every number on this card was measured on real runs; sources in `docs/numeros-evidencia.md`.

## The problem

An AI agent changes hundreds of files; a human signs the approval. Reading everything is infeasible, and trusting
the AI's own summary is negligent. The question is not "is the code good?" but **"what evidence lets a person sign
without reading every line?"**

## Our recommendation

Stop reviewing AI-written changes line by line, and stop trusting the AI's summary of them. The PR review factory
should turn every change into a **ledger of executable evidence traced to its requirement ID**, spend human attention
only where that evidence is missing or contradicted, and make the named owner sign three explicit lists: **what was
checked and by what, what was not checked and why, and the residual risk they accept.** The AI reviews; it never
approves. When it cannot prove something, it **refuses to decide** and says exactly what to read.

## Principles

1. **Proportional, deterministic risk.** Static, auditable rules (paths, `public` signatures, core namespaces)
   decide how much scrutiny a file gets. Never a model's intuition. Same diff, same risk.
2. **Evidence over eloquence.** No model approves anything by argument. Trust comes only from executable checks.
3. **Disagreement only produces tests.** The Defender cannot answer the Prosecutor with text, only with a test that
   passes on the PR **and fails against a mutant**. Otherwise the system **refuses to decide** and a human signs.

## How it balances risk, hallucination, transparency, confidence and quality

| Axis | Mechanism | What we refuse |
|---|---|---|
| **Risk** | Static, auditable rules set the depth of scrutiny per file; high risk triggers cross-examination; out of scope plus high risk is always red | A risk score from a model that nobody can explain |
| **Hallucination** | A model's claim counts only once it is a test that runs. Change tests are written from the issue alone; Defender tests must fail against a mutant; infrastructure failures are marked `INFRA`, never evidence | Accepting an AI's "I checked it" or a test that would also pass on broken code |
| **Transparency** | Every verdict starts with its matrix rule (M1–M7); every test, hash, mutant and model is in the report and the JSON; normalizations are declared | Hidden reasoning, undeclared filtering |
| **Confidence** | There is no self-reported confidence. "Confidence" is the state of the evidence: proven, contradicted, or missing | A confidence number without evidence behind it |
| **Quality** | Generation invariance guards everything outside the issue; Prosecutor and Defender come from different model families so their blind spots do not align | One model grading its own homework |

## How trust is earned over time (implemented: `ledger/trust/`, decision D17)

1. **A named owner signs every change**, using the three lists the report generates (checked / not checked / residual
   risk). `python -m ledger.trust record-change <report> --owner "Full Name"` refuses an empty name: no unowned merge.
2. **Humans spot-check the AI reviewer.** Every report lists green files to read in full: 20 % of each area's green
   files on probation, 5 % once trust is earned, at least 1 and at most 3 per area (a sample, not a full read). The
   sample is picked by a hash of issue and path, so neither the AI nor the signer chooses it, and an auditor can
   recompute it. Whatever the reader finds is recorded with `record-escape`.
3. **Trust is per area and comes from track record** (`trust/track_record.json`, versioned in the repo). An area is the
   file's directory, three levels deep: a fixed rule, not a model's call. It starts on *probation*, is *earned* after 5
   clean signed changes, and is *withdrawn* by one escape: green files there go back to a human (verdict TR) until 5
   clean changes are signed again.
4. **Measure outcomes, not activity:** `python -m ledger.trust status` shows, per area, escapes per approved file and
   how each was found (spot-check, revert, incident, rerun), never "reviews done".

**Real data, nothing invented.** The record holds one escape, and it is ours: in one of the #2283 runs, all three
objections were closed and the evidence approved `TypeCollector.cs`, although that AI fix only moves the crash
(`fixtures/measure_2283_par_overlap_a.json`). Trust in `src/MessagePack.SourceGenerator/CodeAnalysis` is therefore
withdrawn, and that same green would now go to a human. No change is recorded as signed, because no human has signed one yet.

## Technology considerations

- **Backend (what we tested):** the oracle is differential, base vs PR: generated code and diagnostics for a source
  generator. For a service it would be API contract tests and recorded traffic replayed against both versions.
- **Frontend:** the same funnel applies with a different oracle: visual snapshots and accessibility checks of base vs
  PR, with a declared list of screens the issue is allowed to change.
- **Security:** AI-written tests are untrusted code, so they run in network-less sandboxes (Modal). Issue text and
  diffs reach the models as delimited, untrusted data. By rule, high risk (never approved without cross-examination)
  covers memory-unsafe code (`unsafe`, `Span<T>`, `stackalloc`), public signatures, and security-sensitive code for a
  deserializer: resolving types by name (`Type.GetType`, `Assembly.Load`, `Activator.CreateInstance`, the classic
  "typeless" attack vector), `MessagePackSecurity` settings, `BinaryFormatter`, `Process.Start`, crypto, `Marshal`, and
  security or typeless code paths (R-HIGH-04/05). None of the four sample PRs touches them, so they change no result
  shown here.

## The funnel

| Stage | What it does | Who / what |
|---|---|---|
| **T1 Scope & risk** | Each file: in or out of the issue's scope (LLM, judged against the literal issue) × risk by static rules | Gemini flash + rules |
| **T2 Executable evidence** | (a) A **change test** written by an agent that sees only the issue, never the diff: must fail on base and pass on PR. (b) **Generation invariance**: a corpus of 31 snippets through the source generator in two isolated processes; outside the issue, generated code and diagnostics must hash identically (base run twice for determinism) | Gemini/Nemotron + .NET + Modal |
| **T3 Cross-examination** | High-risk, in-scope files: up to 3 Prosecutor objections, each answered only by a Defender test validated against a mutant | Nemotron (Prosecutor) vs Gemini (Defender) |

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
| Full pipeline, 237-file PR (#2297), cross-examination in parallel | **14–20 min on Modal** over 4 runs (over 1 h sequential, cancelled) |
| Concurrency ceiling (measured) | Modal: 60 sandboxes, 0 failures · Gemini pro: no 429 up to 48, collapses at 64 |
| Scope triage of a 237-file PR | 57 s, 15 Gemini calls |
| Modal compute for the whole hackathon | **$2.86** in credits |

Against that: on the 237-file PR, static rules rank **223** files as low risk and the passing evidence approves them
unread; **12** high-risk files go to cross-examination (36 objections in parallel, ~17 min): in our first run 2 were closed by
valid tests and approved, and the system **refused to decide** on 10, handing the human 12 Defender tests that fail
on the PR (possible defects, or wrong tests) and 12 that proved nothing against their mutant; the **2** out-of-scope files go straight to a human (one yellow, one red). At most **14 of 237** files
need human eyes. On #2283 the human gets **the unresolved questions with the exact failing tests**. We did not
measure reviewer time; we measured where the reading goes.

## Limits (honest)

- **A badly written ticket gives weak evidence** (#2234). The system says so; it does not fix the ticket.
- **It needs a differential oracle.** Here it is "generated code + diagnostics"; areas without one get less.
- **LLMs are not reproducible run to run**; the disk cache makes the demo repeatable, not the models. Across four
  real runs of #2297, 3 to 12 of 36 objections were closed, and wall time ranged from 14 to 20 min.
- **Past a point, speed is the model's, not ours.** Parallelism removed the queue (over 1 h → ~17 min); after that,
  one slow model call sets the end time, and its variance is larger than any further optimisation we measured.
- The invariance check runs locally; AI-written code runs isolated only with `LEDGER_RUNNER=modal`.
- Every AI failure we hit is in `docs/lessons-log.md`, each tied to the funnel layer that caught it.

## Reproduce

```bash
python -m ledger run --issue 2283                       # full pipeline, HTML report with sign-off block
LEDGER_RUNNER=modal python -m ledger run --issue 2283    # same, AI-written code in network-less sandboxes
python -m ledger.evidence.regen --issue 2283             # regenerate the evidence with provenance
python -m ledger.evidence.bench --issue 2283             # Modal vs local benchmark
```
