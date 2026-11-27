# Computational environment

Recorded on 2026-11-25 at the start of the project.

| Item | Value |
|---|---|
| Host | Local workstation, WSL2 on Windows |
| CPU | 8 logical cores |
| GPU | Not used (every model runs in seconds on the CPU) |
| Python | 3.14.4, isolated virtualenv in `.venv/` (not committed) |
| Packages | see `requirements.txt` (numpy, scipy, matplotlib, pandas, plotly, pytest, manifold3d, trimesh, shapely, reportlab) |

## Reproduce

```bash
python3 -m venv --without-pip .venv            # this Ubuntu image ships without ensurepip
curl -sSL https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py && .venv/bin/python /tmp/get-pip.py
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest
```
