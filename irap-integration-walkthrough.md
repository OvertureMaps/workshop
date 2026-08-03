# iRAP × Overture: integration options walkthrough

| [Home](README.md) | [<< 9. Matching linearly-referenced road networks](9-transportation-matching.md) |

This is a technical walkthrough for integrating [iRAP](https://irap.org/)
road-safety data with Overture. It supports a working session with iRAP's
software team, not a finished specification: it lays out the paths, the
trade-offs, and what each requires. The general matching methodology lives in
[Lesson 9](9-transportation-matching.md); this page is about the specific
integration decision.

Unlike an early scoping doc, this version is grounded in concrete inputs: the
iRAP × Overture discovery call, iRAP's Coding Manual (the full attribute
specification), and Overture's own Extensions framework. Where a detail still
needs confirming from iRAP's side, it's flagged.

## What iRAP data is, in Overture terms

iRAP is a global road-safety charity (~25 core staff, ~30,000 partners, 140+
countries). It assesses road infrastructure against **50-plus attributes** —
with subcategories, on the order of **200+ distinct road features** — and
produces **Star Ratings** (0–5) for car occupants, pedestrians, cyclists, and
motorcyclists, with public transport coming. To date: roughly **two million
kilometers** of Star Rating assessments and another two million of crash-history
mapping. The ratings are being adopted by UN member states, with global targets
of 75% of travel on 3-star-or-better roads by 2030, and ISO discussions underway
on the specification.

Translated into the concepts from Lesson 9, iRAP data is **linearly-referenced
attribute data along a road network**, with a specific and consequential shape:

- **Fixed 100-meter segmentation.** Assessments are coded in 100 m segments,
  each with a start and end GPS coordinate. This is *not* arbitrary linear
  referencing — it's a regular grid of fixed-length bins.
- **"Worst within 100 m" coding.** Each 100 m segment is rated by the *worst*
  instance of a feature in that stretch (e.g. the single most dangerous
  roadside object). The rating is a bin-level summary, not a point observation.
- **Per-carriageway assessment.** Each carriageway is assessed separately — both
  directions on a dual carriageway, one on a single carriageway. Survey geometry
  comes from a vehicle driving each direction (GoPro / street-view imagery,
  sometimes TomTom HD data), so a divided road is **several lines** where
  Overture typically has one.
- **Segmentation IDs are not standardized.** There is no persistent segment ID
  today; when a country re-surveys a road (say 2020 vs 2025) the segmentation
  has to be manually re-aligned. **This is precisely the problem GERS solves**,
  and it's why iRAP wants GERS IDs as a foundation.

The evolution of this is **AI RAP** — AI-accelerated data collection (computer
vision, LiDAR point clouds, and Overture data itself) aiming toward continuous
coding with exact start/end points rather than 100 m bins. A stable, globally
referenced network is a prerequisite for that to scale, which is a large part of
why iRAP is moving to a GERS-based core.

## The strategic picture (from the discovery call)

iRAP is rebuilding its core platform, **ViDA**, into **ViDA 2.0**, with GERS IDs
as a *foundational* element — this is already their committed direction, not an
open question. The partnership they want centers on doing that well. Three things
follow from the call and they shape which option applies when:

1. **Historical assessments → a one-off GERS-ification.** ~2M km of existing
   assessments would be matched to Overture's network once, so every historical
   segment carries a GERS ID. iRAP's stated preference (Greg) is to **attach to
   Overture's network geometry** — one line — rather than carry their several
   per-carriageway survey lines, "for simplicity and consistency."
2. **New assessments → GERS-native going forward.** In ViDA 2.0, a coder works
   against a road centerline that is *already* GERS-referenced, so attributes,
   crash data, Star Ratings, and fatality estimates attach to GERS IDs at
   capture time — no per-assessment matching.
3. **End state → an iRAP schema extension.** The ultimate goal is an
   iRAP-specified schema — the 50+ attributes / 200+ features — as the standard
   way to describe, e.g., the "22 pedestrian crossing types" or "20 roadside
   hazard types" that Overture's core transportation schema only covers at a
   basic level. This is an Overture **Extension**, and it's the anchor of the
   long-term partnership.

