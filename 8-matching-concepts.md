# 8. Matching concepts and pipeline context

| [<< 7. Matching polygon features to Overture](7-buildings-matching.md) | [Home](README.md) |

This page builds on the two matching demos in lessons 6 and 7. It
covers the conceptual foundation for cardinality-based matching
decisions, how to iterate on a matching pipeline, and how the demo
methodology relates to the production pipelines that power Overture's
official releases.

## Why cardinality is the right diagnostic

The word "cardinality" appears throughout data engineering and GIS work,
usually in the context of database relationships. Esri's ArcGIS
documentation defines it plainly: cardinality describes how records in
two different tables relate to one another -- one-to-one, one-to-many,
many-to-one, or many-to-many -- and treats it as foundational for any
relate or relationship class.[1] Their usage, though, is about
*modeling* relationships you already understand. You know a fire station
has many personnel, so you declare that cardinality in the geodatabase
schema.

What makes cardinality useful in a matching context is different: you
don't know the relationship in advance. You discover it from the
geometry. And what you discover determines what you hand the end user.

This idea has a formal counterpart in the record linkage literature. The
standard framing, going back to Fellegi and Sunter (1969) and codified
in Peter Christen's *Data Matching* (2012), treats linking as a
classification problem: pairs of records are assigned to a match set or
a non-match set based on comparison scores.[2] The Python Record Linkage
Toolkit, a widely used open-source implementation of these methods,
makes the distinction explicit in its API: `OneToOneLinking` and
`OneToManyLinking` are separate post-classification steps, because the
*shape* of the match -- not just the score -- determines how to handle
the output.[3]

Research in large-scale record linkage has established why this matters
operationally. Moretti, Valentino, and Tuoto (2019) describe the
"selection of unique links" as a distinct phase of a record linkage
pipeline in official statistics -- a constrained optimization problem
that specifically enforces 1:1 cardinality when that's what the
application requires.[4] The key insight is that a matching algorithm
can produce high-confidence scores while still generating a match
structure that violates the cardinality the application actually needs.
Zhang, Rubinstein, and Gemmell (2014) formalize this further, showing
that enforcing 1:1 matching through bipartite graph optimization
significantly improves precision and recall compared to simply
thresholding similarity scores.[5]

The framework in this demo extends that logic into a decision tool. We
don't enforce any cardinality upfront -- we let the geometry produce
whatever structure it produces, then observe the result. Observed
cardinality at the feature-code level drives the adoption
recommendation:

- **1:1 (clean)** -- the match structure supports direct ID adoption.
  The MGCP feature can carry a GERS ID, and downstream joins work
  without further mechanism.
- **1:many (aggregated)** -- one MGCP polygon matched several Overture
  features. Direct adoption breaks; a link table is the artifact.
- **many:1 (fragmented)** -- several MGCP polygons point at the same
  Overture feature. Same result: the link table is the product.
- **unmatched** -- no Overture counterpart. Defer.

This is what the GERS adoption matrix is doing: it's cardinality,
summarized at the feature-code level, translated into a recommendation
about what kind of crosswalk artifact the downstream user actually
needs. The matching algorithm is the means; cardinality observation is
the decision mechanism.

This framing isn't standard in the geospatial literature, which tends
to treat matching as an end in itself and evaluate it on recall and
precision. The contribution here is using observed match cardinality as
the primary axis for an ID adoption decision -- treating the *shape* of
the match as the variable that determines what you build, not just
whether the match succeeded.

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

## How these demos relate to production matching pipelines

The two demos in this workshop -- LSIB boundary matching and MGCP
building matching -- are deliberate simplifications. They're designed to
be readable and runnable on a laptop, and to expose the decision points
clearly. Understanding what they leave out, and why, is part of
understanding what production conflation actually involves.

### Buildings: where the demo and production are algorithmically similar

The Overture buildings production pipeline uses the same core matching
signal as this demo: Intersection over Union (IoU), with a threshold of
0.5. That's not a coincidence -- it's the right signal for buildings
because geometry is the only reliable cross-source signal available.
Building names are sparse or absent across most sources, and the largest
source volumes come from ML-derived datasets (Microsoft, Google) that
have no stable or meaningful name attributes at all.

The production pipeline adds significant operational scaffolding the
demo doesn't have:

- **Pre-match filtering by violation type.** Buildings are checked for
  size anomalies (too small or too large for their source type),
  invalid geometries, and duplicate records before matching runs.
  The demo skips this entirely.
- **Source priority ordering.** When multiple sources produce a
  building for the same location, production resolves the conflict
  by strict priority: OSM first, then licensed government sources,
  then ML-derived sources. The demo works against a single source.
