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
