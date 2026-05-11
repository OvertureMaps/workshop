# 6. LSIB <-> Overture matching demo

| [<< 5. Base Theme](5-base-theme.md) | [Home](README.md) | >> |

This page is a companion to companion to the LSIB <-> Overture matching demo in this notebook: `3-lsib_overture.ipynb`. The notebook is the runnable
artifact; this file holds the conceptual background — why we made the
choices we did, what each decision point means, and how to use the outputs
beyond the notebook itself.

## What this notebook is for

The output of the notebook is a *crosswalk* — a table that links each LSIB
boundary segment to its corresponding Overture GERS ID. Each row of the
crosswalk says "LSIB segment X corresponds to Overture feature Y, with this
match class and these supporting metrics."

That linkage is what makes downstream work possible:

- **Cross-release tracking.** GERS IDs are stable across Overture releases.
  Once you've linked an LSIB segment to a GERS ID, you can follow that
  feature through future Overture updates without re-running the matching.
- **Joining to other Overture themes.** With a GERS ID in hand, you can
  pull related features from Overture's other themes (buildings, places,
  transportation) using the same identifier system.
- **Bringing Overture metadata into LSIB-based analysis.** Overture carries
  flags like `is_disputed`, `is_land` / `is_territorial`, and `perspectives`
  that LSIB doesn't structure the same way. The crosswalk lets you bring
  those in by ID.

## Matching algorithms

A boundary-matching workflow can use several different algorithms. The four
that came up while building this demo:

- **Buffer overlap at multiple tolerances.** For each pair of lines, ask
  what fraction of one falls within X meters of the other. We compute this
  at 250m in the demo; the production work used 100m, 250m, and 500m to
  test how robust each match is.
- **Hausdorff distance.** A worst-case distance metric: the farthest any
  point on one line gets from the other line. Useful as an outlier flag
  but a single bad vertex can dominate it, so it's not reliable as a
  primary score.
- **Length ratio.** The shorter line divided by the longer one. Cheap,
  intuitive, catches coverage gaps and data bugs that overlap metrics
  miss.
- **Hungarian assignment for many-to-many cases.** When both datasets have
  multiple features for the same country pair, the Hungarian algorithm
  finds the optimal one-to-one pairing across all candidates by maximizing
  total match quality.

The demo uses the 250m buffer overlap and the length ratio. The other two
are useful in production but add complexity without changing the headline
findings.

## Concepts and decisions

The notebook stays lean and runnable. This section holds the longer
explanations of why we made each choice. Organized as questions and answers
in roughly the order they come up while reading the notebook.

### What is the canonical `pair_key` and why do we build it?

A `pair_key` is a string that identifies a country pair, like `"AR|BR"` for
Argentina-Brazil. It's the join key we use to ask "do LSIB and Overture
both have features for this pair?"

The "canonical" part is a sorting convention. A boundary between Argentina
and Brazil could naturally be written either way: `"AR|BR"` or `"BR|AR"`.
If LSIB happens to encode it as `("AR", "BR")` and Overture happens to
encode it as `("BR", "AR")`, and we used the raw codes, we'd think they
were two different pairs and miss the match.

So we sort the two country codes alphabetically before joining them.
`("AR", "BR")` and `("BR", "AR")` both become `"AR|BR"`. Now both datasets
produce the same key for the same pair, regardless of which side they
happened to put first.

The actual code: `"|".join(sorted([cc1, cc2]))`.

### What's the difference between GENC and ISO?

These are two competing standards for two-letter country codes. Most of the
time they agree (US, GB, DE, FR, JP — same in both; CA in both, CN in both).

But they're maintained by different organizations (GENC by the US National
Geospatial-Intelligence Agency, ISO 3166 by the International Organization
for Standardization), and they diverge on entities where political
recognition is contested or unsettled. The most relevant case for boundary
data is Kosovo: GENC uses `KV`, ISO uses `XK` (XK is in the ISO 3166-1
user-assigned reserved range, used for Kosovo by convention).

