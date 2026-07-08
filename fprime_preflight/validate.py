"""Validation rules for F' deployment topologies."""

from __future__ import annotations

from dataclasses import dataclass

from fprime_preflight.topology import TopologySpec

# Public F' defaults (from FileDownlinkCfg / FilePacket headers — order of magnitude).
DEFAULT_FILE_INTERNAL_BUFFER = 512
FILE_PACKET_DESCRIPTOR_BYTES = 4
FILE_CANCEL_PACKET_BYTES = 5
FILE_START_MIN_BYTES = 16


@dataclass
class Finding:
    code: str
    severity: str  # critical | warning | info
    message: str
    component: str | None = None
    connection: str | None = None

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "component": self.component,
            "connection": self.connection,
        }


def min_buffer_for_packet_kind(packet_kind: str | None, constants: dict[str, int]) -> int:
    internal = constants.get("file_internal_buffer", DEFAULT_FILE_INTERNAL_BUFFER)
    if packet_kind == "file_cancel":
        return FILE_CANCEL_PACKET_BYTES + FILE_PACKET_DESCRIPTOR_BYTES
    if packet_kind == "file_start":
        return FILE_START_MIN_BYTES + FILE_PACKET_DESCRIPTOR_BYTES
    if packet_kind in {"file_data", "file_end"}:
        return internal
    return 1


def validate_topology(topology: TopologySpec) -> list[Finding]:
    findings: list[Finding] = []
    components = topology.component_map()
    connected_outputs: set[str] = set()
    connected_inputs: set[str] = set()

    for conn in topology.connections:
        src = str(conn.source)
        dst = str(conn.target)
        if conn.source.component not in components:
            findings.append(
                Finding(
                    code="unknown_component",
                    severity="critical",
                    message=f"connection source references unknown component {conn.source.component!r}",
                    connection=f"{src} -> {dst}",
                )
            )
        if conn.target.component not in components:
            findings.append(
                Finding(
                    code="unknown_component",
                    severity="critical",
                    message=f"connection target references unknown component {conn.target.component!r}",
                    connection=f"{src} -> {dst}",
                )
            )
        connected_outputs.add(src)
        connected_inputs.add(dst)

        required = min_buffer_for_packet_kind(conn.packet_kind, topology.constants)
        if conn.buffer_size is not None and conn.buffer_size < required:
            findings.append(
                Finding(
                    code="buffer_contract",
                    severity="critical",
                    message=(
                        f"buffer_size {conn.buffer_size} < required {required} "
                        f"for packet_kind={conn.packet_kind or 'default'}"
                    ),
                    connection=f"{src} -> {dst}",
                )
            )

        # FileDownlink cancel path lesson (#5347): downstream deserializes using buffer.getSize()
        if conn.packet_kind == "file_cancel" and conn.buffer_size == topology.constants.get(
            "file_internal_buffer", DEFAULT_FILE_INTERNAL_BUFFER
        ):
            findings.append(
                Finding(
                    code="cancel_oversized_buffer",
                    severity="critical",
                    message=(
                        "cancel packet sent at full internal buffer size — downstream "
                        "Fw::FilePacket::fromBuffer() may hit FW_DESERIALIZE_SIZE_MISMATCH"
                    ),
                    connection=f"{src} -> {dst}",
                )
            )

    for comp in topology.components:
        for port_name, direction in comp.ports.items():
            ref = f"{comp.name}.{port_name}"
            if direction == "output" and ref not in connected_outputs:
                findings.append(
                    Finding(
                        code="dangling_output",
                        severity="warning",
                        message=f"output port {ref!r} has no downstream connection",
                        component=comp.name,
                    )
                )
            if direction == "input" and ref not in connected_inputs:
                findings.append(
                    Finding(
                        code="dangling_input",
                        severity="warning",
                        message=f"input port {ref!r} has no upstream connection",
                        component=comp.name,
                    )
                )

        if "fileDownlink" in comp.kind or comp.name.lower() == "filedownlink":
            outbound = comp.buffers.get("outbound", topology.constants.get("file_internal_buffer"))
            if outbound and outbound < FILE_CANCEL_PACKET_BYTES + FILE_PACKET_DESCRIPTOR_BYTES:
                findings.append(
                    Finding(
                        code="component_buffer",
                        severity="critical",
                        message=f"FileDownlink outbound buffer {outbound} too small for serialized packets",
                        component=comp.name,
                    )
                )

    return findings


def is_shippable(findings: list[Finding]) -> bool:
    return not any(f.severity == "critical" for f in findings)