The small iRAP software team (3–4 people; technical leads **James Bradford** and
**Anne Alexander**) is looking for partnership and infrastructure support, not to
build conflation from scratch. Two pilots are on the table as first case studies:
**Brisbane** (a road-safety mapping pilot over 12 councils, all Esri shops,
starting with crash-history mapping then road attributes — the more defined
option, tied to Brisbane 2032) and a **Brazilian city** (preferred by iRAP as a
more representative data challenge; Belo Horizonte was an earlier AI RAP test
where Overture ≈ OSM). A neutral US case study (**Philadelphia**) is an option
for a first technical demo.

## How the Overture transportation pipeline works

Two facts about the transportation pipeline shape every option below, and they
change what "integrate with Overture" means for roads specifically:

- **Overture does not conflate arbitrary third-party road geometry in-house.**
  The transportation *geometry* in the reference map comes from Overture's
  road-data partner (TomTom, via the Orbis network) and is refreshed on a regular
  cadence. Overture's own pipeline assigns GERS IDs to that reference geometry and
  matches *attributes* onto it. Bringing genuinely new *geometry* into the
  reference map is coordinated with the geometry provider — the fullest form of
  integration, and a longer-term path.
- **Attributes can be associated to the reference geometry — by ID where a
  shared ID exists, by spatial match where it doesn't.** OpenStreetMap-sourced
  attributes flow in keyed on OSM IDs. A source with *no* shared IDs — which is
  iRAP's exact situation — is instead **spatially matched** to the reference
  network (a buffered geometric match), after which its attributes are merged
  onto the matched segments. Either way it's *attribute association*, not
  geometry conflation, and it's the near-term path for a dataset like iRAP's.

The practical consequence, and Overture's own guidance, is **"GERSify your
data"**: rather than expecting Overture to absorb and re-emit iRAP's road network,
iRAP attaches its attributes to Overture's reference features through GERS IDs.
Overture is the only assigner of official GERS IDs, and the concrete, repeatable
artifact it can provide external data owners is a **good bridge file with each
release** — a per-release crosswalk from the owner's IDs to current GERS IDs. For
authoritative partner data (often routed through Esri), that per-release bridge
file is the durable integration point.

The whole path — from road sources through GERS assignment to a matched sidecar
and analysis-ready output — looks like this:

![The Overture transportation pipeline: road sources conflated by the road-data
partner, GERS ids assigned by the Overture pipeline, iRAP attributes joined in as
a GERS-keyed sidecar, and the transportation-splitter emitting analysis-ready
per-segment data](img/transportation-pipeline.svg)

