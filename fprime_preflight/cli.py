"""F' Deploy Preflight CLI."""

from __future__ import annotations

import argparse
import sys
import webbrowser
from pathlib import Path

from fprime_preflight.doctor import render_doctor
from fprime_preflight.planner import build_plan
from fprime_preflight.receipt import PreflightReceipt
from fprime_preflight.topology import load_topology
from fprime_preflight.validate import is_shippable, validate_topology

ROOT = Path(__file__).resolve().parents[1]
DASHBOARD = ROOT / "site" / "index.html"
SAMPLE_RECEIPT = ROOT / "site" / "sample_receipt.json"
DEMO_BROKEN = ROOT / "examples" / "demo" / "broken-cancel-buffer.yaml"
DEMO_GOOD = ROOT / "examples" / "demo" / "ref-cdh-snippet.yaml"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="fprime-preflight",
        description="Plan and validate F' deployment topologies before hardware-in-the-loop.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    plan_p = sub.add_parser("plan", help="Show what will be validated")
    plan_p.add_argument("topology", type=Path, nargs="?", default=DEMO_GOOD)
    plan_p.set_defaults(handler=_cmd_plan)

    run_p = sub.add_parser("run", help="Validate topology and write receipt JSON")
    run_p.add_argument("topology", type=Path, nargs="?", default=DEMO_BROKEN)
    run_p.add_argument("-o", "--output", type=Path, default=Path("out/receipts/latest.json"))
    run_p.set_defaults(handler=_cmd_run)

    doc_p = sub.add_parser("doctor", help="Summarize a receipt")
    doc_p.add_argument("receipt", type=Path, nargs="?", default=SAMPLE_RECEIPT)
    doc_p.add_argument("--json", action="store_true")
    doc_p.set_defaults(handler=_cmd_doctor)

    rep_p = sub.add_parser("report", help="Write markdown report from receipt")
    rep_p.add_argument("receipt", type=Path)
    rep_p.add_argument("-o", "--output", type=Path, default=Path("out/report.md"))
    rep_p.set_defaults(handler=_cmd_report)

    demo_p = sub.add_parser("demo", help="Open polished site with sample receipt")
    demo_p.add_argument("--receipt", type=Path, default=None)
    demo_p.add_argument("--no-open", action="store_true")
    demo_p.set_defaults(handler=_cmd_demo)

    args = parser.parse_args(argv)
    try:
        return args.handler(args)
    except (ValueError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


def _cmd_plan(args) -> int:
    topology = load_topology(args.topology)
    print(build_plan(topology))
    return 0


def _cmd_run(args) -> int:
    topology = load_topology(args.topology)
    findings = validate_topology(topology)
    summary: dict[str, int] = {}
    for f in findings:
        summary[f.severity] = summary.get(f.severity, 0) + 1

    receipt = PreflightReceipt(
        topology_name=topology.name,
        topology_path=str(args.topology),
        ship=is_shippable(findings),
        findings=findings,
        summary=summary,
        notes=[topology.description] if topology.description else [],
    )
    receipt.save(args.output)
    print(render_doctor(receipt))
    print(f"\nWrote {args.output}")
    return 0 if receipt.ship else 2


def _cmd_doctor(args) -> int:
    receipt = PreflightReceipt.load(args.receipt)
    print(render_doctor(receipt, as_json=args.json))
    return 0 if receipt.ship else 2


def _cmd_report(args) -> int:
    receipt = PreflightReceipt.load(args.receipt)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# F' Deploy Preflight — {receipt.topology_name}",
        "",
        f"- **Ship:** {'yes' if receipt.ship else 'no'}",
        f"- **Generated:** {receipt.generated_at}",
        f"- **Topology:** `{receipt.topology_path}`",
        "",
        "## Findings",
        "",
    ]
    if not receipt.findings:
        lines.append("_No issues._")
    else:
        for f in receipt.findings:
            lines.append(f"- **{f.severity}** `{f.code}`: {f.message}")
    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {args.output}")
    return 0


def _cmd_demo(args) -> int:
    if args.receipt:
        import shutil

        shutil.copy(args.receipt, SAMPLE_RECEIPT)
    if not DASHBOARD.exists():
        print(f"error: dashboard missing at {DASHBOARD}", file=sys.stderr)
        return 1
    url = DASHBOARD.resolve().as_uri()
    print(f"Dashboard: {url}")
    if not args.no_open:
        webbrowser.open(url)
    return 0
