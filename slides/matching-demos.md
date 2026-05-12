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

Matching NGA's MGCP polygon features (buildings + base-theme polygons) against Overture.

<<<

### The demo data

MGCP cell **W079N26** — western Bahamas, 1:100K, captured 2015 by UK MOD against TRD 3.0.

- ~1,300 polygon features across 34 fcodes
- Mostly ocean; sparse capture
- Seven Overture types: `buildings/building`, `building_part`, and five `base/*` polygon types

_The methodology applies unchanged to denser data and other schema versions._

<<<

### Methodology

For each polygon pair we compute:

- **IoU** (Intersection over Union)
- **Centroid containment** (Overture centroid inside MGCP polygon)

| Tier | Condition |
| ---- | --------- |
| High | `IoU >= 0.5` |
| Low  | `IoU >= 0.3` _and_ centroid containment |

_Reproject both sides to a metric CRS (UTM 17N) before computing._

<<<

### Results: clean → friction

Seven passes, ordered from cleanest to messiest:

| Pass | Result |
| ---- | ------ |
| `buildings/building` | 412 → 350 matched (85%), 99% clean |
| `buildings/building_part` | 11 / 136 — schema design mismatch (parents, not parts) |
| `base/infrastructure`, `land_use`, `water` | 69 / 59 / 16; mostly clean, occasional aggregation |
| `base/land`, `land_cover` | 125 / 247; cardinality diagnostic earns its keep |

<<<

### Cardinality reporting

Each MGCP polygon gets a global label across all seven passes:

- **clean** — every matched pass is 1:1
- **aggregated** — one MGCP polygon → many Overture features
- **fragmented** — many MGCP polygons → one Overture feature
- **mixed** — both patterns appear
- **unmatched** — no Overture matches in any pass

Notes:
Unmatched is NOT an audit result. A polygon may be unmatched because of an Overture coverage gap, a real-world change, an IoU threshold miss, or because MGCP captured a feature that has no Overture polygon counterpart at any scale.

<<<

### Two-rate diagnostic

| Pattern | Example | What it means |
| ------- | ------- | ------------- |
| High match, high clean | AL015 Building (85% / 99%) | Direct GERS ID works |
| Low match, high clean | BH080 (32% / 100%) | Coverage gap, not schema mismatch |
| High match, low clean | BA030 Island (66% / 3%) | Needs a link table |
| Zero match | BA040 Tidal Water | Defer to a different theme |

<<<

### GERS adoption — five buckets

With thresholds `MATCH_RATE_HIGH=80`, `CLEAN_RATE_HIGH=80`, `MIN_SAMPLE=5`:

<ul>
  <li class="fragment"><strong>Direct GERS ID attachment</strong> — high match + high clean</li>
  <li class="fragment"><strong>Link table</strong> — high match + low clean</li>
  <li class="fragment"><strong>Deferred</strong> — zero match (different geometry/theme needed)</li>
  <li class="fragment"><strong>Review</strong> — partial / mixed</li>
  <li class="fragment"><strong>Insufficient sample</strong> — below threshold</li>
</ul>

<<<

### Finding: the link-table bucket is nearly empty

The skeleton expected it to be substantial. The data disagrees.

At 1:100K capture, the cardinality problem in this cell is binary:
- Codes with high match rates **don't fragment**
- Codes that fragment (BA030 Island, EC030 Trees) have **moderate match rates** → they land in `review`

_A finding about the data, not a flaw in the methodology._

<<<

Lesson: [7-buildings-matching](//labs.overturemaps.org/workshop/7-buildings-matching.html)

Notebook: `notebooks/4-buildings-matching.ipynb`
