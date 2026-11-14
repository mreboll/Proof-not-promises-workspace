"""Test del cambio (Etapa 2, regla 1): un agente que SOLO ve el issue escribe el test (decision-log D4).

Entradas del LLM: el texto de `issues/<id>.md` y un extracto de estilo de `GenericsFormatterTests.cs`
tomado del worktree BASE (la versión del PR ya incluye los tests del fix y filtraría la solución).
Nunca el diff. Si el test no compila en el PR, se reintenta UNA vez pasándole el error; si vuelve a
fallar, se devuelve tal cual y el veredicto será ROJO ("se niega a decidir").
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, Field

from ledger import llm
from ledger.config import Settings, get_issue
from ledger.evidence.workspace import ensure_worktree
from ledger.models import ChangeTestEvidence, TestRunner, TestRunResult

TEMPLATE_FILE = "tests/MessagePack.SourceGenerator.Tests/GenericsFormatterTests.cs"
TEMPLATE_MAX_LINES = 75
MAX_ERROR_CHARS = 3000

Complete = Callable[..., Any]


class GeneratedTest(BaseModel):
    test_name: str = Field(description="C# identifier; also the name of the single public test class")
    test_code: str = Field(description="Complete C# file with the xUnit test class")


SYSTEM_PROMPT = """You are an independent test author for the MessagePack-CSharp repository.
You get ONLY the text of a GitHub issue. You have NOT seen any fix. Write ONE xUnit test file that
reproduces the issue: on the code before the fix it must FAIL (an assertion fails), and once the
issue is resolved as described ("Expected behavior") it must PASS.

Hard rules:
- Output JSON with `test_name` and `test_code`. `test_name` is a C# identifier starting with
  "LedgerIssue"; `test_code` declares exactly one public class whose name is `test_name`.
  No namespace (the existing test classes live in the global namespace).
- The file is compiled inside tests/MessagePack.SourceGenerator.Tests (net8.0). Global usings already
  present: System.Collections.Immutable, MessagePack.SourceGenerator.CodeAnalysis, Xunit, Xunit.Abstractions.
  Add any other `using` you need. Available packages: xunit, FluentAssertions,
  Microsoft.CodeAnalysis.CSharp 4.12, Microsoft.CodeAnalysis.Testing (ReferenceAssemblies.Net.Net80).
- Useful types from the test project and product:
  * `MessagePack.SourceGenerator.MessagePackGenerator` (IIncrementalGenerator; use `.AsSourceGenerator()`)
  * `MessagePack.SourceGenerator.Analyzers.MsgPack00xMessagePackAnalyzer` (DiagnosticAnalyzer)
  * `ReferencesHelper.GetReferences(ReferencesSet.MessagePack)` -> MessagePack metadata references
  * `await ReferenceAssemblies.Net.Net80.ResolveAsync(LanguageNames.CSharp, CancellationToken.None)` -> framework refs
- Do NOT use `VerifyCS.Test.RunDefaultAsync`: it compares against stored snapshot files that do not
  exist for a new test, so it would fail even after a correct fix. Drive Roslyn directly instead
  (CSharpCompilation.Create, CSharpGeneratorDriver, Compilation.WithAnalyzers ->
  GetAnalyzerDiagnosticsAsync / GetAllDiagnosticsAsync, Emit to a MemoryStream +
  MetadataReference.CreateFromImage for a separate referenced assembly).
- Assert on observable behavior described in the issue (diagnostic IDs, exceptions, generated sources).
  Never write assertions that are always true. Do not catch and swallow exceptions.

