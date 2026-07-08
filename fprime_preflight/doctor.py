"""Human-readable doctor output."""

from __future__ import annotations

from fprime_preflight.receipt import PreflightReceipt


def render_doctor(receipt: PreflightReceipt, as_json: bool = False) -> str:
    if as_json:
        import json

        return json.dumps(receipt.to_dict(), indent=2)

    lines = [
        f"F' Deploy Preflight — {receipt.topology_name}",
        f"ship: {'YES' if receipt.ship else 'NO'}",
        f"findings: {len(receipt.findings)} "
        f"(critical={receipt.summary.get('critical', 0)}, "
        f"warning={receipt.summary.get('warning', 0)})",
        "",
    ]
    if not receipt.findings:
        lines.append("All checks passed. Topology is ready for HWIT preflight.")
        return "\n".join(lines)

    for finding in receipt.findings:
        prefix = finding.severity.upper()
        where = ""
        if finding.connection:
            where = f" [{finding.connection}]"
        elif finding.component:
            where = f" [{finding.component}]"
        lines.append(f"  {prefix} {finding.code}{where}: {finding.message}")
    return "\n".join(lines)