Two things this diagram encodes are worth stating plainly for the session: iRAP's
data enters as the **GERS-ified sidecar** (not as new geometry), and the
**transportation-splitter is the last mile**, not the matcher. Lesson 9's
[section on Overture's segmentation](9-transportation-matching.md#why-overtures-segmentation-is-its-own-thing)
explains *why* Overture's segment boundaries won't line up with iRAP's 100 m bins
— consistent sectioning, merging, ID stabilization, and linear referencing — which
is the root cause of the low clean rate the pilot will show.

### The proven pattern: transform → spatial-match → merge

This isn't hypothetical. Overture has demonstrated the exact shape iRAP needs by
bringing a public U.S. federal roads-attribute dataset (HPMS speed limits) onto
the reference network, in three steps:

1. **Transform** the raw source into Overture segment schema (class, names,
   speed limits, surface, flags, routes).
2. **Spatially match** the transformed segments to the reference (Orbis) network
   with a distance buffer — *no shared IDs required*, which is the key point for
   iRAP, whose 100 m segments carry no identifier Overture knows.
3. **Merge attributes** onto the matched reference segments with a *generic*
   merge step (join by id, then coalesce new-over-existing), designed to layer
   multiple sources with confidence/authoritativeness rules over time.

The maturity caveat matters: this pattern is **proven but not yet turnkey**.
Standing up a *new* source is still bespoke, QA-gated engineering work, geometry
still comes from the road-data partner, and merging a source into a production
release is a deliberate decision, not a self-serve pipeline. So it's a real,
demonstrated path for iRAP — but one to scope as a project, not assume as a
button. Downstream, once segments carry the merged attributes (a "sidecar"
joined by GERS ID), the [transportation-splitter](https://github.com/OvertureMaps/transportation-splitter)
produces analysis-ready per-segment data.

This is why the options below converge on GERS association and an extension rather
than on Overture "ingesting" iRAP geometry. Full geometry integration through the
road-data partner is real, but it's the longer-term, fuller-engagement option.

## The options as composing stages

These are best understood not as competing choices but as **stages that
compose**, separated by two questions: *does the data need to attach to Overture
features (GERS)?* and *who runs the matching?* Option 3 is the destination;
Options 1 and 2 are two near-term ways to GERSify, and the road-data-partner path
is the longer-term full-geometry integration.

| | Option 1: Bridge file from Overture | Option 2: iRAP matches | Option 3: Extension |
|---|---|---|---|
| **Role** | Overture assigns GERS + emits a bridge file / associates attributes by ID | iRAP runs matching in ViDA 2.0 | The end-state schema |
| **Deliverable** | Per-release bridge file (iRAP ID ↔ GERS ID) | Bridge file iRAP produces | Verified extension on `transportation` |
| **When** | Near-term, historical data keyed to stable IDs | Going-forward, GERS-native pipeline | Long-term standardization goal |
| **Who owns it** | Overture pipeline (no in-house geometry conflation) | iRAP | iRAP defines schema; Overture verifies |
| **Needs a match?** | Spatial match (no shared IDs), then attribute merge | Yes (iRAP-run) | Historical: yes. New: GERS-native |

## A decision tree

```
Does the iRAP data need to attach to Overture features (join on GERS IDs)?
│
├─ No — publish iRAP's network-with-ratings as its own rows on Overture infra
│        → Supplemental dataset (no matching, no GERS IDs; incubator path)
│
└─ Yes — attach to Overture reference features via GERS IDs
         │  (note: Overture does not conflate iRAP road geometry in-house)
         │
         Is this historical data, or new capture?
         │
         ├─ Historical (~2M km, one-off) — GERSify it
         │     │
         │     Who runs the GERS match?
         │     ├─ Overture → Option 1 (per-release bridge file; attribute-by-ID)
         │     └─ iRAP     → Option 2 (we provide tooling + guidance)
         │
         └─ New capture (ViDA 2.0) → GERS-native: attach at capture time
                │
                Do you also want iRAP's attributes standardized in Overture?
                └─ Yes → Option 3, a verified schema extension on transportation

Longer-term / fullest integration: bring iRAP geometry into the reference map
via the road-data partner (TomTom / Orbis). Higher bar, partner-coordinated.
```

---

## Option 1 — A bridge file from Overture

Within the limits of the pipeline above, this is what Overture can offer
directly, following the proven transform → spatial-match → merge pattern:
spatially match iRAP's segments to the reference network (a buffered match, since
iRAP carries no IDs Overture knows), assign GERS IDs, merge the attributes onto
the matched segments, and emit a **per-release bridge file** linking iRAP IDs to
GERS IDs (with linear-reference ranges where a correspondence splits or merges).
It's the near-term way to GERS-ify the historical archive and to prove the
approach on a pilot — *without* Overture conflating iRAP's road geometry
in-house, which the transportation pipeline does not do. Scope it as a project:
the machinery is demonstrated, but onboarding a new source is bespoke work, not a
turnkey pipeline.

**The matching itself is still a real, hard problem** — whoever runs it (iRAP in
Option 2, or the road-data partner in the longer-term path). iRAP data stresses
every hard case in Lesson 9 at once:

- **Per-carriageway vs single centerline.** iRAP's separate directional survey
  lines matching against Overture's single road line is a built-in 2:1 (or
  worse) correspondence before any attribute is compared.
- **Fixed 100 m bins vs Overture segmentation.** iRAP's regular 100 m grid will
  cut across Overture segment boundaries arbitrarily. Almost no correspondence
  will be a clean 1:1; most will be split/merge with LR ranges — which is
  exactly what the bridge file's LR columns are for.
- **Survey-vehicle geometry offset.** Lines traced from a moving vehicle sit
  meters off a reference centerline, so distance-based scores need generous
  tolerances.

None of this is a failure mode — it's the expected structure, and it's why the
match-rate/clean-rate honesty from Lesson 8 matters. Agree in advance that a low
*clean* rate is a segmentation-model difference, not a quality verdict, and that
the deliverable is an LR-ranged link table, not 1:1 adoption everywhere.

**A nuance from the call:** because iRAP wants to *attach to Overture's geometry*
rather than keep its own, the "match" here is partly a re-referencing exercise —
mapping each 100 m assessment onto a position along an Overture segment — rather
than reconciling two networks both intended to persist. That simplifies the
target (one canonical geometry) but doesn't remove the binning/offset work.

