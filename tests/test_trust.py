"""Confianza por área (reto: "humans spot-check the AI reviewer, and track what it misses"; "trust is earned per area,
from track record, and withdrawn after escapes"; "measure outcomes, not review activity")."""

from __future__ import annotations

import json

import pytest

from ledger.fakes import GREEN, RED
from ledger.models import (
    ChangeTestEvidence, ChangeType, FileTriage, FragmentVerdict, InvarianceCase, InvarianceEvidence, Report, Risk, Scope, Verdict,
)
from ledger.trust import __main__ as cli
from ledger.trust.policy import EARN_AFTER, Level, apply_trust, area_of, area_trust, outcomes, spot_checks
from ledger.trust.record import ChangeEvent, EscapeEvent, TrackRecord, add, change_from_report, load_record, save_record

AREA = "src/Lib/Core"
CT = ChangeTestEvidence(issue_id="1", change_type=ChangeType.BUGFIX, test_name="T", test_code="...", base=RED, pr=GREEN)
INV = InvarianceEvidence(cases=(InvarianceCase(id="a", tag="general", base_hash="1", base_hash_rerun="1", pr_hash="1"),))


def _report(paths_and_verdicts: list[tuple[str, Verdict]], issue_id: str = "1") -> Report:
    triage = tuple(FileTriage(path=p, scope=Scope.IN, risk=Risk.LOW) for p, _ in paths_and_verdicts)
    verdicts = tuple(FragmentVerdict(path=p, verdict=v, reasons=(f"M4: x",)) for p, v in paths_and_verdicts)
    return Report(issue_id=issue_id, change_type=ChangeType.BUGFIX, branch="b", base_commit="x", pr_commit="y", generated_at="t",
                  triage=triage, change_test=CT, invariance=INV, verdicts=verdicts)


def _clean(n: int, area: str = AREA) -> TrackRecord:
    record = TrackRecord()
    for i in range(n):
        record = add(record, ChangeEvent(issue_id=f"c{i}", date="2026-11-14", owner="Ana", approved={area: 3}))
    return record


ESCAPE = EscapeEvent(issue_id="9", date="2026-11-14", area=AREA, path=f"{AREA}/X.cs", found_by="spot-check", description="missed bug")


# --------------------------------------------------------------------------- áreas y niveles


def test_area_is_the_directory_up_to_three_levels():
    assert area_of("src/Lib/Core/Deep/File.cs") == "src/Lib/Core"
    assert area_of("src/Lib/File.cs") == "src/Lib"
    assert area_of("README.md") == "."


def test_new_area_is_on_probation():
    assert area_trust(TrackRecord(), AREA).level is Level.PROBATION


def test_trust_is_earned_after_enough_clean_changes():
    assert area_trust(_clean(EARN_AFTER - 1), AREA).level is Level.PROBATION
    assert area_trust(_clean(EARN_AFTER), AREA).level is Level.EARNED


def test_an_escape_withdraws_trust_until_it_is_earned_again():
    record = add(_clean(EARN_AFTER + 3), ESCAPE)
    assert area_trust(record, AREA).level is Level.WITHDRAWN
    for i in range(EARN_AFTER):
        record = add(record, ChangeEvent(issue_id=f"after{i}", date="d", owner="Ana", approved={AREA: 1}))
    trust = area_trust(record, AREA)
    assert trust.level is Level.EARNED and trust.clean_since_escape == EARN_AFTER


def test_changes_in_other_areas_do_not_count():
    assert area_trust(_clean(EARN_AFTER, area="src/Other"), AREA).level is Level.PROBATION


# --------------------------------------------------------------------------- efecto en el informe


def test_withdrawn_area_sends_green_files_to_a_human():
    report = _report([(f"{AREA}/A.cs", Verdict.GREEN), ("docs/B.md", Verdict.GREEN)])

    out = apply_trust(report, add(TrackRecord(), ESCAPE))

    a, b = out.verdicts
    assert a.verdict is Verdict.YELLOW and a.reasons[0].startswith("T1:") and "missed bug" in a.reasons[0]
    assert a.reasons[1:] == ("M4: x",)  # la razón de la matriz se conserva detrás
    assert b.verdict is Verdict.GREEN


