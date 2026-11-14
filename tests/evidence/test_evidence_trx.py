from pathlib import Path

from ledger.evidence.trx import build_result, extract_compile_errors, parse_trx

DATA = Path(__file__).parent / "data"

ALL_PASS = """<?xml version="1.0" encoding="utf-8"?>
<TestRun xmlns="http://microsoft.com/schemas/VisualStudio/TeamTest/2010">
  <Results>
    <UnitTestResult testName="A.One" outcome="Passed" />
    <UnitTestResult testName="A.Two" outcome="Passed" />
  </Results>
  <ResultSummary outcome="Completed">
    <Counters total="2" executed="2" passed="2" failed="0" error="0" timeout="0" aborted="0" />
  </ResultSummary>
</TestRun>"""

NO_TESTS = """<?xml version="1.0" encoding="utf-8"?>
<TestRun xmlns="http://microsoft.com/schemas/VisualStudio/TeamTest/2010">
  <ResultSummary outcome="Completed">
    <Counters total="0" executed="0" passed="0" failed="0" error="0" timeout="0" aborted="0" />
  </ResultSummary>
</TestRun>"""

BUILD_OUTPUT_ES = r"""
  MessagePack -> C:\src\bin\MessagePack.dll
C:\src\tests\Ledger\T.cs(12,5): error CS0246: No se puede encontrar el tipo o el nombre de espacio de nombres 'Foo' [C:\src\T.csproj]
C:\src\tests\Ledger\T.cs(12,5): error CS0246: No se puede encontrar el tipo o el nombre de espacio de nombres 'Foo' [C:\src\T.csproj]
C:\src\tests\Ledger\T.cs(20,1): error CS1002: Se esperaba ; [C:\src\T.csproj]
C:\src\T.csproj : warning NU1901: vulnerabilidad baja
ERROR al compilar.
"""


def test_parse_real_trx_with_one_pass_and_one_fail():
    summary = parse_trx((DATA / "pass_fail.trx").read_text(encoding="utf-8-sig"))

    assert (summary.total, summary.passed, summary.failed) == (2, 1, 1)
    assert len(summary.failures) == 1
    assert summary.failures[0].startswith("LedgerProbeTrx.Fails: Assert.Equal() Failure")


def test_parse_all_pass():
    summary = parse_trx(ALL_PASS)
    assert (summary.total, summary.passed, summary.failed) == (2, 2, 0)
    assert summary.failures == ()


def test_build_result_red_for_real_from_trx():
    result = build_result((DATA / "pass_fail.trx").read_text(encoding="utf-8-sig"), "irrelevante", 12.5)

    assert result.build_ok and result.red_for_real and not result.green
    assert "Values differ" in result.output_tail
    assert result.duration_s == 12.5


def test_build_result_green():
    result = build_result(ALL_PASS, "", 1.0)
    assert result.green
    assert "2 passed" in result.output_tail


def test_no_matching_tests_is_neither_green_nor_red():
    result = build_result(NO_TESTS, "", 1.0)
    assert result.build_ok and not result.green and not result.red_for_real
    assert "no test matched" in result.output_tail


def test_missing_trx_means_build_failed_with_compile_errors():
    result = build_result(None, BUILD_OUTPUT_ES, 3.0)

    assert not result.build_ok
    assert not result.red_for_real  # un fallo de compilación NO reproduce el bug
    assert "CS0246" in result.output_tail and "CS1002" in result.output_tail
    assert result.output_tail.count("CS0246") == 1


def test_malformed_trx_is_reported_not_raised():
    result = build_result("<TestRun><oops", "", 1.0)
    assert not result.build_ok
    assert "trx" in result.output_tail.lower()


def test_extract_compile_errors_dedupes_and_ignores_warnings():
    errors = extract_compile_errors(BUILD_OUTPUT_ES)
    assert len(errors) == 2
    assert all("error CS" in e for e in errors)


def test_extract_compile_errors_falls_back_to_tail_when_no_cs_errors():
    errors = extract_compile_errors("línea 1\nMSB4018: la tarea falló\n")
    assert errors == ()
