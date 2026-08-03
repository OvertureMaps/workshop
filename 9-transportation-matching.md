# 9. Matching linearly-referenced road networks to Overture

| [<< 8. Matching concepts and pipeline context](8-matching-concepts.md) | [Home](README.md) | [iRAP integration walkthrough >>](irap-integration-walkthrough.md) |

This lesson is the prose companion to notebook
`notebooks/5-transportation-matching.ipynb`. It extends the matching
methodology from lessons 6–8 to a harder case: linear features. Boundaries
and building footprints are areas or lines you can compare with overlap
metrics. A road network is a graph of segments whose *segmentation* — where
one segment stops and the next begins — is an arbitrary modeling choice that
differs from source to source. Matching roads means matching across those
differences.

The worked example throughout is a road-safety dataset (the kind iRAP
produces): Star Ratings and road attributes captured as measurements along
roads, keyed to the provider's own segment IDs. But nothing here is specific
to safety data. The same methodology applies to any linearly-referenced road
attribute — pavement condition, traffic counts, speed studies, incident
rates — that someone wants to join to Overture's [GERS](https://docs.overturemaps.org/gers/)
IDs.

## What makes road matching different

The two earlier demos matched *closed* geometries. LSIB boundaries (lesson 6)
matched by buffer overlap and length ratio; MGCP polygons (lesson 7) matched
by Intersection over Union. In both cases a single number summarizes how well
two shapes coincide, and the cardinality question ("does one feature match
one, many, or none?") is asked about whole features.

Roads break both assumptions.

**Segmentation is arbitrary and source-specific.** A local dataset might cut a
new segment at every stop sign, jurisdiction change, or attribute change,
while Overture represents the same stretch of road as one segment, or splits
it in entirely different places. Neither is wrong; they're different modeling
decisions. A whole-feature overlap metric compares two things that were never
meant to line up one-to-one.

**Attributes are positioned *along* a segment, not attached to it.** A Star
Rating, a speed limit, or a surface type doesn't apply to "the segment" — it
applies to a *range* along the segment. Overture models this with **linear
referencing**: a property can be scoped to a sub-range of a segment expressed
as two length-relative positions between 0.0 (segment start) and 1.0 (segment
end). Two datasets can agree perfectly about the road and still disagree about
where each attribute begins and ends.

So the unit of matching isn't the segment. It's the **subline** — a portion of
one segment that corresponds to a portion of another. Getting the methodology
right means reasoning in sublines and linear references from the start.

## Linear referencing in Overture transportation

Three feature concepts carry the whole model:

- **Segments** are the roads (and paths, rails, waterways). A road segment is
  a LineString with a class, direction, and a set of properties.
- **Connectors** are point features where segments meet. A segment references
  the connectors at and along it; connectors are what make the network a
  routable graph rather than a pile of lines.
- **Linear references (LRs)** scope a property to part of a segment. Overture
  expresses these as length-relative `between` ranges — `[0.25, 0.60]` means
  "from 25% to 60% of the way along this segment." Speed limits, access rules,
  surface, width, and lane information are all commonly LR-scoped.

A consequence worth internalizing early: **an external dataset's segment IDs
are meaningless inside Overture, and Overture's `id` values are meaningless in
the external dataset.** The entire job of matching is to build the crosswalk
between them — and because segmentation differs, that crosswalk is often not
one row per segment but one row per subline correspondence, carrying the LR
range on each side.

## Two tools, two jobs

Overture has open-sourced two experimental tools that together cover the road-
matching workflow. They do different jobs and are usually used in sequence.

### transportation-splitter — normalize segmentation

[`transportation-splitter`](https://github.com/OvertureMaps/transportation-splitter)
is a PySpark application that splits Overture transportation segments at all
their connectors and all their `between` LR points, producing sub-segments
that have exactly two connectors (one at each end) and **no linear
references**. Every attribute change becomes a segment boundary, so the output
is a network where "the segment" and "the attribute range" finally coincide.

![One LR-scoped Overture segment, split at its connectors and linear-reference
points into plain per-segment sub-segments](img/transportation-splitter-object-model.svg)

The diagram is the whole idea: a single Overture segment carries an attribute on
a `between [0.1, 0.6]` range and keeps one stable GERS id; the splitter cuts it
at every connector and every LR boundary so each resulting sub-segment has two
connectors, no LRs, and a value that applies to its entire length. Note what the
splitter is *not* — it does not match anything and it does not raise a match
rate. It makes an already-referenced network simpler to consume, which is why it
belongs to the last mile, not the matching step.

This matters for matching in two ways:

1. **It removes linear referencing as a variable.** Once both sides are split
   so that attributes are constant along each sub-segment, you're comparing
   like with like.
2. **It ingests external feeds directly.** The splitter's documentation calls
   this out explicitly: if you have a data feed that maps Overture segment IDs
   to other properties — with `between` LR fields or not — you can consolidate
   it into a single parquet via a trivial join on `id`, then run the splitter
   *once* to produce easy-to-consume split segments. This is exactly the shape
   of a road-safety feed that has already been matched to Overture: the
   splitter turns LR-scoped attributes into plain per-segment attributes.

The splitter is the tool for the *last* mile — after a crosswalk exists, or
when the external data already references Overture IDs. It is not itself a
matcher.

### transportation-matcher — find the correspondence

[`transportation-matcher`](https://github.com/OvertureMaps/transportation-matcher)
is a Python + DuckDB tool whose one-line description is the whole problem
statement: "matching linearly-referenced road networks with differing
segmentations." It's the tool for the *first* mile — establishing which part
of which external segment corresponds to which part of which Overture segment,
when no shared ID exists yet.

Its design draws a clean line between two kinds of operation, and the
distinction is worth adopting in your own thinking even if you never use the
tool:

- **Scoring** — single-row operations that generate a score for a candidate
  pair. Geometry (Euclidean distance, parallelism, offset), topology
  (connector placement, broader graph similarity), and metadata (name and tag
  similarity) each produce scores.
- **Inference** — multi-row operations that interpret those scores: updating
  them based on neighbors, and ultimately deciding which candidates are
  matches.

Keeping scoring and inference separate is what makes a matching pipeline
reconfigurable. You can add a new geometric score without touching the
decision logic, or change the decision threshold without recomputing
geometry.

## The subline matching pipeline

The matcher's suggested approach — and a good mental model regardless of
tooling — is five steps:

1. **Spatial join** segments into a table of candidate pairs. Only pairs whose
   geometries are close enough to plausibly match are considered; this is the
   linear-network equivalent of the blocking step in lesson 8.
2. **Compute linear references** for each candidate pair — the sublines that
   indicate how one segment maps onto the other. This is the step that makes
   the method segmentation-agnostic: a candidate isn't "segment A matches
   segment B," it's "the [0.0, 0.4] subline of A corresponds to the
   [0.6, 1.0] subline of B."
3. **Score the sublines** with as many algorithms as apply.
4. **Update scores using topology** — a subline whose neighbors match well is
   more likely a real match; connector agreement reinforces or undercuts a
   geometric score.
5. **Infer matches** from the (possibly updated) scores.

The subline idea is related to the maximal-subline approach in NGA's
Hootenanny conflation engine, though the implementations differ. The key point
is that segmentation is not discarded — it's often meaningful (a segment break
frequently marks a real change on the ground) — but it is *not assumed to
agree* between sources.

## Reading the results: cardinality for linear features

Lesson 8 argued that observed match *cardinality* — not just the match score —
is the diagnostic that tells you what crosswalk artifact to build. That holds
for roads, but the categories take a linear-network form:

- **1:1 clean** — one external segment corresponds to one Overture segment
  along their whole length. Direct GERS ID adoption works: the external
  feature can carry the Overture `id`.
- **Split (1:many)** — one external segment spans several Overture segments.
  The crosswalk needs LR ranges to say which part goes with which — one
  external ID maps to several `(gers_id, start_lr, end_lr)` rows.
- **Merge (many:1)** — several external segments fall along one Overture
  segment. The Overture segment carries several external IDs, each on its own
  LR range.
- **Partial / offset** — the sublines overlap but don't cleanly nest, usually
  from digitizing offset or a genuine geometry disagreement. These need review.
- **Unmatched** — no Overture counterpart clears the thresholds.

As in lesson 8, the two-rate diagnostic compresses this: a **match rate** (what
fraction of external segments found any Overture correspondence) and a **clean
rate** (of those that matched, what fraction were 1:1 along their whole
length). The two move independently, and the combination tells you whether
you're looking at a coverage gap, a segmentation-model difference, or a clean
adoption case.

## Why road match rates come in lower than you expect

This is the single most important expectation to set with any partner before a
matching project starts, and it's worth being as direct about it as the MGCP
demo was about the sparse Bahamas cell. In the NGA workshop, the headline
finding was that a plausible-looking pipeline still left a large fraction of
features in the unmatched or review buckets — not because the method was
broken, but because the two datasets genuinely disagreed about what and where
the features were. Linear road matching has the same property, amplified by
several road-specific factors:

- **Segmentation mismatch inflates the "messy" buckets.** When neither side
  agrees on where segments start and stop, more correspondences are splits and
  merges than clean 1:1 — even when the geometry is excellent. A low clean
  rate here is a modeling-difference signal, not a quality failure.
- **Digitizing offset breaks distance-based scores.** Two sources tracing the
  same road from different imagery can sit tens of meters apart. Divided
  highways, where each direction is a separate line, are a frequent source of
  ambiguous or double matches.
- **Directionality and one-way modeling differ.** One source may model a dual
  carriageway as one bidirectional line, another as two one-way lines. That's
  a 1:2 correspondence before any attribute is even compared.
- **Coverage genuinely differs.** New roads, private roads, service roads, and
  paths are present in one dataset and absent from the other. An unmatched
  external segment may simply have no Overture counterpart yet.
- **The unmatched bucket is not an audit result.** Exactly as in lesson 8: a
  segment can be unmatched because of a coverage gap, a real-world change, a
  geometry that just missed the threshold, or a modeling difference — and the
  matcher cannot tell these apart on its own. Reporting an unmatched rate as a
  "quality score" for either dataset is a misread.

The productive framing for a partner is the one lesson 8 lands on: the matrix
doesn't tell you the datasets are bad, it tells you which decisions to make and
on what evidence. A lower-than-hoped clean rate usually means "build a link
table with LR ranges," not "the match failed."

## The deliverable: a bridge file

The artifact a matching project produces is a **bridge file** (or link table):
a stable crosswalk between the provider's internal IDs and Overture GERS IDs.
For linear data it carries the LR ranges that a split/merge correspondence
requires:

| provider_id | gers_id | provider_lr | gers_lr | match_type | score |
|---|---|---|---|---|---|
| `R-1042` | `08f2a…` | [0.0, 1.0] | [0.0, 1.0] | clean | 0.97 |
| `R-1043` | `08f2b…` | [0.0, 0.55] | [0.30, 1.0] | split | 0.88 |
| `R-1043` | `08f2c…` | [0.55, 1.0] | [0.0, 0.42] | split | 0.85 |

Once the bridge file exists, either party can join the other's attributes
without the matching pipeline needing to understand what those attributes
mean — the same separation-of-concerns principle from lesson 7. And if the
provider's feed is expressed against Overture IDs (via the bridge), running it
through the transportation-splitter produces analysis-ready per-segment data.

## How this relates to Overture's production pipeline

As with the buildings and divisions demos in lesson 8, the workshop tooling is
a deliberate simplification. `transportation-matcher` is explicitly
experimental — one of its stated goals is to "start the long process of
building up Overture's own internal conflation tooling," with the possibility
of scaling into the production transportation pipeline later. Treat it as a
methodology you can run and reason about on a laptop, not as the production
conflation engine. The production concerns it doesn't fully address are the
familiar ones: planet scale, history-first matching (reusing a prior release's
IDs before re-scoring), and the operational scaffolding around source
priority and quality checks.

One thing specific to the transportation theme is worth knowing when you plan an
integration: Overture's road *geometry* is supplied by a data partner and
conflated upstream, rather than conflated from arbitrary contributed networks
inside Overture's own pipeline. Overture assigns GERS IDs to that reference
geometry and matches *attributes* onto it by stable identifier. The practical
implication for anyone bringing a road dataset is that the reliable integration
point is **attribute association via GERS** — matching your data to the reference
network to obtain GERS IDs, then attaching your attributes — plus, for data
owners, a per-release bridge file. Merging new *geometry* into the reference map
is a separate, upstream process. This is why the bridge file (not a promise to
absorb your geometry) is the durable artifact.

### Why Overture's segmentation is its own thing

Lesson 9 opened with the claim that segmentation is an arbitrary, source-specific
modeling choice. There is a specific reason your dataset's boundaries will rarely
line up with Overture's: Overture deliberately does **not** inherit a source's
segmentation. A source typically starts a new segment wherever an attribute
changes — add a parking rule to one side of a street and the line gets cut there.
Overture instead applies a **consistent, predictable sectioning strategy** aimed
at a stable network for routing, and pushes attribute variation into linear
references rather than into new geometry. Four ideas do the work:

- **Sectioning** — segments are cut at genuine decision points (where the network
  topology changes), not wherever an attribute happens to change.
- **Merging** — runs a source split only because of an attribute edit are merged
  back into one segment.
- **ID stabilization** — because geometry does not churn on every attribute edit,
  a segment keeps its GERS id release over release instead of being reissued.
- **Linear referencing** — the attribute that would have caused a split is
  attached to a `between` range on the stable segment instead.

The payoff is what makes GERS useful: a segment's id is **insensitive to
attribute changes**. The cost, for anyone matching in, is exactly this lesson's
subject — your boundaries and Overture's were drawn on different principles, so
most correspondences come out as splits and merges, and the splitter is what
reconciles the two segmentations *after* a match exists.

Putting the pieces together, this is the path a road-attribute dataset like
iRAP's travels to become analysis-ready Overture data — matching produces the
GERS-keyed sidecar (the bridge file), and the splitter is the last mile:

![The Overture transportation pipeline: road sources are conflated by the
road-data partner, the Overture pipeline assigns GERS ids, your matched
attributes join in as a GERS-keyed sidecar, and the transportation-splitter emits
analysis-ready per-segment data](img/transportation-pipeline.svg)

## Limitations and next steps

- **The matcher and splitter are experimental.** APIs and behavior will change
  before a stable release. Pin versions for any reproducible run.
- **Scoring choices are workload-specific.** The right geometric, topological,
  and metadata scores depend on the external dataset's density, accuracy, and
  attribute richness. There is no single threshold that generalizes.
- **Directionality handling needs care.** Decide up front how the external
  dataset models one-way and divided roads, because it drives the cardinality
  you'll observe.
- **Validation needs ground truth.** The match-rate and clean-rate numbers
  describe the *correspondence structure*, not correctness. Confirming that a
  match is right still requires sampling against imagery or a reference.

## References

- [`transportation-matcher`](https://github.com/OvertureMaps/transportation-matcher)
  — Python + DuckDB matcher for linearly-referenced road networks; see
  `docs/overview.md` for the scoring/inference split and the subline pipeline.
- [`transportation-splitter`](https://github.com/OvertureMaps/transportation-splitter)
  — PySpark tool for splitting segments at connectors and LR points, and for
  ingesting external LR-keyed feeds by Overture `id`.
- Overture's [transportation schema](https://docs.overturemaps.org/schema/reference/transportation/segment/)
  for segments, connectors, and linear referencing.
- Overture's [GERS documentation](https://docs.overturemaps.org/gers/).
- Lesson 8, [Matching concepts and pipeline context](8-matching-concepts.md),
  for cardinality as a decision diagnostic and the two-rate framing.
- NGA's [Hootenanny](https://github.com/ngageoint/hootenanny) conflation
  engine for the maximal-subline lineage.

---

For a concrete application of this methodology to a real integration
decision — including when to match versus when to model the data as a schema
extension or supplemental dataset — see the
[iRAP integration walkthrough](irap-integration-walkthrough.md).

| [<< 8. Matching concepts and pipeline context](8-matching-concepts.md) | [Home](README.md) | [iRAP integration walkthrough >>](irap-integration-walkthrough.md) |