def test_apply_trust_is_idempotent_and_leaves_red_alone():
    report = _report([(f"{AREA}/A.cs", Verdict.GREEN), (f"{AREA}/R.cs", Verdict.RED)])
    record = add(TrackRecord(), ESCAPE)

    once = apply_trust(report, record)

    assert apply_trust(once, record) == once
    assert once.verdicts[1].verdict is Verdict.RED


def test_spot_checks_are_deterministic_and_scale_with_trust():
    paths = [(f"{AREA}/F{i}.cs", Verdict.GREEN) for i in range(20)]
    report = _report(paths)

    probation = spot_checks(report, TrackRecord())
    earned = spot_checks(report, _clean(EARN_AFTER))

    assert len(probation) == 3 and len(earned) == 1  # 20 % y 5 % de 20, con tope de 3 y 1 por área
    assert spot_checks(report, TrackRecord()) == probation  # mismo informe, misma muestra
    assert {s.path for s in earned} <= {s.path for s in probation} or len(earned) == 1


def test_spot_checks_skip_withdrawn_areas_because_they_are_read_in_full():
    report = apply_trust(_report([(f"{AREA}/A.cs", Verdict.GREEN)]), add(TrackRecord(), ESCAPE))
    assert spot_checks(report, add(TrackRecord(), ESCAPE)) == ()


def test_every_area_with_green_files_gets_at_least_one_spot_check():
    report = _report([(f"{AREA}/A.cs", Verdict.GREEN), ("src/Other/x/B.cs", Verdict.GREEN)])
    assert {s.area for s in spot_checks(report, _clean(EARN_AFTER))} == {AREA, "src/Other/x"}


# --------------------------------------------------------------------------- resultados, no actividad


def test_outcomes_count_escapes_by_how_they_were_found():
    record = add(add(_clean(2), ESCAPE), EscapeEvent(issue_id="8", date="d", area=AREA, path="p", found_by="revert", description="r"))
    (row,) = [r for r in outcomes(record) if r.area == AREA]
    assert row.changes == 2 and row.approved_files == 6
    assert row.escapes == {"spot-check": 1, "revert": 1}
    assert row.escape_rate == pytest.approx(2 / 6)
    assert row.level is Level.WITHDRAWN


# --------------------------------------------------------------------------- registro en disco y CLI


def test_change_from_report_counts_files_approved_by_evidence_per_area():
    report = _report([(f"{AREA}/A.cs", Verdict.GREEN), (f"{AREA}/B.cs", Verdict.GREEN), ("docs/C.md", Verdict.YELLOW)])
    event = change_from_report(report, owner="Ana", date="2026-11-14")
    assert event.approved == {AREA: 2} and event.reviewed == {"docs": 1} and event.owner == "Ana"


def test_record_round_trips_through_disk(tmp_path):
    path = tmp_path / "track_record.json"
    record = add(_clean(1), ESCAPE)
    save_record(record, path)
    assert load_record(path) == record
    assert load_record(tmp_path / "missing.json") == TrackRecord()


def test_cli_records_a_change_and_an_escape_then_shows_status(tmp_path, capsys):
    record_path = tmp_path / "track_record.json"
    report_path = tmp_path / "report.json"
    report_path.write_text(_report([(f"{AREA}/A.cs", Verdict.GREEN)]).model_dump_json(), encoding="utf-8")

    cli.main(["--record", str(record_path), "record-change", str(report_path), "--owner", "Ana Pérez"])
    cli.main(["--record", str(record_path), "record-escape", "--issue", "1", "--path", f"{AREA}/A.cs",
              "--found-by", "spot-check", "--description", "null not handled"])
    cli.main(["--record", str(record_path), "status"])

    data = json.loads(record_path.read_text(encoding="utf-8"))
    assert [e["kind"] for e in data["events"]] == ["change", "escape"]
    out = capsys.readouterr().out
    assert AREA in out and "withdrawn" in out


def test_cli_rejects_a_change_without_a_named_owner(tmp_path):
    report_path = tmp_path / "report.json"
    report_path.write_text(_report([(f"{AREA}/A.cs", Verdict.GREEN)]).model_dump_json(), encoding="utf-8")
    with pytest.raises(SystemExit):
        cli.main(["--record", str(tmp_path / "r.json"), "record-change", str(report_path), "--owner", "  "])