**LSIB uses GENC** (it's published by the State Department). **Overture
uses ISO** (it's an international consortium and ISO is the broader
standard). So without translation, every Kosovo boundary in LSIB would
look like it has no Overture equivalent.

The demo simplifies this to one line:

```python
def genc_to_iso(cc):
    return "XK" if cc == "KV" else cc
```

Kosovo is the only meaningful divergence in practice for country-level
boundaries.

### What is Q2 and why do we drop it?

Q2 is a special LSIB code, not a real country. From the LSIB documentation:
*"The codes 'Q2' or 'QX2' denote a line in the LSIB representing a boundary
associated with areas not contained within the GENC standard."*

In plain language: when LSIB needs to encode a boundary involving an entity
that GENC doesn't have a code for — a non-recognized territory, a contested
region, an area of special status — they put `Q2` as the country code as a
placeholder. The boundary still exists in LSIB (with NOTES explaining what
it is), but it can't be expressed in GENC's vocabulary.

We drop these in the demo because they have no Overture counterpart. If
GENC doesn't have a code for the entity, ISO probably doesn't either, so a
Q2 LSIB segment has nothing to match against on the Overture side. In a
production workflow, Q2 entries would go to a manual review queue.

### Why are there more `division_boundary` rows than `division` rows?

Once the load runs, you'll see ~219 `division` rows (one per country) but
~363 `division_boundary` rows. The reason: a single country pair can appear
as multiple boundary features in Overture. Russia and China share one
international boundary in the geopolitical sense, but the data may split it
into multiple rows along its length. Same with US|CA across the Great
Lakes. This isn't an error — it's how the data is encoded, and it's
exactly what Section 4's cardinality bucketing detects and handles.

With ~200 countries averaging 3-5 land neighbors each, you'd expect roughly
`(200 * 4) / 2 = 400` unique country-pair borders. 363 is in the right
ballpark, slightly low because island nations have no land borders and
because the country-to-country filter drops some edge cases.

### What about the other dispute codes besides Kosovo?

The `genc_to_iso` translation in the load cell handles only Kosovo. This
is a real simplification, and it's worth understanding the full picture.

LSIB uses a family of GENC codes for entities that don't have standard
country codes, mostly disputed or special-status territories: `Q2`
(outside GENC), `Q4` (Palestinian territories), `QN` (Abyei), `QO` (Aksai
Chin), `QP` (Falkland Islands), `XO` (Jammu and Kashmir,
Indian-administered), `XW` (West Bank), and others. The demo only drops
`Q2`. The other dispute codes pass through and will appear in `lsib_only`
rows in the output.

Overture, separately, uses its own family of synthetic codes for the same
kinds of entities: codes like `XC`, `XH`, `XL`, `XQ`, `XX`, `XT`, `XY`,
`XZ`, and `XK` (Kosovo). These are documented in the Overture divisions
schema as permitted when no ISO code exists, but the meaning of each
individual code isn't externally documented — you have to query the
corresponding `division` row and read the `names.primary` field to find
out which entity each one refers to. The demo doesn't translate any of
these except `XK`.

**The two vocabularies don't align.** LSIB's Q-codes and Overture's
X-codes are separate naming systems for overlapping (but not identical)
sets of disputed entities. Aligning them requires a hand-curated entity
crosswalk that lives outside the country-code layer. That's real work —
important work — but it's out of scope for the demo. The consequence is
that some real boundaries (especially in disputed regions) will land in
`lsib_only` or `overture_only` rows not because they're missing from the
other dataset, but because we haven't done the dispute-code translation.

### What does the schema comparison really show?

The comparison table in Section 3 lays out the fields side by side. The
deeper reading is that each side carries information the other doesn't,
and those differences are part of why a crosswalk between them is
interesting in the first place.

- **LSIB carries fields that come from human judgment.** `NOTES`, `LABEL`,
  the `RANK` distinction between international boundaries (1) and other
  lines of separation (2). These exist because an analyst at the State
  Department decided what each segment is and wrote it down. They aren't
  recoverable from the geometry alone.
- **Overture's fields come from OSM data, transformed into the Overture
  schema.** Flags like `is_land`, `is_territorial`, `is_disputed`, the
  `perspectives` array, and per-source provenance via `sources[]` are
  applied systematically across the dataset.
- **Country codes live in different places.** LSIB puts `CC1` and `CC2`
  directly on every boundary feature. Overture splits the work across two
  types: `division_boundary` references its neighbors by UUID, and you
  resolve those to country codes via `division`.
- **They agree on geometry shape.** Both are line-only, multi-part
  allowed. This is what makes the geometric comparison apples-to-apples.
- **Identifiers behave differently despite looking identical.** Both
  datasets use UUIDv4 for their primary IDs, so they're indistinguishable
  on inspection. But LSIB's `ID` is per-version (changes on every release
  if the feature changes), while Overture's `id` is stable across
  releases when the feature qualifies for GERS. So a crosswalk built
  today won't have the same LSIB IDs as one built against the next LSIB
  release, but Overture IDs will largely persist.

