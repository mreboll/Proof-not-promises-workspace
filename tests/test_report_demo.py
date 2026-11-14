"""`python -m ledger.report.demo`: los informes de la demo, regenerables desde los fixtures del repo."""

from __future__ import annotations

from ledger.report import demo


def identity(report, **kwargs):
    return report


def test_builds_every_demo_report_and_an_index(tmp_path):
    paths = demo.build_demo(tmp_path, translate=identity)
    names = sorted(p.name for p in paths)
    assert names == sorted(f"{d.slug}.html" for d in demo.DEMOS)
    index = (tmp_path / "index.html").read_text(encoding="utf-8")
    for d in demo.DEMOS:
        assert f'href="{d.slug}.html"' in index


def test_recorded_dotnet_run_uses_the_models_of_that_run(tmp_path):
    demo.build_demo(tmp_path, translate=identity)
    html = (tmp_path / "2283-dotnet.html").read_text(encoding="utf-8")
    assert "gemini-4-hydrogen" in html and "gemini-3.5-flash" in html and "nemotron-3.5-super-vl" in html
    assert "possible defect" in html


def test_fixture_reports_say_stage_3_was_not_run_and_keep_high_risk_red(tmp_path):
    demo.build_demo(tmp_path, translate=identity)
    html = (tmp_path / "2297.html").read_text(encoding="utf-8")
    assert "Stage 3 (cross-examination) was not run" in html
    assert "high risk without cross-examination" in html


def test_index_is_self_contained_and_english(tmp_path):
    demo.build_demo(tmp_path, translate=identity)
    index = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert '<html lang="en">' in index and "<script" not in index and "<link" not in index