**What we need from iRAP:** network geometry, internal IDs, the 100 m
segmentation, and confirmation of how carriageways/one-way roads are modeled.

## Option 2 — iRAP runs the matching in ViDA 2.0

Same deliverable (a bridge file), but iRAP owns the pipeline — which is the
going-forward model, since ViDA 2.0 is being built GERS-native. Our role is
methodology and tooling transfer.

**The tools:**
[`transportation-matcher`](https://github.com/OvertureMaps/transportation-matcher)
(Python + DuckDB) to establish correspondence, and
[`transportation-splitter`](https://github.com/OvertureMaps/transportation-splitter)
(PySpark) to normalize segmentation and to ingest an ID-keyed feed once the
bridge exists. Both are experimental; pin versions. Note too that the matcher in
Overture's public GERS tutorial is a deliberately simplified one — Overture's
production matcher is not yet packaged or open-sourced (there's interest in
doing so, wrapped in an easy CLI), so iRAP would be building on the experimental
tools plus their own logic in the near term.

**The highest-value thing we can give a 3–4 person team** is not the code — it's
the realistic expectation-setting the NGA workshop got: what match and clean
rates to expect on 100 m per-carriageway data, why the "column join not spatial
join" pitch is only partly true (GERS assignment is iterative, not one-and-done),
and how to read the two-rate diagnostic. Walking James and Anne through Lesson 9
+ the Lesson 8 adoption matrix on a small pilot before they scale is the point of
the technical session.

**The infrastructure angle.** iRAP's own framing is that this is an
*infrastructure* problem more than an expertise gap — compute to run iterative
spatial joins at 2M-km scale, and not passing conflation cost onto their
partners. That's worth keeping in view: the pilot proves the method; scaling is a
separate conversation (possibly with Esri/TomTom doing GERS-ification at scale).

## Option 3 — An iRAP extension (the destination)

Options 1 and 2 produce a *link*. Option 3 is about iRAP's rich attribute
schema living **in the Overture ecosystem** as a standard. Overture's Extensions
framework is the right lens here, and it fits iRAP almost exactly.

### How Overture's Extensions framework defines this

The framework's guiding principles are three:

- **Enable schema, don't host data.** Overture standardizes and verifies the
  *schema*; the provider keeps and serves the *data*. (This is the key
  difference from a supplemental dataset, below.)
- **Prioritize GERS, encourage any IDs.** Extensions attach to GERS-enabled
  feature types via GERS IDs; non-GERS IDs are allowed where GERS doesn't exist.
- **Govern "Verified", liberate "Community".**

And it defines two types:

- **Verified Extension** (narrow definition): a standardized way to add **new
  attributes to an existing feature type** using GERS, with the schema (plus
  sample data) reviewed by an Overture working group — earning an "Overture
  verified" badge that signals interoperability. The verification checklist:
  *does it extend a GERS-enabled feature type? does it fit the theme? does it
  come with sufficient data? SWG approval?*
- **Community Extension** (broad definition): created and shared without formal
  review — "permissionless, rapid innovation," no badge, use-at-your-own-risk.

**iRAP passes the Verified checklist cleanly:** it extends a GERS-enabled feature
type (`transportation` segment), fits the transportation theme, and comes with
substantial data (2M km). The framework's own **"Example 2: Lane-Level Driving
Extension"** is the direct analog — *"standardized schema for adding rich,
lane-level attributes to Overture's road segments, linked via GERS IDs, with
multiple providers publishing to the extended schema; Overture's role is to
verify the schema and enable richness without hosting the data."* Swap
"lane-level" for "safety attributes" and that is the iRAP extension. The
framework's use-case map even lists **Pedestrian** and **Transit** transportation
extensions as anticipated — both squarely in iRAP's wheelhouse.

### What iRAP's extension could look like

Concretely — and illustratively, not as a specification — an iRAP **Verified
Extension** on the `transportation` theme would follow the same shape as the
deck's Lane-Level Driving example:

- **Attaches to `transportation` segments via GERS IDs.** Each iRAP 100 m
  assessment rides on a segment as a **linear-referenced range**
  (`between [start, end]`), not as new geometry. Those ranges are exactly what the
  bridge file from Options 1/2 produces — the extension is what gives them a
  *standardized schema* to live in.
- **Defines a property set for the iRAP attribute families** — Star Ratings per
  mode, speed, roadside hazards, crossing types, footpath/sidewalk provision,
  delineation, and the rest of the 50+ attributes — preserving iRAP's
  "worst-within-100 m" coding as the value semantics.
- **Multiple providers publish to it.** iRAP and the national RAP programs
  (AusRAP, usRAP, …) emit to the *same* schema, so a "3-star" segment means the
  same thing everywhere and is directly comparable across countries.
- **Overture verifies the schema (plus a data sample); it does not host or
  maintain the data.** iRAP stays the steward and server of its own assessments.

A single record might look like this — one 100 m assessment, carried on a GERS
segment as an LR range:

```json
{
  "gers_id": "08f2a1b3c4d5e6f7",   // Overture segment
  "between": [0.42, 0.55],         // one 100 m iRAP bin (LR range)
  "carriageway": "left",           // each direction rated separately
  "star_rating": {                 // iRAP Star Ratings, by mode
    "car": 3, "pedestrian": 2, "bicycle": 2, "motorcycle": 3
  },
  "speed_limit_kmh": 60,
  "roadside_object_driver_side": "tree_>10cm",  // worst in 100 m
  "pedestrian_crossing": "unsignalised_marked",
  "footpath_provision": "informal_path_>=1m",
  "provider": "AusRAP",
  "assessment_year": 2024
}
```

The property names and value sets above are **illustrative** — the authoritative
ones come from iRAP's Coding Manual (one of the to-confirm items below). What
matters is the *shape*: GERS-linked, LR-scoped, multi-provider, and
schema-verified-not-hosted — the Lane-Level Driving pattern applied to road
safety. It also composes cleanly with the notebook: the bridge file's `gers_lr`
column is the `between` range, and the AusRAP attributes are the properties.

### The extension creator journey

The framework describes the provider path in three stages, with a manual MVP
today and a tooling-guided GA vision:

1. **Define & Build** — *"how do I get started?"* Today: socialize the idea in
   the working group, draft the schema (a text file), prepare a dataset. GA
   vision: a `conductor` CLI scaffolds a formally-modeled schema (pydantic-style)
   ready for validation.
2. **Publish & Verify** — *"how do I share it?"* Today: file a GitHub ticket with
   schema + data-sample links; the Schema Working Group reviews manually; if
   approved it's listed on a wiki page. GA vision: CLI validates against the
   formal schema and self-publishes to a searchable registry; the "Verified"
   badge follows automated checks + SWG approval.
3. **Maintain & Evolve** — *"how do I manage it?"* Today: manual, reactive
   (file an issue to change docs). GA vision: versioned like an NPM/PyPI package,
   with dependency management.

For iRAP, the pydantic patterns in the schema repo
([`PYDANTIC_GUIDE.md`](https://github.com/OvertureMaps/schema)) are how the
schema itself gets authored: the 100 m safety attributes as LR-scoped properties
on transportation segments, using discriminated unions, Overture numeric types,
and the project's constraint system. Coordination with **Amy Rose** and the
schema team is the concrete next step for scoping it.

### Supplemental dataset — the complementary path

A **supplemental dataset** (per Overture's supplemental-datasets process) is the
other mechanism, and it's easy to conflate with an extension but does a different
job:

- An **extension** *enables schema* — it standardizes how iRAP attributes attach
  to existing Overture (GERS) features. Overture doesn't host the data.
- A **supplemental dataset** *hosts data* — iRAP's network-with-ratings as its
  own rows on Overture infrastructure, **no GERS IDs required**, unmanaged and
  iRAP-stewarded. No cross-dataset match is needed to publish.

They compose: iRAP could publish data as a supplemental dataset *and* define a
verified extension schema — the supplemental-datasets guidance explicitly notes a
supplemental dataset can be an extension populated with data. Practically, the
supplemental path is the **low-friction on-ramp** (get iRAP data into the
ecosystem without first solving matching), and the verified extension is the
**standardization end-state** iRAP actually wants. The pilot and historical
GERS-ification (Options 1/2) are the bridge between them.

## The longer-term path: full geometry integration

Everything above attaches iRAP *attributes* to Overture's existing reference
geometry via GERS. There is a further, deeper form of integration: bringing
iRAP's road *geometry* into the reference map itself. Because Overture's
transportation geometry is supplied and conflated by its road-data partner
(TomTom / Orbis) rather than conflated in-house, this path runs **through that
partner**, where the bar for admitting new geometry is high and the cadence is
partner-driven. It is the fullest way for iRAP to engage with Overture — and the
one most aligned with an iRAP schema becoming a first-class part of the
transportation theme — but it's a longer-term option, not a starting point.

The near-term sequence is therefore: GERSify the historical data and prove the
approach on a pilot (Options 1/2), stand up the extension schema (Option 3), and
treat full geometry integration as a later milestone that the pilot and the
partnership can build toward. Framing it this way with iRAP sets honest
expectations: the immediate wins are GERS association, a per-release bridge file,
and a standardized extension; deep geometry integration is a destination, not a
day-one deliverable.

## Pilots as first case studies

- **Brisbane (Brisbane 2032).** A road-safety mapping pilot across 12 councils,
  all Esri, starting with crash-history mapping then road-attribute pilots over
  ~6 months (pending government approval). Esri is embedded with every council,
  which makes it a natural place to test GERS carry-through end-to-end. iRAP runs
  a ~60-org "Coalition of the Keen" around a "five-star journey" for the Games;
  Overture participation there is a Will/steering-level conversation, not a
  technical one.
- **Brazil (e.g. Interlagos / F1, Belo Horizonte).** iRAP's preferred data
  challenge — more representative of the global, data-sparse case where Overture
  adds the most over OSM.
- **Melbourne (AusRAP)** — the demo notebook already runs on this. AusRAP
  publishes real iRAP-methodology Star Ratings for Victoria as open data
  (CC-BY 4.0), so [notebook 5](notebooks/5-transportation-matching.ipynb)
  spatially matches ~2,300 real 100 m AusRAP bins in central Melbourne to
  Overture and emits a real bridge file — a ready, real-data starting point that
  also ties to the Australia / Brisbane 2032 context.
- **Philadelphia / other** — a neutral, data-rich case remains an easy swap if a
  different geography suits the session.

The technical demo session (James, Anne, Monica, Greg) would cover: an Overture
pipeline walkthrough (ingestion, conflation, ID assignment); the **runnable
real-data** Jupyter notebook that matches AusRAP Star Ratings to Overture and
produces a bridge file (this repo's
[notebook 5](notebooks/5-transportation-matching.ipynb)) — its headline result
(≈96% match rate, ≈1.5% clean rate on 100 m bins) is the concrete way to set the
match-rate expectations from lesson 9; then the ViDA 2.0 GERS-native approach and
the historical-data transformation path.

## Open questions to pin down

1. **Licensing.** iRAP assessment data is often restricted until a road
   authority approves release. Licensing gates the supplemental data-source
   approval and what can appear in any public sample — resolve early.
2. **Carriageway / one-way modeling.** Confirm exactly how iRAP represents dual
   vs single carriageways in the geometry, since it drives match cardinality.
3. **Attach to Overture geometry vs contribute iRAP geometry.** The call leaned
   toward attaching to Overture's network for the historical data; confirm, since
   it changes whether the pipeline emits a bridge file against contributed
   geometry or re-references onto Overture geometry.
4. **Which pilot first** — Brisbane (defined, Esri-embedded) or Brazil
   (preferred data challenge), or a neutral Philadelphia demo to start.
5. **Extension scope** — which attribute families lead (pedestrian crossings and
   roadside hazards are the richest gap vs core schema), and the schema-team
   coordination with Amy Rose.

## References

- [Lesson 9 — Matching linearly-referenced road networks to Overture](9-transportation-matching.md)
  and [Lesson 8 — Matching concepts and pipeline context](8-matching-concepts.md)
- [`transportation-matcher`](https://github.com/OvertureMaps/transportation-matcher)
  and [`transportation-splitter`](https://github.com/OvertureMaps/transportation-splitter)
- Overture Extensions framework ("Richness & Standardization") — Verified vs
  Community extensions, the guiding principles, and the Lane-Level Driving
  Extension example
- Overture schema pydantic guides (`PYDANTIC_GUIDE.md`, `README.pydantic.md`,
  `SCHEMA_CONVENTIONS.md`) for authoring the extension schema
- Overture Supplemental Datasets process for the data-hosting path
- [iRAP](https://irap.org/), [AI RAP](https://irap.org/project/ai-rap/), and
  [ViDA](https://vida.irap.org/) for the source data model

| [Home](README.md) | [<< 9. Matching linearly-referenced road networks](9-transportation-matching.md) |
