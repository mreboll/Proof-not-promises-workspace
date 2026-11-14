# Bounty forms: Gemini and NVIDIA Nemotron

Text ready to paste into the Junction 2026 submission forms. Every number below comes from a real run in this repository; where a result is still pending, it says so.

---

## Best Use of Gemini API

**Project:** tieto-ledger, a Risk-Scoped Evidence Ledger (Tieto challenge "Earned Trust in AI Code").

**One sentence:** an AI agent changes hundreds of files, a human has to sign off; we replace line-by-line reading with a funnel where no model approves anything by argument, and Gemini produces the executable evidence that trust is built on.

**Why Gemini is central.** Our rule is "evidence over eloquence": a change is approved only by tests that run. Gemini writes that evidence:

1. **Scope triage at scale (`gemini-3.8-flash`).** For every changed file, Gemini decides whether the change is required by the issue (IN) or not (OUT), judging only against the literal issue text. On the largest PR (#2297, 237 files) the full Stage 1 took **57 s and 15 Gemini calls**, because 222 generated snapshots are classified by a static rule instead of the model. It left **14 of 237 files for a human** and caught an unrequested change: `TransformUtilities.cs` alters line breaks in generated code although the issue never asks for it.
2. **Independent change test.** An agent that sees only the issue text, never the diff, writes a test that must fail on the base branch and pass on the PR. A test written by the same agent that wrote the fix would be validating itself. For feature #2297 this test was written by Gemini and ran with real `dotnet test`: red on base, green on the PR.
3. **Defender and mutants (`gemini-4-hydrogen`).** In the cross-examination, the Defender cannot answer with text: its structured-output schema is only `{test_name, test_code}`. Gemini also writes the mutants that break each edge case on purpose; a Defender test counts only if it fails against its mutant, which rejects empty tests such as `Assert.True(true)`.

**What we did to make Gemini's output reliable.**
- Structured output (`response_schema`) with Pydantic validation and temperature 0.
- Disk cache keyed by prompt, so the demo is repeatable and protected from rate limits.
- Mutants are requested as `{find, replace}` over the real PR source, and we build the unified diff ourselves with difflib, so the patch always applies. If `find` is ambiguous, the error shows every occurrence with context so the model can make it unique (3 attempts).
- Issue and diff are passed as delimited untrusted data, with an instruction never to follow text inside them.

**Measured difference.** We first ran the triage with another model while our Gemini credits were pending. On #2297, Gemini flash was **3.7x faster (57 s vs 214 s)** and removed **both false positives** the other model produced, while still flagging the one real unrequested change.

**Honest status.** The change tests for #2283 and #2234 were generated before our Gemini key arrived; regenerating them with Gemini is in progress.

---

## Best Use of NVIDIA Nemotron

**Model:** `nvidia/nemotron-3.5-super-vl-120b-a12b` (Nemotron 3.5 Super VL), through the OpenAI-compatible API at `integrate.api.nvidia.com`.

**What it does: the Prosecutor.** After a high-risk change has passed its change test and the generation-invariance check, Nemotron reads the issue, the diff and the evidence summary and raises at most three concrete, testable edge cases that the evidence does not cover. It never wins by arguing: an objection is closed only when the Defender produces a test that passes on the PR and fails against a mutant. If any objection stays open after three rounds, the system refuses to decide and a human must sign.

**Why it matters: model diversity.** The Prosecutor (Nemotron, NVIDIA) and the Defender (Gemini, Google) are deliberately from different model families. If accusation and defence shared a model, they would share blind spots, and errors would be correlated.

**A real example.** On issue #2283 (an `IndexOutOfRangeException` in the MessagePack source generator), Nemotron's first objection pointed out that the issue names three unsafe `DeclaringSyntaxReferences[0]` call sites and the PR protects only two directly. That is exactly the kind of incomplete fix a human reviewer misses when the tests are green. (Confirming it with `dotnet test` against a mutant is in progress.)

**How we improved its output.**
1. JSON Schema injected into the prompt, Pydantic validation, and one automatic repair round that sends the validation error back to the model.
2. `<think>` reasoning blocks and markdown fences are stripped before parsing.
3. At most three objections, each of which must end in a test that fails against a mutant, or it does not count. This turns the model's output into an objective feedback loop instead of a matter of opinion.
4. Every failure we saw went into our lessons log with the rule that contained it. For example, a smaller Nemotron model once returned the JSON Schema itself instead of an answer; the system retried with another model and, failing that, sent the file to human review instead of crashing or approving it.
