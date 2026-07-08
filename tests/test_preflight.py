from pathlib import Path

import pytest

from fprime_preflight.topology import PortRef, load_topology, topology_from_dict
from fprime_preflight.validate import is_shippable, min_buffer_for_packet_kind, validate_topology

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "examples" / "demo"


def test_port_ref_parse():
    ref = PortRef.parse("fileDownlink.bufferSendOut")
    assert ref.component == "fileDownlink"
    assert ref.port == "bufferSendOut"


def test_port_ref_invalid():
    with pytest.raises(ValueError):
        PortRef.parse("nodot")


def test_load_good_topology():
    topo = load_topology(DEMO / "ref-cdh-snippet.yaml")
    assert topo.name == "ref-cdh-snippet"
    assert len(topo.components) == 2


def test_min_buffer_cancel():
    assert min_buffer_for_packet_kind("file_cancel", {}) == 9


def test_min_buffer_data():
    assert min_buffer_for_packet_kind("file_data", {"file_internal_buffer": 512}) == 512


def test_good_topology_ships():
    topo = load_topology(DEMO / "ref-cdh-snippet.yaml")
    findings = validate_topology(topo)
    assert is_shippable(findings)


def test_broken_cancel_buffer_fails():
    topo = load_topology(DEMO / "broken-cancel-buffer.yaml")
    findings = validate_topology(topo)
    assert not is_shippable(findings)
    codes = {f.code for f in findings}
    assert "cancel_oversized_buffer" in codes


def test_unknown_component():
    topo = topology_from_dict(
        {
            "name": "x",
            "components": [{"name": "a", "kind": "A", "ports": {"out": "output"}}],
            "connections": [{"from": "a.out", "to": "missing.in"}],
        }
    )
    findings = validate_topology(topo)
    assert any(f.code == "unknown_component" for f in findings)


def test_buffer_contract_too_small():
    topo = topology_from_dict(
        {
            "name": "x",
            "components": [
                {"name": "a", "kind": "A", "ports": {"out": "output"}},
                {"name": "b", "kind": "B", "ports": {"in": "input"}},
            ],
            "connections": [
                {"from": "a.out", "to": "b.in", "buffer_size": 2, "packet_kind": "file_cancel"}
            ],
        }
    )
    findings = validate_topology(topo)
    assert any(f.code == "buffer_contract" for f in findings)


def test_dangling_ports_warning():
    topo = load_topology(DEMO / "dangling-ports.yaml")
    findings = validate_topology(topo)
    assert any(f.code == "dangling_input" for f in findings)
    assert is_shippable(findings)


def test_receipt_roundtrip(tmp_path):
    from fprime_preflight.receipt import PreflightReceipt
    from fprime_preflight.validate import Finding

    receipt = PreflightReceipt(
        topology_name="t",
        topology_path="x.yaml",
        ship=False,
        findings=[Finding("buffer_contract", "critical", "too small")],
        summary={"critical": 1},
    )
    path = tmp_path / "r.json"
    receipt.save(path)
    loaded = PreflightReceipt.load(path)
    assert loaded.topology_name == "t"
    assert loaded.findings[0].code == "buffer_contract"


def test_doctor_render():
    from fprime_preflight.doctor import render_doctor
    from fprime_preflight.receipt import PreflightReceipt
    from fprime_preflight.validate import Finding

    text = render_doctor(
        PreflightReceipt(
            topology_name="demo",
            ship=False,
            findings=[Finding("cancel_oversized_buffer", "critical", "msg")],
            summary={"critical": 1},
        )
    )
    assert "NO" in text
    assert "cancel_oversized_buffer" in text


def test_doctor_json():
    from fprime_preflight.doctor import render_doctor
    from fprime_preflight.receipt import PreflightReceipt

    text = render_doctor(PreflightReceipt(topology_name="t", ship=True), as_json=True)
    assert '"topology_name": "t"' in text


def test_finding_to_dict():
    from fprime_preflight.validate import Finding

    d = Finding("x", "warning", "m", component="c").to_dict()
    assert d["component"] == "c"


def test_topology_from_dict_minimal():
    topo = topology_from_dict({"name": "min"})
    assert topo.name == "min"
    assert topo.components == []


def test_component_buffer_too_small():
    topo = topology_from_dict(
        {
            "name": "x",
            "components": [
                {
                    "name": "fileDownlink",
                    "kind": "Svc.FileDownlink",
                    "buffers": {"outbound": 4},
                    "ports": {},
                }
            ],
        }
    )
    findings = validate_topology(topo)
    assert any(f.code == "component_buffer" for f in findings)


def test_plan_build():
    from fprime_preflight.planner import build_plan

    topo = load_topology(DEMO / "ref-cdh-snippet.yaml")
    plan = build_plan(topo)
    assert "fileDownlink" in plan


def test_cli_plan(capsys):
    from fprime_preflight.cli import main

    assert main(["plan", str(DEMO / "ref-cdh-snippet.yaml")]) == 0
    assert "fileDownlink" in capsys.readouterr().out


def test_cli_run_writes_receipt(tmp_path):
    from fprime_preflight.cli import main

    out = tmp_path / "r.json"
    code = main(["run", str(DEMO / "broken-cancel-buffer.yaml"), "-o", str(out)])
    assert code == 2
    assert out.exists()


def test_cli_doctor_sample():
    from fprime_preflight.cli import main

    sample = ROOT / "site" / "sample_receipt.json"
    assert sample.exists()
    assert main(["doctor", str(sample)]) == 2


def test_cli_report(tmp_path):
    from fprime_preflight.cli import main

    sample = ROOT / "site" / "sample_receipt.json"
    out = tmp_path / "report.md"
    assert main(["report", str(sample), "-o", str(out)]) == 0
    assert "broken-cancel-buffer" in out.read_text()