### What does "opaque UUID" mean?

The Section 3 intro mentions that Overture's `division_boundary` references
its two adjacent divisions "only as opaque UUIDs in a `division_ids`
array." The word *opaque* is doing real work here: it means the UUID
itself doesn't tell you what it points to. You can't look at
`5c56cf7d-c485-4659-9399-5c17e9003112` and know whether it's France,
Texas, or Cook County. It's just a random-looking string. The only way to
find out what entity it represents is to query the `division` table, find
the row with that `id`, and read the `country` (or `names.primary`) field.
The UUID is a *reference* to a row, not information about a row.

The opposite would be a *transparent* identifier — something where the
value itself carries meaning. LSIB's `CC1 = "AR"` is transparent: you read
`AR` and you know it's Argentina. No lookup needed.

So the two datasets sit on opposite sides of this design choice:

- **LSIB (transparent):** stores `CC1 = "AR"` directly on each row.
- **Overture (opaque):** stores `division_ids = ["5c56cf7d-...", "422131df-..."]`
  and requires a lookup join to translate them.

That's why the lookup table exists. We pull `countries` (the `division`
rows where `subtype='country'`) so we can take an opaque UUID and turn it
into a country code we can actually use.

This is a design tradeoff, not a flaw. Opaque UUIDs let Overture maintain
stable identifiers across releases (the GERS thing) without forcing every
reference to embed semantic information that might change. If France's ISO
code changed, every row that hardcoded "FR" would need updating; rows that
point at France's UUID don't care. The cost is one extra step at query
time to resolve the reference. This is the same tradeoff database
designers make when they choose foreign keys over denormalized columns.

### Why didn't we start with a spatial join?

A reasonable instinct: if we have two sets of geometries, why not just do
`gpd.sjoin` on them and let geometry tell us which features go together?
Three reasons we didn't.

**1. Country pair attributes are a more reliable join key than geometry
for this problem.** Both datasets already carry country codes on every
feature. We *know* which country pair each line represents before we look
at the geometry at all. Joining by `pair_key` is cheap and gives us a
perfect partitioning: AR|BR features only need to be compared to other
AR|BR features. No ambiguity, no thresholds.

**2. A spatial join would create false positives we'd have to filter out
anyway.** At country tripoints (where three borders meet), lines from
multiple country pairs are within 250m of each other. A naive spatial join
would pair AR|BR segments with BR|UY segments at the AR|BR|UY tripoint,
then we'd have to filter back down to within-country-pair matches. That's
the attribute join we did in the first place, just done after the spatial
work instead of before.

**3. Starting with the attribute join makes the cardinality structure
visible.** The bucket counts are a finding in their own right — they tell
us where the structural disagreement between LSIB and Overture lives.

The spatial work is still happening — Section 5 is where we actually
compare the geometries. But it's compare, not match: we already know which
features to compare against which by the time we buffer-and-intersect
anything.

### Why does `geometric_disagreement` matter?

Length agrees, path doesn't. This usually means the two datasets *agree
on what they're representing* but disagree on where it is — a more
interesting finding than a generic "bad match." Often this is real source
disagreement (different treaty interpretations, different generalization
decisions, different vintages of the source data). It's the most useful
finding the matching surfaces, and it's the class that most surprises
people when they encounter it for the first time.

If you imagine a downstream user filtering the crosswalk: `match` rows
are ones they trust, `unmatched` rows they'd ignore, and
`geometric_disagreement` rows are the ones worth investigating because
both datasets *agreed enough to compare* but landed on different lines.

