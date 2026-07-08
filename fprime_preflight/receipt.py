"""Preflight receipt schema."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fprime_preflight.validate import Finding


@dataclass
class PreflightReceipt:
    schema_version: str = "1.0"
    generated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    topology_name: str = ""
    topology_path: str = ""
    ship: bool = False
    findings: list[Finding] = field(default_factory=list)
    summary: dict[str, int] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["findings"] = [f.to_dict() for f in self.findings]
        return d

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> PreflightReceipt:
        data = json.loads(path.read_text(encoding="utf-8"))
        findings = [Finding(**f) for f in data.pop("findings", [])]
        return cls(findings=findings, **data)
