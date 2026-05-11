# Matching MGCP polygon features to Overture

This lesson is the prose companion to notebook `4-buildings-matching.ipynb`.
The notebook contains the runnable demo; this page explains what the demo is
doing, why the methodology is designed the way it is, and how to read the
results it produces.

> **Status:** skeleton. Many sections are TODOs that point at material in the
> notebook or at design choices we've already made. Will be filled out in a
> follow-up pass.

## What this demo does

Two open geospatial datasets — NGA's MGCP and Overture — each describe the
same real-world places, but with different schemas, different capture
scales, and different decisions about what counts as a "feature." This demo
walks through a methodology for matching polygon features between them and
producing a stable [GERS](https://docs.overturemaps.org/gers/) link table
that can serve as the join key for downstream data integration.

> **TODO:** Expand. Worth landing here: the link table is the deliverable;
> attribute translation is a separate exercise; the methodology is geometry-
> based and schema-version-agnostic. The conversation about *why* this
> matters (third-party data flow-in, cross-dataset alignment) lives in the
> teaching notes, not in the public lesson.

## Schema landscape

A short orientation to the standards in play: MGCP, TRD, TDS, DGIWG, and
how GERS relates to all of them.

> **TODO:** Write this. Generic and public-facing — not engagement-specific.
> Cover: MGCP as a multinational topographic data program; TRD as the spec
> family; TDS as a related NGA schema; DGIWG as the standards body; GERS as
> a stable reference-ID system that doesn't replace any of these but sits
> alongside them. A diagram would help here.

## The demo data

The demo runs against the W079N26 MGCP cell (Bahamas, TRD 3.0) matched
against seven Overture types covering buildings and the polygon-geometry
types within the `base` theme.

> **TODO:** Brief framing. The Bahamas cell is sparse — most of the cell is
> ocean, capture is at 1:100K, and MGCP captures most small features as
> points rather than polygons. Acknowledge openly that this isn't a stress
> test of the methodology; it's the publicly-shareable demo data we have.
> The methodology extends to TDS v7 and current MGCP TRD 4 by changing the
> input filter; the matching code is unchanged.

## Schema comparison

Before matching, it's worth understanding what each side actually captures.

> **TODO:** Lift from the notebook's "Schema comparison" cells. The point of
> the comparison isn't to translate attributes between schemas — it's to
> orient anyone who's going to do something with the matched results.
> Attributes stay on whichever side captured them.

## Matching methodology

For each pair of polygons, we compute Intersection over Union (IoU) and
centroid containment. A pair is considered a match if it meets one of two
criteria: IoU ≥ 0.5 (high tier), or IoU ≥ 0.3 with the Overture centroid
contained in the MGCP polygon (low tier).

> **TODO:** Expand. Worth landing: why two tiers rather than one; why
> centroid containment is asymmetric; why we reproject to a metric CRS.
> Surface the cross-scale matching tradeoff — the rule wasn't specifically
> validated for matching across very different capture scales, and the
> ~13% low-tier rate is itself informative about how often the looser
> criterion is doing work.

## Matching results

The demo runs seven independent passes — one per Overture type — and
classifies the results. We present them in a deliberate order that builds
from the cleanest case to the messiest.

### The clean case: buildings

> **TODO:** Lead with `buildings/building`. ~99% of matched MGCP buildings
> land in the "clean" cardinality bucket. This establishes that the
> methodology works when both schemas agree on what counts as a feature.

### Building parts: schema design surfaces in the geometry

> **TODO:** Building_part as a low-match-count case. The 11/136 result isn't
> about MGCP's resolution; it's about MGCP and Overture modeling building
> sub-structure differently. Worth a paragraph because it's the cleanest
> example of "the matching methodology surfaces schema design differences
> directly through match counts."

### Adjacent themes

> **TODO:** `base/infrastructure`, `base/land_use`, `base/water`. Similar
> behavior to buildings at smaller volume. Mostly clean, with some
> aggregation. Storage tanks and power substations are the standout
> "trivial adoption" cases.

### Cross-schema friction: land and land cover

> **TODO:** `base/land` and `base/land_cover` are where the methodology
> earns its keep. MGCP's specific vegetation/terrain codes (EB020 Thicket,
> EC030 Trees, BA030 Island) fragment against Overture's broader land
> taxonomy. This is the case the cardinality diagnostic is *for*. Use
> BA030 Island (3% clean rate when matched) as the standout illustration.

## Cardinality reporting

For each MGCP polygon, we classify the match pattern into one of five
categories:

- **clean** — every matched pass is 1:1
- **aggregated** — at least one pass where one MGCP polygon matched
  multiple Overture features
