"""CLI del historial de confianza. Lo usan PERSONAS después de firmar o al encontrar un fallo:

    python -m ledger.trust status
    python -m ledger.trust record-change out/report-2283.json --owner "Nombre Apellido"
    python -m ledger.trust record-escape --issue 2283 --path src/.../TypeCollector.cs --found-by spot-check \\
        --description "qué se escapó" [--source "commit, incidente o fichero"]

`status` enseña resultados (escapes por fichero aprobado, reverts, incidentes), no actividad (revisiones hechas).
"""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
from typing import get_args

from ledger.models import Report
from ledger.trust.policy import area_of, outcomes
from ledger.trust.record import DEFAULT_RECORD, EscapeEvent, FoundBy, add, change_from_report, load_record, save_record


def _owner(raw: str) -> str:
    owner = raw.strip()
    if not owner:
        raise argparse.ArgumentTypeError("a named owner is required: an unowned merge is not accepted")
    return owner


def _status(record_path: Path) -> None:
    rows = outcomes(load_record(record_path))
    if not rows:
        print("No signed changes or escapes recorded yet: every area is on probation.")
        return
    print(f"{'area':55s} {'trust':10s} {'changes':>7s} {'approved':>8s} {'escapes':>7s} {'rate':>6s}  found by")
    for r in rows:
        found = ", ".join(f"{k}={v}" for k, v in sorted(r.escapes.items())) or "-"
        print(f"{r.area:55s} {r.level.value:10s} {r.changes:7d} {r.approved_files:8d} {sum(r.escapes.values()):7d} {r.escape_rate:6.1%}  {found}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--record", type=Path, default=DEFAULT_RECORD, help="track record JSON (default: trust/track_record.json)")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    change = sub.add_parser("record-change", help="after a named owner signs a report")
    change.add_argument("report", type=Path)
    change.add_argument("--owner", type=_owner, required=True)
    escape = sub.add_parser("record-escape", help="something the evidence approved turned out wrong")
    escape.add_argument("--issue", required=True)
    escape.add_argument("--path", required=True)
    escape.add_argument("--found-by", choices=get_args(FoundBy), required=True)
    escape.add_argument("--description", required=True)
    escape.add_argument("--source", default="")
    args = parser.parse_args(argv)

    today = date.today().isoformat()
    if args.command == "status":
        _status(args.record)
        return
    record = load_record(args.record)
    if args.command == "record-change":
        report = Report.model_validate_json(args.report.read_text(encoding="utf-8"))
        event = change_from_report(report, owner=args.owner, date=today)
    else:
        event = EscapeEvent(issue_id=args.issue, date=today, area=area_of(args.path), path=args.path, found_by=args.found_by,
                            description=args.description, source=args.source)
    save_record(add(record, event), args.record)
    print(f"Recorded {event.kind} for #{event.issue_id} in {args.record}")
    _status(args.record)


if __name__ == "__main__":
    main()
