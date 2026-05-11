## Matching Demos

Linking external datasets to Overture via _GERS IDs_

<<<

## What is a "match"?

A row in a _crosswalk_ table that links one feature in dataset A
to its corresponding feature in dataset B.

`(external_id, overture_id, match_class, metrics…)`

<<<

## Why match against Overture?

<ul>
  <li class="fragment">GERS IDs are <strong>stable across releases</strong></li>
  <li class="fragment">One ID lets you pull from <strong>any Overture theme</strong></li>
  <li class="fragment">Brings Overture's <em>provenance and flags</em> into your data</li>
</ul>

>>>

## Demo 1: LSIB ↔ Overture

Matching **administrative boundaries** between the U.S. State Department's
Large Scale International Boundaries (LSIB) and Overture's `division_boundary`.

Notes:
LSIB is the State Department's reference for international boundaries.
The notebook produces a crosswalk linking each LSIB segment to its
matching Overture GERS ID. The crosswalk is the deliverable; the
matching score is just how we got there.

<<<

## The join key: `pair_key`

A canonical, sorted country-pair string.

```python
pair_key = "|".join(sorted([cc1, cc2]))
# ("AR", "BR")  →  "AR|BR"
# ("BR", "AR")  →  "AR|BR"
```

Both datasets produce the _same key_ for the same border.

<<<

## Two country-code vocabularies

|          | LSIB   | Overture |
| -------- | ------ | -------- |
| Standard | GENC   | ISO 3166 |
| Kosovo   | `KV`   | `XK`     |

Translate before joining:

```python
def genc_to_iso(cc):
    return "XK" if cc == "KV" else cc
```

Notes:
GENC and ISO agree on most countries. They diverge on contested or
unrecognized entities. For country-level boundaries, Kosovo is the
only meaningful divergence; other dispute codes exist but are out of
scope for the demo.

<<<

## How we score a candidate pair

- **Buffer overlap (250m)** — what fraction of each line falls within 250m of the other
- **Length ratio** — shorter / longer

_Production adds Hausdorff distance and multi-tolerance sweeps; the demo keeps it lean._

<<<

## Cardinality buckets

The structural shape of the match, _before_ we look at geometry.

- **clean** — 1 LSIB feature ↔ 1 Overture feature
- **lsib_fragmented** — LSIB splits a single boundary into parts
- **overture_fragmented** — Overture splits it
- **both_fragmented** — both do, possibly differently

<<<

## Match classes

After scoring, every pair lands in one of:

<ul>
  <li class="fragment"><strong>match</strong> — geometry agrees, IDs link</li>
  <li class="fragment"><strong>geometric_disagreement</strong> — same boundary, different lines<br><em>The most interesting class</em></li>
  <li class="fragment"><strong>review</strong> — borderline; worth a human look</li>
  <li class="fragment"><strong>unmatched</strong> — no counterpart found</li>
</ul>

<<<

## Three takeaways

1. The output is a _link table_, not a score
2. Building it is _iterative_ — bucketing, filters, and thresholds shape the result
3. _Disagreements are findings, not failures_

<<<

Lesson: [6-lsib-demo](//labs.overturemaps.org/workshop/6-lsib-demo.html)

Notebook: `notebooks/3-lsib-demo.ipynb`

>>>

## Demo 2: MGCP polygons ↔ Overture

> **Status:** skeleton — full deck will land with the finished lesson

Matching NGA's MGCP polygon features (buildings + base-theme polygons) against Overture.

<<<

### Schema landscape

MGCP, TRD, TDS, DGIWG — and where GERS fits.

_Slide TODO_

<<<

### Methodology

For each polygon pair we compute:

- **IoU** (Intersection over Union)
- **Centroid containment**

A pair matches when IoU ≥ 0.5, **or** IoU ≥ 0.3 with the Overture centroid inside the MGCP polygon.

<<<

### Results: seven passes

| Overture type | Behavior |
| ------------- | -------- |
| `buildings/building` | Clean case — ~99% land in the clean bucket |
| `buildings/building_part` | Schema-design mismatch surfaces in low match count |
| `base/infrastructure`, `base/land_use`, `base/water` | Mostly clean with some aggregation |

_Slide TODO: expand with notebook screenshots_

<<<

Lesson: [7-buildings-matching](//labs.overturemaps.org/workshop/7-buildings-matching.html)

Notebook: `notebooks/4-buildings-matching.ipynb`
