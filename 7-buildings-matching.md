# Matching MGCP polygon features to Overture

This lesson is the prose companion to notebook `4-buildings-matching.ipynb`.
The notebook contains the runnable demo; this page explains what the demo
is doing, why the methodology is designed the way it is, and how to read
the results it produces.

## What this demo does

Two open geospatial datasets, NGA's MGCP and Overture, each describe the
same real-world places, but with different schemas, different capture
scales, and different decisions about what counts as a "feature." This
demo walks through a methodology for matching polygon features between
them and producing a stable [GERS](https://docs.overturemaps.org/gers/)
link table that can serve as the join key for downstream data integration.

The deliverable is the link table: a many-to-one or one-to-one mapping
between MGCP UIDs and Overture GERS IDs. Attribute translation and other
downstream integration work are deliberately out of scope. Once the link
table exists, anyone holding either side can join attributes from the
other; the matching pipeline doesn't need to reason about what the
attributes mean.

The methodology is geometry-based and schema-version-agnostic. It
operates on polygon overlap, not on attribute values or feature codes,
which means it works identically against MGCP TRD 3.0 (the demo data),
current MGCP TRD 4, TDS v7, or any other schema family in the same
lineage. Switching schemas changes the input filter; the matching itself
doesn't change.

## Running the demo

See `notebooks/4-buildings-matching.ipynb` and the project README for
setup instructions. The notebook expects:

- The MGCP W079N26 cell unpacked into `data/mgcp/W079N26/`. Download
  link is in the notebook.
- Overture parquets cached at `data/overture_cache/`. The notebook
  pulls these from S3 on first run, or you can pre-stage them if your
  environment has restricted network access.

The notebook uses `uv` for environment management; setup instructions
are in the project README.

## Schema landscape

A few standards are in play in this demo and the relationships between
them are worth pinning down before we look at any data.

**MGCP** (Multinational Geospatial Co-production Program) is a topographic
data collection effort coordinated through DGIWG (the Defence Geospatial
Information Working Group). National contributors capture data using a
shared specification, the Topographic Reference Database, or **TRD**, and
publish it as standardized tiles. The Bahamas data used in this demo was
captured by UK MOD in 2015 against TRD 3.0. The current operational
version of the spec is TRD 4.6.

**TDS** (Topographic Data Store) is a related schema family used by NGA
internally. TDS shares most of its structure with MGCP and uses
overlapping feature codes, but the two specs have evolved on parallel
tracks and the codes don't always line up. Buildings, for example, are
AL015 in MGCP TRD 3.0 and AL013 in TDS v7: same real-world feature,
different code.

**GERS** ([Global Entity Reference System](https://docs.overturemaps.org/gers/))
is Overture's persistent identifier system. It doesn't replace MGCP or
TDS or any other schema; it sits alongside them, providing a stable ID
that downstream consumers can join on regardless of which schema produced
the underlying feature. Once a feature has a GERS ID, integrating new
data sources that reference it doesn't require schema-version
negotiation.

## The demo data

MGCP data is organized into 1° × 1° cells. The demo uses cell `W079N26`,
covering longitudes -79 to -78 and latitudes 26 to 27 over the western
Bahamas, including parts of Grand Bahama Island. The cell was captured by
UK MOD in 2015 against TRD 3.0 and is publicly available through ArcGIS
Online.

This cell is sparse, and being honest about that is worth doing up front.
A 1° × 1° cell is around 12,300 km², and two things stack up to make
W079N26 thin: most of the cell is open ocean rather than land, and MGCP's
1:100,000 capture scale doesn't try to record every small structure the
way denser ML-derived datasets do. The cell contains roughly 1,300
polygon features across 34 feature codes, a small fraction of what an
Overture pull over the same bounding box returns.

MGCP also captures most small features as points rather than polygons at
1:100K scale. The bulk of MGCP's feature coverage in W079N26 is point
data, which this demo doesn't address; point-in-polygon matching is a
separate methodology and a natural follow-on.

The matching methodology in this demo runs against seven Overture types:
`buildings/building`, `buildings/building_part`, and the five
polygon-bearing types within Overture's `base` theme (`infrastructure`,
`land_use`, `water`, `land`, `land_cover`). The seven passes are run
independently and aggregated, so we don't have to decide in advance
which Overture type any given MGCP feature should match against.

## Schema comparison

Before matching, it's worth understanding what each side's building
schema actually contains. The notebook walks through the
`MGCP AL015 (Building)` ↔ `Overture buildings/building` pair in detail;
this section summarizes the comparison.

The point of the comparison isn't to translate attributes between
schemas. Attributes stay on whichever side they came from. The matching
pipeline produces a link between identifiers; nothing else. The
comparison exists to orient anyone who's going to do something with the
matched results downstream.

A few observations from looking at both sides:

- **Both schemas have a stable identifier** intended to persist across
  edits and releases. MGCP's `UID` and Overture's `id` (a GERS ID) are
  both UUIDs. The matching pipeline links these two identifiers; that
  link is the central deliverable.

- **The shape of attribute coverage differs.** Overture's schema is
  broader (more attribute fields available); MGCP is more sparsely
  populated in practice (many spec fields contain "no information"
  sentinels). For attributes like height, Overture is more likely to
  have values; for provenance and accuracy metadata, MGCP is more
  complete.

- **Some attributes don't have direct counterparts.** MGCP's `ACE`
  (positional accuracy) and `TIER_NOTE` (release restrictions) have no
  Overture analog. Overture's `roof_shape` and `facade_material` have
  no MGCP analog. In this methodology, those attributes stay on
  whichever side captured them.

A full attribute mapping is a separate exercise that isn't required for
the matching to work. The same principles apply to the other six passes,
though the specific attributes differ.

## Matching methodology

For each pair of polygons (one from MGCP, one from an Overture type), we
compute two quantities:

1. **Intersection over Union (IoU)**: the ratio of the area of
   intersection to the area of union. Ranges from 0 (no overlap) to 1
   (identical footprints). The standard polygon-matching metric.

2. **Centroid containment**: whether the centroid of the Overture
   polygon falls inside the MGCP polygon. Asymmetric on purpose: it
   catches the case where the MGCP polygon is significantly larger
   than the Overture one and IoU alone wouldn't be high enough to
   declare a match.

A pair is considered a match if it meets one of two criteria:

| Tier | Condition |
| --- | --- |
| High | `IoU >= 0.5` |
| Low  | `IoU >= 0.3` *and* the Overture centroid is contained in the MGCP polygon |

The single-threshold version of this rule (high tier only) is the
natural starting point. The two-tier rule is a controlled relaxation
for cases where IoU underweights real matches: an MGCP feature
captured at coarse scale that aggregates what Overture has split into
two or three smaller features. Centroid containment catches these as
low-tier matches and distinguishes them from accidental sliver
overlap. About 13% of all matches in this demo come through the low
tier.

**Centroid containment is directional.** The criterion is *Overture
centroid inside MGCP polygon*, not the other direction. This works when
MGCP is the coarser side, which holds for buildings but may be backwards
for `base/land_cover` and similar passes where Overture polygons can be
larger. A production pipeline would want either a symmetric check or
per-pass direction.

**A note on units.** IoU and centroid containment depend on geometric
operations that need consistent units. The raw data on both sides is in
`EPSG:4326` (degrees), where a degree of longitude varies by latitude.
We reproject both sides to `EPSG:32617` (UTM Zone 17N, meters) for the
demo tile; a different geography would use a different UTM zone or a
global equal-area projection.

**Seven passes, deliberately ordered.** The passes run from cleanest
case to messiest: `buildings/building` first, then `buildings/building_part`,
then the adjacent `base` themes (`infrastructure`, `land_use`, `water`),
then the cross-schema friction cases (`base/land`, `base/land_cover`). The
order matters for reading the results: by the time you've understood how
buildings behave, you have a baseline for what fragmentation in the
land-cover pass means.

## Matching results

### The clean case: buildings

The `buildings/building` pass is the methodology working in its best
case. Both schemas agree on what a building is: a discrete polygon
footprint. Of 412 MGCP AL015 buildings in the cell, 350 (85%) found an
Overture counterpart, and 347 of those (99%) landed in the "clean"
cardinality bucket. This is the case where direct GERS ID attachment
works without further mechanism, and it's also the baseline against
which to read every other pass.

### Building parts: schema design surfaces in the geometry

The `buildings/building_part` pass surfaces only 11 matches against 136
candidate MGCP buildings. This isn't a failure of the methodology; it's
MGCP and Overture modeling building substructure differently. MGCP
captures a building as one feature. Overture follows OSM in optionally
capturing parts (wings, projections, roof sections of different heights)
as separate features that sit on top of the parent building.

The right GERS integration for `building_part` isn't direct matching at
all. It's through the parent building's GERS ID established in the
previous pass. The matching methodology surfaces this as a low match
count, which is the right diagnostic behavior.

### Adjacent themes

The next three passes (`base/infrastructure`, `base/land_use`,
`base/water`) exhibit similar behavior to buildings at smaller volume:
69, 59, and 16 matches respectively. The cardinality is mostly clean,
with occasional aggregation. AM070 Storage Tank (59 polygons, 100%
match, 100% clean) is the standout: storage tanks are large, discrete,
isolated features that both schemas capture the same way. A few
less-common fcodes (AD010 Electric Power Station, AD030 Power
Substation, GB015 Apron) match at 100% clean but appear only once or
twice; in denser data they resolve into the same category.

### Cross-schema friction: land and land cover

The last two passes (`base/land` and `base/land_cover`) produce 125 and
247 matches respectively, the largest non-building pass totals. They're
where the cardinality diagnostic stops being decorative.

MGCP's specific vegetation and terrain codes (EB020 Thicket, EC030
Trees, BA030 Island) capture distinctions that Overture's broader land
taxonomy doesn't preserve. The result is fragmentation: a single
Overture land polygon may overlap several MGCP polygons with different
fcodes, or a single MGCP polygon may straddle several Overture polygons.

BA030 Island at 66% match rate but 3% clean rate is the standout
illustration. Two-thirds of the islands found a match, but almost none
of those matches were clean: Overture typically splits a single MGCP
island into multiple land polygons along internal coastline detail. The
methodology correctly surfaces these as matches, and the cardinality
classifier correctly surfaces them as fragmented or mixed. This is the
case the cardinality diagnostic is *for*.

## Cardinality reporting

A matched pair on its own doesn't tell us much about how to integrate
two datasets. What matters is the *pattern* of matches: does each MGCP
polygon correspond cleanly to one Overture feature, or does it overlap
many smaller ones? Are there MGCP features that match nothing at all?

We classify each MGCP polygon's match pattern per pass, then aggregate
across all seven passes into a global label per polygon. The global
categories are:

- **clean** — every matched pass is 1:1
- **aggregated** — at least one pass where one MGCP polygon matched
  multiple Overture features
- **fragmented** — at least one pass where multiple MGCP polygons
  matched the same Overture feature
- **mixed** — both aggregated and fragmented patterns across passes
- **unmatched** — no Overture matches in any pass

The 0:1 case (Overture has a feature, MGCP doesn't) is reported
separately per pass, since it isn't a property of any MGCP UID.

**The unmatched bucket needs careful reading.** It is *not* an audit
result. A polygon in the unmatched bucket might be an Overture coverage
gap, a feature that no longer exists on the ground, a real match where
the geometries don't clear the IoU thresholds, or a feature MGCP
captured at 1:100K that simply has no Overture polygon counterpart at
any scale. The methodology can't distinguish these on its own; that
requires extraction policy, ground truth, or auxiliary data. The same
caveat applies in the 0:1 direction.

For deciding what to do about GERS adoption, the relevant unit isn't
the dataset as a whole; it's the feature code. The notebook
cross-tabulates the five categories per feature code, and the patterns
it surfaces are what the next two sections turn into adoption decisions.

## The two-rate diagnostic

The cross-tab is informative but dense. The two-rate diagnostic
compresses it into two numbers per feature code:

- **Match rate** — of all polygons in this feature code, what fraction
  found any Overture match? (The inverse of the unmatched rate.)
- **Clean rate** — of the polygons that matched, what fraction matched
  cleanly 1:1 on every pass?

The two move independently, and the combination is more informative
than either alone:

| Pattern | Example (this cell) | What it means |
|---|---|---|
| High match, high clean | AL015 Building (85% / 99%) | Most polygons match; almost all are clean. Direct GERS ID works. |
| Low match, high clean | BH080 (32% / 100%) | When it matches, it matches well. Coverage gap, not schema mismatch. |
| High match, low clean | BA030 Island (66% / 3%) | Coverage is fine, but matches fragment. Needs a link table. |
| Zero match | BA040 Tidal Water, BH140 River | No polygon counterpart at all. Defer to a different geometry or theme. |

Codes that fall in between on both axes (EC030 Trees at 45% / 41%,
DA010 Soil Surface Region at 27% / 48%) need case-by-case judgment.
Clean rate is undefined when match rate is zero; the matrix in the
next section handles this by checking match rate first.

## GERS adoption decision matrix

The two rates per feature code, combined with a minimum-sample
threshold, produce a categorical assignment. The notebook computes this
with explicit thresholds (`MATCH_RATE_HIGH = 80`, `CLEAN_RATE_HIGH = 80`,
`MIN_SAMPLE = 5`) that classify each fcode into one of five buckets:

- **Direct GERS ID attachment.** High match rate, high clean rate. The
  MGCP feature carries a GERS ID directly, and downstream joins work
  without further mechanism.
- **Link table.** High match rate, low clean rate. A `(mgcp_uid,
  gers_id)` crosswalk handles the many-to-one or one-to-many cases.
- **Deferred.** Zero match rate. Integration needs a different geometry
  type or theme.
- **Review.** Partial match rate, mixed clean rate. Human judgment
  needed.
- **Insufficient sample.** Below the minimum sample threshold.

The notebook shows the full matrix. One finding from that run is worth
surfacing in prose.

### The link-table bucket is nearly empty

The skeleton anticipated this bucket would be substantial: feature codes
that match often but fragment when they do. The matrix run disagrees.
The codes that fragment in this cell (BA030 Island, EC030 Trees) have
moderate match rates, not high ones, so they land in `review` rather
than `link table`. The codes with high match rates don't fragment.

This is a finding about the data, not a flaw in the methodology. At the
1:100K capture scale of the Bahamas cell, the cardinality problem
appears to be largely binary: feature codes either match cleanly or
don't match at all, with the "matches frequently but messily" middle
ground appearing more rarely than expected. Whether this generalizes to
other MGCP cells, to TDS v7, or to denser capture scales is exactly the
kind of question the next iteration should investigate.

The 80/80 thresholds are conservative. Lowering `MATCH_RATE_HIGH` to 50
would pull moderate-match codes into `link table`, making the matrix
look more like the skeleton expected, at the cost of recommending
direct or link-table adoption for codes that match less than two-thirds
of the time. The notebook makes the thresholds visible at the top of
the classifier cell.

## Limitations and next steps

This demo is what it is: a methodology demonstration against one MGCP
cell. What it shows is encouraging but not generalizable.

- **Polygon-only matching.** The bulk of MGCP's feature coverage at
  1:100K is captured as points. Point-in-polygon matching is the
  natural follow-on.
- **The Bahamas cell is sparse.** Mostly ocean, 1:100K, single
  contributor, 2015. The methodology behaves differently at higher
  densities and with more recent data.
- **The two-tier IoU rule wasn't specifically validated for cross-scale
  matching.** The ~13% low-tier rate suggests it's catching real
  matches, but the rule's behavior under very different capture scales
  is worth characterizing more rigorously.
- **Centroid containment direction is asymmetric** in a way that may be
  backwards for `base/land_cover` and similar passes.
- **Schema version is TRD 3.0, not operational current.** Running the
  methodology against TDS v7 or current MGCP TRD 4 is the natural next
  test.

The matrix doesn't tell you what to do; it tells you which decisions to
make and on what evidence. For the data shown here, the decisions are:
direct GERS adoption for buildings, defer water-line features to a
different theme or geometry type, and review the middle band case by
case.

## References

- Overture's [GERS documentation](https://docs.overturemaps.org/gers/).
- The [Overture schema reference](https://docs.overturemaps.org/schema/reference/buildings/building/)
  for `buildings/building` and the `base` theme types.
- NGA's [Geospatial Analysis Integrity Tool (GAIT)](https://github.com/ngageoint/Geospatial-Analysis-Integrity-Tool)
  for the canonical MGCP TRD 3.0 attribute and feature-code
  definitions.
- The TDS DCS Extraction Guide v7.1 (NGA) for feature-code names
  shared between MGCP and TDS.