# --------------------------------------------------------------------------- integración: pipeline, informe y firma


def test_pipeline_applies_the_track_record(monkeypatch):
    from pathlib import Path

    from ledger import pipeline
    from ledger.config import load_settings

    path = f"{AREA}/A.cs"
    monkeypatch.setattr(pipeline, "_stages_1_and_2", lambda i, s, r: ((FileTriage(path=path, scope=Scope.IN, risk=Risk.LOW),), CT, INV))
    monkeypatch.setattr(pipeline, "stage3_and_verdicts", lambda *a: (FragmentVerdict(path=path, verdict=Verdict.GREEN, reasons=("M4: x",)),))
    monkeypatch.setattr(pipeline, "load_record", lambda: add(TrackRecord(), ESCAPE))
    seen = {}
    monkeypatch.setattr(pipeline, "render_report", lambda report, out: seen.setdefault("r", report) and Path("x"))

    pipeline.run("2283", load_settings(), object())

    assert seen["r"].verdicts[0].verdict is Verdict.YELLOW


def test_report_shows_area_trust_and_the_spot_checks_to_do():
    from ledger.report.render import render_html

    report = _report([(f"{AREA}/F{i}.cs", Verdict.GREEN) for i in range(10)], issue_id="2283")
    html = render_html(report, models={}, issue_title="t", record=TrackRecord())

    assert "Spot-checks" in html and "probation" in html
    (pick, pick2) = spot_checks(report, TrackRecord())
    assert pick.path in html and pick2.path in html
    assert "python -m ledger.trust record-escape" in html


def test_signoff_names_withdrawn_files_and_the_spot_checks():
    from ledger.report.signoff import signoff

    record = add(TrackRecord(), ESCAPE)
    report = apply_trust(_report([(f"{AREA}/A.cs", Verdict.GREEN), ("src/Other/x/B.cs", Verdict.GREEN)]), record)

    s = signoff(report, {}, record=record)

    assert any(f"{AREA}/A.cs" in line and "trust withdrawn" in line for line in s["not_checked"])
    assert any(line.startswith("Spot-checks assigned") and "src/Other/x/B.cs" in line for line in s["residual"])


def test_the_real_2283_escape_withdraws_trust_in_code_analysis():
    """Escape real (fixtures/measure_2283_par_overlap_a.json): una ejecución aprobó TypeCollector.cs con el crash
    desplazado dentro. Con el historial del repo, ese mismo verde hoy lo leería una persona."""
    record = load_record()
    path = "src/MessagePack.SourceGenerator/CodeAnalysis/TypeCollector.cs"

    (v,) = apply_trust(_report([(path, Verdict.GREEN)], issue_id="2283"), record).verdicts

    assert area_trust(record, area_of(path)).level is Level.WITHDRAWN
    assert v.verdict is Verdict.YELLOW and "#2283" in v.reasons[0]


def test_spot_checks_are_a_sample_not_a_full_read():
    """222 snapshots verdes en un área (#2297) no pueden convertirse en 45 ficheros que leer."""
    report = _report([(f"{AREA}/S{i}.g.cs", Verdict.GREEN) for i in range(222)])
    assert len(spot_checks(report, TrackRecord())) == 3


def test_a_withdrawn_area_can_earn_trust_back():
    """Sus verdes salen T1 (amarillo); si el registro no los contara como aprobados por la evidencia, nunca se recuperaría."""
    record = add(TrackRecord(), ESCAPE)
    for i in range(EARN_AFTER):
        signed = apply_trust(_report([(f"{AREA}/A{i}.cs", Verdict.GREEN)], issue_id=f"n{i}"), record)
        assert signed.verdicts[0].verdict is Verdict.YELLOW
        record = add(record, change_from_report(signed, owner="Ana", date="d"))
    assert area_trust(record, AREA).level is Level.EARNED


def test_signoff_assigns_spot_checks_without_claiming_they_were_done():
    from ledger.report.signoff import signoff

    s = signoff(_report([(f"{AREA}/A.cs", Verdict.GREEN)]), {}, record=TrackRecord())
    line = next(x for x in s["residual"] if f"{AREA}/A.cs" in x)
    assert line.startswith("Spot-checks assigned") and "I spot-check" not in line
