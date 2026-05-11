# Workshop notebooks

These Jupyter notebooks are self-paced tutorials and interactive demos
for working with Overture data in Python. They're designed to be run
locally — see the [main README](../README.md#workshop-setup) for setup
instructions.

## Conventions for contributors

### Naming

Notebooks are numbered by intended order. The number prefix matches the
companion lesson markdown in the repo root. For example,
`3-lsib-demo.ipynb` is the runnable demo for lesson `6-lsib-demo.md`.

### Path handling

Every notebook resolves paths relative to its own location, not the
launch directory. This means the notebook works whether Jupyter is
launched from the repo root or from inside `notebooks/`. Use this
pattern at the top of every notebook:

```python
from pathlib import Path

NOTEBOOK_DIR = Path.cwd()
REPO_ROOT = NOTEBOOK_DIR.parent if NOTEBOOK_DIR.name == "notebooks" else NOTEBOOK_DIR
DATA = REPO_ROOT / "data"
```

Reference data files relative to `DATA`. Don't hardcode `./data/...` or
`../data/...`.

### Data files

Small shared data (under ~1 MB) lives in `data/`. Larger data should be
downloaded by the participant — document the download steps in both the
notebook itself and the companion lesson markdown.

### Outputs

Notebook-generated outputs go in `results/` or, for ephemeral artifacts,
a notebook-specific subdirectory that's gitignored.