- **Cross-theme quality checks.** After matching and merging, the
  production pipeline filters buildings that inappropriately
  intersect roads, water bodies, or have digitization artifacts.
  These require having the transportation and base themes available
  alongside the buildings data.
- **Scale.** The demo processes ~1,300 polygons against Overture's
  S3 parquet files for a 1-degree cell. Production runs against
  the full global corpus, partitioned across a Spark cluster.

The matching algorithm itself -- IoU, threshold, best-match selection,
cardinality filtering -- is structurally the same. The difference is
everything around it.

### Divisions: where production is architecturally different

The LSIB boundary demo and the Overture divisions production pipeline
share a goal (linking boundary features across datasets) but use
substantially different approaches. The divisions pipeline adds three
things the demo has no equivalent of.

**H3-based blocking.** The production pipeline partitions candidate
pairs spatially using H3 cells before any scoring runs. The H3
resolution varies by administrative subtype: countries are blocked at
a coarse resolution covering hundreds of thousands of square kilometers,
while neighborhoods and microhoods are blocked at a resolution covering
less than a square kilometer. This means a candidate pair is only scored
if both features fall in overlapping H3 cells at the resolution
appropriate for their subtype. In the LSIB demo, the equivalent of
blocking is the `pair_key` join -- you only compare features that share
a country-pair code. H3 blocking is the spatial generalization of that
idea, applicable to any administrative feature regardless of whether it
carries an explicit country-code attribute.

**Multi-signal composite scoring.** The LSIB demo scores pairs on two
geometric signals: buffer overlap and length ratio. The divisions
pipeline scores on a composite of name similarity and geographic
similarity, combined with configurable weights. The composite is
evaluated under multiple weighting scenarios and the minimum score is
taken -- a conservative strategy that penalizes pairs where one signal
is strong but the other is weak. A near-perfect geometric match with a
very different name scores poorly, and vice versa. Geographic overlap is
still a signal, but it's one input into the composite rather than the
whole answer.

**Multilingual name embeddings.** Name similarity in production is
computed using a cross-lingual sentence transformer model (XLM-RoBERTa)
applied to all name variants for a feature, with average pooling across
variants. This means "München" and "Munich" produce similar embeddings
without requiring an explicit translation table. The LSIB demo has no
name signal at all -- LSIB boundaries are identified by country-pair
code, not by name.

The reason divisions needs names and buildings doesn't comes back to
the data. Every division has a name; it's the primary human-recognizable
signal for whether two features represent the same entity. Most buildings
don't have names, and for the ones that do, the name is often absent
from ML-derived sources. The matching signal has to match what's
reliably present in the data.

### History matching: what both pipelines do that neither demo does

Both the divisions and buildings production pipelines implement a form
of history-first matching: before any geometric or attribute scoring
runs, the pipeline checks whether a candidate feature was already
assigned a GERS ID in a prior release. If it was, it gets that ID back
directly, without re-running the full scoring logic.

This is the production equivalent of the iterative matching approach
described earlier in this lesson. In the demo, iteration is a manual
loop: run the matcher, inspect the unresolved cases, apply a different
strategy, append results to the crosswalk. In production, the first
iteration already happened in a previous release, and the history pass
captures its output automatically. New or changed features fall through
to the full scoring pipeline; stable features are matched by identity.

The crosswalk file this demo produces is, structurally, a hand-built
version of that history register -- a record of which external IDs have
already been resolved to GERS IDs, which can be checked before running
any geometry comparison on subsequent passes.

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

### Notes on cardinality sources

[1] Esri, "Relates and Relationship Classes Explained," ArcGIS Training
Blog, February 2022.
https://community.esri.com/t5/esri-training-blog/relates-and-relationship-classes-explained/ba-p/900757

[2] Christen, Peter. *Data Matching: Concepts and Techniques for Record
Linkage, Entity Resolution, and Duplicate Detection.* Springer, 2012.
Referenced via the Python Record Linkage Toolkit documentation.

[3] Python Record Linkage Toolkit, Classification reference (v0.15).
`OneToOneLinking` and `OneToManyLinking` classes.
https://recordlinkage.readthedocs.io/en/latest/ref-classifiers.html

[4] Moretti, Diego, Luca Valentino, and Tiziana Tuoto. "Optimization
Routines for Enforcing One-to-One Matches in Record Linkage Problems."
*The R Journal* 11/01, June 2019.
https://journal.r-project.org/archive/2019/RJ-2019-008/RJ-2019-008.pdf

[5] Zhang, Duo, Benjamin I. P. Rubinstein, and Jim Gemmell. "Principled
Graph Matching Algorithms for Integrating Multiple Data Sources." arXiv
preprint, 2014.
https://arxiv.org/abs/1402.0282

| [<< 7. Matching polygon features to Overture](7-buildings-matching.md) | [Home](README.md) |