Exact Roslyn 4.12 API shapes (these compile; do not invent other members):
```csharp
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.Diagnostics;   // required for Compilation.WithAnalyzers
using Microsoft.CodeAnalysis.Testing;       // ReferenceAssemblies

CSharpCompilation compilation = CSharpCompilation.Create(
    "Name", new[] { CSharpSyntaxTree.ParseText(source, new CSharpParseOptions(LanguageVersion.Latest)) },
    references, new CSharpCompilationOptions(OutputKind.DynamicallyLinkedLibrary));

GeneratorDriver driver = CSharpGeneratorDriver.Create(new MessagePackGenerator().AsSourceGenerator());
driver = driver.RunGeneratorsAndUpdateCompilation(compilation, out Compilation output, out ImmutableArray<Diagnostic> generatorDiagnostics);
GeneratorDriverRunResult runResult = driver.GetRunResult();
// runResult.Diagnostics : ImmutableArray<Diagnostic>
// runResult.Results[i].Exception : Exception?   runResult.Results[i].GeneratedSources[j].HintName : string

ImmutableArray<Diagnostic> analyzerDiagnostics = await compilation
    .WithAnalyzers(ImmutableArray.Create<DiagnosticAnalyzer>(new MsgPack00xMessagePackAnalyzer()))
    .GetAnalyzerDiagnosticsAsync();   // analyzer crashes surface here as diagnostic "AD0001"
```
"""


def build_user_prompt(issue_text: str, template: str) -> str:
    return (
        "## Issue\n\n"
        f"{issue_text.strip()}\n\n"
        "## Style reference (an existing test file in the same project, truncated)\n\n"
        f"```csharp\n{template.strip()}\n```\n"
    )


def build_retry_prompt(issue_text: str, template: str, previous: GeneratedTest, error: str) -> str:
    return (
        f"{build_user_prompt(issue_text, template)}\n"
        "## Your previous attempt did not compile\n\n"
        f"```csharp\n{previous.test_code}\n```\n\n"
        f"Compiler output:\n```\n{error[-MAX_ERROR_CHARS:]}\n```\n\n"
        "Return a corrected, complete file. Keep the same intent."
    )


def read_issue(settings: Settings, issue_id: str) -> str:
    path = settings.issues_dir / f"{issue_id}.md"
    if not path.exists():
        raise FileNotFoundError(f"Falta {path} (lo descarga la Línea B: issues/<id>.md)")
    return path.read_text(encoding="utf-8")


def style_template(settings: Settings, issue_id: str) -> str:
    """Extracto de GenericsFormatterTests.cs de la BASE (no del PR, que ya trae los tests del fix)."""
    source = ensure_worktree(settings, issue_id, "base") / TEMPLATE_FILE
    lines = source.read_text(encoding="utf-8-sig").splitlines()
    return "\n".join(lines[:TEMPLATE_MAX_LINES])


def generate_change_test(
    issue_id: str,
    settings: Settings,
    runner: TestRunner,
    *,
    issue_text: str | None = None,
    template: str | None = None,
    complete: Complete = llm.complete,
) -> ChangeTestEvidence:
    spec = get_issue(issue_id)
    issue_text = issue_text if issue_text is not None else read_issue(settings, issue_id)
    template = template if template is not None else style_template(settings, issue_id)

    test: GeneratedTest = complete(SYSTEM_PROMPT, build_user_prompt(issue_text, template), GeneratedTest, "pro")
    pr = runner.run_tests("pr", test.test_code, test.test_name)
    if not pr.build_ok:
        retry_prompt = build_retry_prompt(issue_text, template, test, pr.output_tail)
        test = complete(SYSTEM_PROMPT, retry_prompt, GeneratedTest, "pro")
        pr = runner.run_tests("pr", test.test_code, test.test_name)

    # En bug fix la base es obligatoria (debe fallar). En feature es evidencia extra: rojo en base
    # demuestra que el test mide algo nuevo; `ChangeTestEvidence.ok` sigue dependiendo solo del PR.
    base: TestRunResult = runner.run_tests("base", test.test_code, test.test_name)

    return ChangeTestEvidence(
        issue_id=issue_id,
        change_type=spec.change_type,
        test_name=test.test_name,
        test_code=test.test_code,
        base=base,
        pr=pr,
    )