### Why does the crosswalk schema preserve both sides' metadata?

A crosswalk's core purpose is the ID-to-ID match. In principle,
`(lsib_id, overture_id, match_score)` is enough — the metadata that
describes each side already lives in the source datasets, and downstream
users can join back to it through the IDs whenever they need to. Keeping
the crosswalk minimal has real virtues: it's small, fast to read, and
easy to version.

In this case we're going to include more than that anyway. The reason is
the matching itself is likely to be iterated on — by us, by the divisions
team, by anyone reviewing the output. Carrying the country pair, the
bucket, the match class, and the metrics alongside each ID pair means a
reviewer can read a row and see why it landed where it did without
re-running the workflow. The metrics are part of the audit trail, not just
inputs we discard.

The IN|PK case in Section 9 is a clean illustration. LSIB has two features
(rank 1 International Boundary, rank 2 Line of Control). Overture has one
feature merging both into a single boundary. Neither dataset is "wrong" —
they're answering different questions about what a boundary is. The
crosswalk lets each downstream user pick which framing they want, filtering
the output by the field that matters to their use case.

### What would a more complex version of this workflow include?

The demo trims down from a more elaborate version. A more complex
workflow would add:

- **A multi-tolerance overlap sweep at 100 / 250 / 500m** to test how
  robust each match is to small geometric noise.
- **Hausdorff distance as an outlier flag.**
- **Hungarian assignment for `both_fragmented` pairs** to find the
  optimal feature-to-feature pairing across the candidates, instead of
  merging.
- **A more detailed sub-classification** that distinguishes data bugs from
  coastal asymmetry from coverage gaps.
- **A geometry companion file** (~100 MB at this scale) so consumers can
  re-render any pair without re-running the workflow.

These all live in the production workflow built before this demo. They
were cut from the demo for runtime and clarity, not because they're not
worth doing.

## Using the GeoJSON export in kepler.gl

The last cell of Section 10 writes a single GeoJSON file
(`output/lsib_overture_examples.geojson`) with 12 features: LSIB +
Overture lines for all six example pairs. Each feature carries
`pair_key`, `source` (`"lsib"` or `"overture"`), `match_class`, and
either `rank` (LSIB) or `is_disputed` (Overture).

To use it:

1. **Go to [kepler.gl](https://kepler.gl).** No login needed. Click "Get
   Started" if it's the first time, otherwise the map view loads directly.
2. **Drag the GeoJSON file onto the kepler.gl window** (or use the "Add
   Data" button in the top-left and select the file). The lines will load
   as a single layer.
3. **Open the Layer panel on the left** to style the layer. The most
   useful styling for this data:
   - Click the color swatch next to the layer name → choose "Color Based
     On" → pick `source` to color LSIB and Overture distinctly (red and
     blue work well), OR pick `pair_key` to see all six examples in
     different hues.
   - Bump the line thickness to 3-4 px so the lines are easy to see at
     zoom.
4. **Open the Filter panel** to drill into one example at a time. Filter
   by `pair_key` to show only IN|PK, then only KE|SS, etc.
5. **Zoom and pan freely.** The basemap is high-quality CARTO tiles by
   default, which gives you real geographic context for each boundary.
   Kashmir's geography for IN|PK, the Ilemi Triangle for KE|SS, the
   Brazilian Island for BR|UY — all visible in context.

The GeoJSON file is small (~50-100 KB) and contains only boundary
geometries derived from open data on both sides. Sharing it publicly is
fine.

## Three takeaways

These appear at the end of the notebook too. Repeated here because they're
the headline:

1. **The output is a link table, not a score.** Each row attaches a stable
   GERS ID to an LSIB segment. That linkage is what makes downstream work
   possible.
2. **Building that table is iterative.** The `is_land` filter, the
   bucketing decision, the threshold choices — none of these are obvious
   before you look at the data, and all of them shape what your output
   means.
3. **The disagreements are findings, not failures.** A pair that lands in
   `match` is confirmation. A pair in `geometric_disagreement` or `review`
   is a *finding* — something one of the datasets gets wrong, or
   something the two datasets are (correctly) saying different things
   about. Preserve both sides' metadata in the output so downstream users
   can read the findings in context.
