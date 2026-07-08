"""Plan summary before validation."""

from __future__ import annotations

from fprime_preflight.topology import TopologySpec


def build_plan(topology: TopologySpec) -> str:
    lines = [
        f"topology: {topology.name}",
        f"components: {len(topology.components)}",
        f"connections: {len(topology.connections)}",
        "",
        "components:",
    ]
    for comp in topology.components:
        buf = ", ".join(f"{k}={v}" for k, v in comp.buffers.items()) or "default"
        lines.append(f"  - {comp.name} ({comp.kind}) buffers=[{buf}]")
    lines.append("")
    lines.append("connections:")
    for conn in topology.connections:
        size = conn.buffer_size if conn.buffer_size is not None else "inherit"
        kind = conn.packet_kind or "any"
        lines.append(
            f"  - {conn.source} -> {conn.target} "
            f"buffer_size={size} packet_kind={kind}"
        )
    lines.append("")
    lines.append("checks: endpoints, buffer contracts, FileDownlink cancel path, dangling ports")
    return "\n".join(lines)