- **fragmented** — at least one pass where multiple MGCP polygons matched
  the same Overture feature
- **mixed** — both aggregated and fragmented patterns appear across passes
- **unmatched** — no Overture matches in any pass

The 0:1 case (Overture has a feature, MGCP doesn't) is reported separately
per pass, since it isn't a property of any MGCP UID.

> **TODO:** Lift the cardinality discussion from the notebook. Two important
> framings to preserve from this session: (1) the unmatched bucket isn't an
> audit result — it includes legitimately-uncaptured features per MGCP's
> 1:100K extraction policy, not just "missed" features; (2) the
> distinction between "missed" and "legitimately uncaptured" requires
> domain knowledge the cardinality table can't provide on its own.

## The two-rate diagnostic

Two summary numbers per MGCP feature code tell most of the story: the
**match rate** (what fraction of polygons in this feature code found any
Overture match) and the **clean rate** (of those that matched, what
fraction matched cleanly with no fragmentation or aggregation).

> **TODO:** Lift from the notebook. Worth surfacing in the lesson: three
> clusters appear in the data — high match rate + high clean rate (trivial
> GERS adoption), high match rate + low clean rate (GERS adoption needs a
> link table), zero match rate (no Overture polygon counterpart;
> integration may need to happen at a different geometry level or in a
> different theme).

## GERS adoption decision matrix

Different feature codes have different cardinality signatures, and those
signatures point to different GERS adoption paths.

> **TODO:** This is the synthesis section. Three paths:
>
> - **Direct GERS ID attachment.** For high-match, high-clean feature
>   codes. The MGCP feature carries a GERS ID as an attribute; downstream
>   joins work directly. Best for AL015 Building, AM070 Storage Tank,
>   AD010 Electric Power Station, AD030 Power Substation, GB015 Apron.
>
> - **Link table.** For high-match, low-clean feature codes. Maintain a
>   (mgcp_uid, gers_id) crosswalk that can be many-to-one or one-to-many.
>   Best for BA030 Island, AK100 Golf Course, EC030 Trees, ED010 Marsh.
>
> - **No GERS adoption (yet).** For zero-match feature codes. The MGCP
>   feature has no Overture polygon counterpart in our seven passes.
>   Best for BA040 Tidal Water, BH140 River, BH020 Navigable Canal,
>   GB055 Runway, GB075 Taxiway. Likely indicates the integration should
>   happen at a different geometry level (lines, points) or that Overture's
>   coverage for that feature class is sparse.
>
> Populate the matrix with the tile's actual numbers from the cross-tab
> and two-rate views.

## Limitations and next steps

> **TODO:** Honest about what isn't in this demo.
>
> - Polygon-only matching; MGCP point features (the bulk of the data at
>   1:100K) are out of scope. Point-in-polygon matching is the natural
>   follow-on.
> - The Bahamas cell is sparse — not representative of dense operational
>   data. The methodology behaves differently at higher densities.
> - The two-tier IoU rule wasn't specifically validated for cross-scale
>   matching. The ~13% low-tier rate suggests it's catching real matches,
>   but the rule's behavior under very different capture scales is worth
>   characterizing further.
> - Centroid-containment direction is asymmetric in a way that may be
>   backwards for some passes (notably `base/land_cover` where Overture
>   polygons can be larger than the MGCP polygons they contain).
> - This demo runs against MGCP TRD 3.0. The methodology is schema-version-
>   agnostic; running against TDS v7 or current MGCP TRD 4 just changes
>   the input filter.

## Running the demo

See `notebooks/4-buildings-matching.ipynb` and the project README for setup
instructions.

> **TODO:** Brief note. The notebook expects:
>
> - The MGCP W079N26 cell unpacked into `data/mgcp/W079N26/`. Download
>   instructions are in the notebook.
> - Overture parquets cached at `data/overture_cache/`. The notebook
>   pulls these from S3 on first run (or use a pre-staged copy if
>   network access is restricted).

## References

> **TODO:** Compile. At minimum:
>
> - Overture's [GERS documentation](https://docs.overturemaps.org/gers/).
> - The [Overture schema reference](https://docs.overturemaps.org/schema/reference/buildings/building/) for `buildings/building` and the `base` theme types.
> - NGA's [Geospatial Analysis Integrity Tool (GAIT)](https://github.com/ngageoint/Geospatial-Analysis-Integrity-Tool) for the canonical MGCP TRD 3.0 attribute and feature-code definitions.
> - The TDS DCS Extraction Guide v7.1 (NGA) for feature-code names shared between MGCP and TDS.
