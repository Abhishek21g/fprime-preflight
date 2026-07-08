"""Topology model and YAML loader for F' deployment preflight."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class PortRef:
    component: str
    port: str

    @classmethod
    def parse(cls, value: str) -> PortRef:
        if "." not in value:
            raise ValueError(f"port reference must be component.port, got {value!r}")
        comp, port = value.split(".", 1)
        if not comp or not port:
            raise ValueError(f"invalid port reference {value!r}")
        return cls(component=comp, port=port)

    def __str__(self) -> str:
        return f"{self.component}.{self.port}"


@dataclass
class ComponentSpec:
    name: str
    kind: str
    buffers: dict[str, int] = field(default_factory=dict)
    ports: dict[str, str] = field(default_factory=dict)


@dataclass
class ConnectionSpec:
    source: PortRef
    target: PortRef
    buffer_size: int | None = None
    packet_kind: str | None = None


@dataclass
class TopologySpec:
    name: str
    description: str = ""
    components: list[ComponentSpec] = field(default_factory=list)
    connections: list[ConnectionSpec] = field(default_factory=list)
    constants: dict[str, int] = field(default_factory=dict)

    def component_map(self) -> dict[str, ComponentSpec]:
        return {c.name: c for c in self.components}


def load_topology(path: Path) -> TopologySpec:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("topology file must be a YAML mapping")
    return topology_from_dict(data)


def topology_from_dict(data: dict[str, Any]) -> TopologySpec:
    name = str(data.get("name", "unnamed"))
    description = str(data.get("description", ""))
    constants = {str(k): int(v) for k, v in dict(data.get("constants", {})).items()}

    components: list[ComponentSpec] = []
    for raw in data.get("components", []):
        if not isinstance(raw, dict) or "name" not in raw:
            raise ValueError("each component requires name and kind")
        components.append(
            ComponentSpec(
                name=str(raw["name"]),
                kind=str(raw.get("kind", "unknown")),
                buffers={str(k): int(v) for k, v in dict(raw.get("buffers", {})).items()},
                ports={str(k): str(v) for k, v in dict(raw.get("ports", {})).items()},
            )
        )

    connections: list[ConnectionSpec] = []
    for raw in data.get("connections", []):
        if not isinstance(raw, dict):
            raise ValueError("connection entries must be mappings")
        src = PortRef.parse(str(raw["from"]))
        dst = PortRef.parse(str(raw["to"]))
        buffer_size = raw.get("buffer_size")
        connections.append(
            ConnectionSpec(
                source=src,
                target=dst,
                buffer_size=int(buffer_size) if buffer_size is not None else None,
                packet_kind=str(raw["packet_kind"]) if raw.get("packet_kind") else None,
            )
        )

    return TopologySpec(
        name=name,
        description=description,
        components=components,
        connections=connections,
        constants=constants,
    )
