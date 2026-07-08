# F' Deploy Preflight

Validate F' deployment topologies and buffer contracts **before** hardware-in-the-loop — with receipt JSON and a polished dashboard.

**Live demo:** [enaguthi.com/fprime-preflight/site/](https://enaguthi.com/fprime-preflight/site/)

## Why this exists

NASA's F' framework ships powerful component-based flight software, but topology mistakes (buffer sizes, dangling ports, cancel-packet paths) often surface only on the bench. F' Deploy Preflight catches that class of defect locally — independent of any single upstream PR.

## Quick start

```bash
pip install fprime-preflight
fprime-preflight plan examples/demo/ref-cdh-snippet.yaml
fprime-preflight run examples/demo/broken-cancel-buffer.yaml -o out/receipts/latest.json
fprime-preflight doctor out/receipts/latest.json
fprime-preflight report out/receipts/latest.json -o out/report.md
fprime-preflight demo   # opens site/ with sample receipt
```

## CLI

| Command | Purpose |
|---------|---------|
| `plan` | Show components, connections, and checks that will run |
| `run` | Validate topology YAML → receipt JSON (exit 2 if not shippable) |
| `doctor` | Human summary of a receipt (`--json` for machine output) |
| `report` | Markdown report from receipt |
| `demo` | Open polished dashboard with bundled sample |

## Topology format

YAML describing components, port directions, and connections with optional `buffer_size` and `packet_kind`:

```yaml
name: my-deploy
constants:
  file_internal_buffer: 512
components:
  - name: fileDownlink
    kind: Svc.FileDownlink
    buffers:
      outbound: 512
    ports:
      bufferSendOut: output
connections:
  - from: fileDownlink.bufferSendOut
    to: downstream.bufferIn
    buffer_size: 9
    packet_kind: file_cancel
```

## Checks

- Unknown components on connections
- Buffer contract vs packet kind (`file_cancel`, `file_start`, `file_data`)
- FileDownlink cancel path oversized buffer (class from [nasa/fprime#5347](https://github.com/nasa/fprime/issues/5347))
- Dangling input/output ports

## Development

```bash
pip install -e ".[dev]"
pytest
```

## Contact

Abhishek Enaguthi — [enaguthi.com](https://enaguthi.com) · enaguthiabhishek@gmail.com
