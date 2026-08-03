---
layout: none
permalink: /index.html
---

## Resources

| Name | Description |
| ---- | ----------- |
| [Overture Explorer](https://explore.overturemaps.org) | Inspect and explore Overture data and schema |
| [Overture Documentation](https://docs.overturemaps.org/) | Learn how to access and work with Overture data and schema |

---

## Workshop Lessons

1. [What is Overture Maps?](1-what-is-overture.md)
2. [Exploring Overture Maps Data](2-accessing-data.md)
3. [Accessing Overture Maps GeoParquet with DuckDB](3-geoparquet-duckdb.md)
4. [Global Entity Reference System (GERS)](4-gers.md)
5. [Base Theme](5-base-theme.md)
6. [LSIB ↔ Overture matching demo](6-lsib-demo.md)
7. [Matching polygon features to Overture](7-buildings-matching.md)
8. [Matching concepts and pipeline context](8-matching-concepts.md)
9. [Matching linearly-referenced road networks to Overture](9-transportation-matching.md)

---

## Walkthroughs

Applied, scenario-specific walkthroughs that build on the lessons above.

| Name | Description |
| ---- | ----------- |
| [iRAP integration options](irap-integration-walkthrough.md) | Options for integrating iRAP road-safety data with Overture: matching for a bridge file, self-service matching, or a schema extension / supplemental dataset |

---

## Workshop Setup

### Local setup (recommended)

Install [uv](https://docs.astral.sh/uv/), a fast Python environment manager:

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows: see https://docs.astral.sh/uv/getting-started/installation/
```

Clone the repo and start JupyterLab:

```bash
git clone https://github.com/OvertureMaps/workshop.git
cd workshop
uv sync
uv run jupyter lab
```

`uv sync` installs all dependencies into a project-local `.venv/` based on the locked versions in `uv.lock`. First run takes a minute; subsequent runs are instant. You don't need to activate the venv manually — `uv run` handles it.

### Alternative: pip

If you prefer pip and already have a Python environment:

```bash
git clone https://github.com/OvertureMaps/workshop.git
cd workshop
pip install -r requirements.txt
jupyter lab
```

The `requirements.txt` is generated from `pyproject.toml` and `uv.lock`, so versions match the uv setup.

> **Note:** GitHub Codespaces support is being updated for the new setup. For now, please use one of the local setup paths above.

### Running the notebooks

Launch JupyterLab from the repo, then open a notebook from the `notebooks/` panel and run cells top to bottom (Shift+Enter), or **Run ▸ Run All Cells**:

```bash
uv run jupyter lab
```

- Notebooks resolve paths relative to their own location, so they work whether you launch Jupyter from the repo root or from inside `notebooks/`.
- Source data is fetched on first run (Overture from S3, plus any dataset a notebook needs) and cached under `data/` (which is gitignored). The first data-heavy cell can take a minute; re-runs are fast.
- To check that a notebook executes end to end without opening the UI:

  ```bash
  uv run jupyter nbconvert --to notebook --execute --stdout notebooks/5-transportation-matching.ipynb > /dev/null
  ```

**Notebook 5 — optional splitter step.** `5-transportation-matching.ipynb` has one step that runs the [transportation-splitter](https://github.com/OvertureMaps/transportation-splitter)'s real split functions on Overture segments. It's declared as an optional extra (it pulls in `pyspark`/`apache-sedona`, though **no Spark session is ever started** — only the pure-Python geometry functions are used), so it's kept out of the default install. Enable it with:

```bash
uv sync --extra splitter
```

or, with pip: `pip install ".[splitter]"`. If you skip it, that step prints an install hint and the rest of the notebook still runs.

### Previewing the lessons in your browser

The lessons are Markdown files that link to one another. To read them rendered (GitHub-style) with working lesson-to-lesson navigation, use [grip](https://github.com/joeyespo/grip):

```bash
uv run --with grip grip .
```

Then open <http://localhost:6419> and click through the lessons — `grip` renders each `.md` and follows the relative links. (It calls GitHub's render API, so very heavy use can hit rate limits.)

Alternatives:

- **VS Code** — open a lesson and press `Cmd+Shift+V` (macOS) or `Ctrl+Shift+V`; relative links between lessons work in the preview.
- **On GitHub** — the lessons render with working links directly in the repository.

> Don't use `bundle exec jekyll serve` to preview the lessons: the site config only renders `README.md` to `index.html`, so the inter-lesson `.md` links 404 under Jekyll.

---

### Working with DuckDB

When launching DuckDB, specify a database name like `duckdb workshop.dbb` so you can save tables and views that persist across sessions.

To attach Overture's hosted DuckDB database (experimental):

```sql
LOAD spatial;
ATTACH 'https://labs.overturemaps.org/data/latest.ddb' as overture;

-- Now you can just reference `overture.place` for type=place features
SELECT count(1) from overture.place;
```
