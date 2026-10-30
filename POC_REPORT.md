# Onedata Intermediate Metadata Object: architecture POC

This is the historical report for the original RDFLib experiment. Its test
counts and measurements refer to the run dated below. The current direct
JSON-LD implementation and architecture are documented in
[`docs/`](docs/README.md); the original implementation remains for comparison.

## Scope and research assumptions

This experiment was executed on 2026-10-28 with Python 3.12.3, RDFLib 7.6.0,
lxml 6.1.3 and pytest 9.2.0. The demonstration and all **17 automated tests passed**. Dependency consistency
was also checked with `pip check`. RDFLib emits upstream JSON-LD deprecation
warnings; the README records them. All example outputs are provided under
[`examples/output/`](examples/output/). The implementation is independent of
Onedata and replaces only the workspace's starter `main.py`.

Adam Biśta's thesis, the FDIM/FAIR article and a specific FAIR compliance
document were not attached or found in the workspace. Searches did not identify
the thesis/article unambiguously; no findings are attributed to them. The
public [Onedata metadata documentation](https://onedata.org/docs/25/user-guide/metadata/)
was available: it distinguishes filesystem attributes, extended attributes and
schema-independent custom JSON/RDF on files/directories. The
[Public Data guide](https://onedata.org/docs/25/user-guide/public-data/)
also describes PID/DOI registration, Dublin Core/EDM annotation and OAI-PMH
advertising; this supplies publication context, not a FAIR compliance assessment.
This POC assumes the
prompt's pipeline, not knowledge of an existing implementation. It does not
measure FAIR compliance. File metadata and descriptive metadata remain separate
concepts even when displayed in the same graph.

Adapters deliberately target a subset of
[DataCite 4.6](https://datacite-metadata-schema.readthedocs.io/en/4.6/properties/)
and the current online
[EDM mapping guidance](https://europeana.atlassian.net/wiki/spaces/EF/pages/987791389/EDM%2B-%2BMapping%2Bguidelines).
This is a reproducibility choice: DataCite 4.7 is now available, as recorded in
the [official introduction](https://support.datacite.org/docs/datacite-metadata-schema).
A schema/profile version must accompany future adapters.

## Representation comparison

These ratings are architectural assessments informed by the experiments, not
benchmark results. DataCite and RO-Crate are profiles/models, whereas JSON-LD is
a serialization and RDF is a data model; they are not exclusive alternatives.

| Candidate | Extensibility and expressiveness | Preservation / round trip | Dataset, directory, file | Semantics and implementation / Erlang |
| --- | --- | --- | --- | --- |
| JSON-LD + small profile | Open vocabulary graph; rich typed links and contextual entities | Native RDF terms survive; JSON field order, qualifiers and duplicates need explicit treatment | Shared envelope; type-specific constraints | RDF-native; context processing and graph scoping add complexity. JSON maps are straightforward in Erlang, a conformant JSON-LD processor is additional work |
| DataCite canonical | Strong citation-oriented fields and controlled qualifiers; arbitrary domain detail needs an extension policy | Excellent fit for DataCite; EDM aggregation, digital-vs-physical scope and arbitrary RDF do not fit naturally | Can describe varied research outputs; containment through typed related identifiers, not an operational filesystem manifest | Simple JSON records in Erlang; flattening graphs and satisfying required target fields remain difficult |
| RO-Crate canonical | JSON-LD profile for research-object packages and contextual/provenance entities | Flexible extensions preserve RDF; not a solution to non-RDF source fidelity | Strong native packaging vocabulary for datasets, directories and files | Existing profile avoids some invention; package root, identity, descriptor and context conventions constrain an internal model |
| Custom JSON canonical | Any structure we design, easy validators; requires maintaining every field's definition | Can preserve structured source records exactly; semantic interoperability then depends on bespoke mappings | Easy tagged union or common record with type-specific fields | Simplest initial Erlang implementation; vocabulary, links, cardinality and evolution become Onedata's responsibility |
| RDF dataset + JSON-LD/TriG serializations | Same graph design without making JSON layout the conceptual model | Natural source graph isolation and provenance; ordered source data still needs modelling | Same shared entity graph | Good conceptual alternative; store normalized node maps or quads and serialize at boundaries |
| DCAT 3 application profile | Established dataset/catalog/distribution semantics | Helpful for publishing datasets, insufficient for arbitrary EDM source detail | Distinguishes a dataset from an accessible representation; a directory is not automatically a distribution | Candidate export/profile layer, not evaluated as a working adapter here |

[RO-Crate 1.2](https://www.researchobject.org/ro-crate/specification/1.2/)
is the fixed comparison baseline, not a claim about the latest release. Its
[data-entity rules](https://www.researchobject.org/ro-crate/specification/1.2/data-entities)
make it a strong alternative when packaging dominates requirements. The
[DCAT 3 recommendation](https://www.w3.org/TR/vocab-dcat-3/)
is another useful vocabulary source; this POC does not implement a DCAT profile.

## Proposed IMO model

Use an **RDF dataset serialized as JSON-LD 1.1**, with three named graphs:

| Graph | Meaning |
| --- | --- |
| `urn:imo:canonical` | Selected normalized assertions used by cross-schema adapters |
| `urn:imo:source` | Native EDM triples, with original IRIs, literal datatypes, language tags and blank-node structure |
| `urn:imo:provenance` | Metadata record, conversion activity, source identifier, profile digest and labelled JSON residuals |

These identifiers are fixed per standalone IMO document. They must be scoped
per record before combining documents in a database; blindly merging multiple
documents would conflate their records and graph names. Only the canonical graph
is projected by exporters; taking the union could mix conflicting source and
normalized assertions.

The [JSON-LD recommendation](https://www.w3.org/TR/json-ld11/)
provides graph names, explicit resource references and typed/language-tagged
literals. The inline context declares prefixes only; no `@vocab` silently turns
unknown bare JSON keys into new terms. JSON-LD is neither validation nor
ontology reasoning. This POC's loader accepts exactly the pinned inline context
and rejects nested contexts, so the demo makes no remote context requests.

A reduced, valid model illustration follows; full files include provenance,
people, publisher, dates, licences and source preservation graphs:

```json
{
  "@context": {
    "schema": "https://schema.org/",
    "dct": "http://purl.org/dc/terms/",
    "imo": "https://example.org/onedata/imo/0.1/"
  },
  "@graph": [{
    "@id": "urn:imo:canonical",
    "@graph": [
      {
        "@id": "https://doi.org/10.82433/imo-demo.001",
        "@type": "schema:Dataset",
        "dct:title": {"@value": "Urban air quality observations", "@language": "en"},
        "dct:hasPart": {"@id": "https://example.org/data/aq-2025/raw/"}
      },
      {
        "@id": "https://example.org/data/aq-2025/raw/",
        "@type": ["schema:Dataset", "imo:Directory"],
        "dct:isPartOf": {"@id": "https://doi.org/10.82433/imo-demo.001"},
        "dct:hasPart": {"@id": "https://example.org/data/aq-2025/raw/stations.csv"}
      },
      {
        "@id": "https://example.org/data/aq-2025/raw/stations.csv",
        "@type": "schema:MediaObject",
        "dct:title": "stations.csv",
        "schema:encodingFormat": "text/csv",
        "dct:isPartOf": {"@id": "https://example.org/data/aq-2025/raw/"}
      }
    ]
  }]
}
```

The example-domain `imo:` namespace is a **proposal**, not a published Onedata
ontology. Its terms are limited to `Directory`, source DataCite classifications
(`dataciteResourceTypeGeneral`, `dataciteResourceType`) and preservation bookkeeping
(`sourceFormat`, `canonicalDigest`, `residual`, `jsonKey`). Existing vocabularies
supply descriptive properties and provenance. A metadata record, rather than
the described scientific object, `prov:wasGeneratedBy` the conversion activity;
the activity `prov:used` its source. These distinctions follow
[PROV-O](https://www.w3.org/TR/prov-o/).

`schema:identifier` plus `schema:PropertyValue` carries identifier scheme and
value separately. An ORCID is an identifier of an agent, not automatic proof of
identity from a name. Publisher nodes are scoped to the record. The single
string publisher in the fixture is interpreted as an organization; other
publisher forms need an adapter extension. Unknown DataCite resource classes
receive `schema:Thing`; software is not automatically classified as source code.
An EDM ProvidedCHO also receives only `schema:Thing`: cultural heritage objects
are not necessarily datasets or creative works.

## Metadata mappings

This table documents the **implemented subset**. Retaining a residual or native
property is not equivalent to implementing its canonical meaning. DCT terms
are defined in the [DCMI vocabulary](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/).

| Source | Canonical representation | Target behavior and limit |
| --- | --- | --- |
| DataCite `doi` | `schema:identifier` / PropertyValue, propertyID `DOI`; root DOI URI | Reconstruct DOI value; no resolution/registration |
| DataCite alternate identifiers | PropertyValue with original type string | Reconstruct type and value |
| DataCite title without `titleType` | `dct:title`, language-tagged literal | Reconstruct text/lang; typed titles stay in residuals |
| DataCite creators | `dct:creator` → Person, Organization or Agent; name, given/family names, identifiers, affiliation labels | Most agent data reconstructs; scheme URIs and affiliation identifiers are residuals |
| DataCite contributors | `dct:contributor` → agent | Generic contribution only; `DataCurator` role stays in residual |
| DataCite publisher | `dct:publisher` → Organization with name | Single publisher exported; ambiguous multiple publishers omitted |
| DataCite publicationYear | `dct:issued` typed `xsd:gYear` | Integer year reconstructed; not confused with object creation |
| DataCite Created / Updated / Issued | `dct:created` / `dct:modified` / `schema:datePublished` | Date strings retained; no guessing datatypes for intervals |
| DataCite Abstract / Other | `dct:abstract` / `dct:description` | Matching description types exported; Methods stays residual |
| DataCite rightsList | `dct:rights` → RightsStatement, URI and label; recognized licence URLs also `dct:license` | Text/URI reconstruct; SPDX and scheme qualifiers stay residual |
| DataCite typed relations | HasPart, IsPartOf, IsVersionOf, IsReferencedBy, References, IsDerivedFrom → matching DCT predicates (`dct:source` for derivation) | DOI/URL relations reconstruct; target resource classification stays residual |
| DataCite language/version | `schema:inLanguage` / `schema:version` | Single values exported |
| DataCite types | Schema.org broad type + explicit source classification terms | Avoid guessing DataCite class from RDF type alone |
| DataCite subjects/funding/formats/sizes | JSON residuals only | No canonical mapping implemented; size is not necessarily a file's byte size |
| EDM `dc:title` / `dc:description` | `dct:title` / `dct:description` | DataCite titles / descriptionType Other, not Abstract |
| EDM `dc:creator`, contributor, publisher | DCT links to agents; literal names wrapped in nodes; contextual labels used | DataCite agent names/publisher; contributorType needs curation |
| EDM `dc:identifier` | `dct:identifier` | Literal exported as alternate identifier with explicit `Unqualified identifier` label; not DOI |
| EDM `dc:date` | `dct:date` | DataCite dateType Other with explanatory dateInformation; not publicationYear |
| EDM `dc:language` | `schema:inLanguage` | Single text code exported |
| EDM CHO `dc:rights` | RightsStatement node and label or original resource URI | DataCite rightsList for this object only |
| EDM DCT created/issued/part links; dc:relation | Original DCT or `dct:relation` | Supported typed part links exported; generic relation lacks a safe DataCite relationType |
| EDM Aggregation/WebResource, provider, dataProvider, edm:type/rights, spatial, custom properties | Native source graph | Preserved as RDF, excluded from the narrow cross-schema projection |

The [DataCite description](https://datacite-metadata-schema.readthedocs.io/en/4.6/properties/description/)
and [date](https://datacite-metadata-schema.readthedocs.io/en/4.6/properties/date/)
qualifiers permit explicitly generic target descriptions/dates. Mapping generic
information to Other is preferable to asserting it is an abstract or publication
date. Rights URIs are not all licences; only recognized licence-document URLs
receive the extra licence assertion in this subset.

The EDM core projection accepts literal text/date values and resource-valued
relationship links. Referenced TimeSpans or concepts need additional mappings;
their IRIs are not converted into text values pretending to be dates or titles.
EDM separates ProvidedCHO, WebResource and Aggregation. Its
[Aggregation guidance](https://europeana.atlassian.net/wiki/spaces/EF/pages/2106032160)
explains the scope of `edm:rights` on digital representations. Therefore the
image's CC-BY statement is **not** copied onto the physical map. The source's
`dc:publisher` supplies publisher; its service provider names do not.

The canonical EDM exporter produces a **draft CHO view**; it cannot infer a
hosting landing page, digital representation, provider agreement or valid
Europeana aggregation. No fabricated `edm:type` is supplied. Both cross-schema
outputs require target validation and curation before submission.

## Information preservation: measured results

The experiments serialize IMO to JSON-LD and load it back before export.
EDM target XML is also reparsed before measuring graph equivalence. Results are
not comparisons of Python objects that retain hidden source state.

| Experiment | Byte equal | Structure / semantic result | Meaning |
| --- | --- | --- | --- |
| Rich DataCite → core → DataCite | No | JSON structure differs | Partial semantic projection; details below |
| Rich DataCite + residuals → DataCite | No | All 18 original top-level fields structurally equal | Source structure restored with 11 labelled residual fields |
| Independent supported DataCite subset → core → DataCite | Not asserted | Structurally equal, zero residuals | Demonstrated reversible semantic subset |
| EDM → core projection → EDM | No | Not RDF-isomorphic: 11 original triples retained, 20 removed, 1 added | Context, native qualifiers and agent URI lost in narrow projection |
| EDM → native graph → EDM | No | RDF-isomorphic: all 31 original triples, none added/removed | Native RDF preservation, not inverse canonical normalization |
| EDM → core → DataCite | N/A | Incomplete draft | Mapped fields survive; missing required target information remains explicit |

Byte equality compares actual source/output bytes. JSON structural comparison
ignores object-key order and formatting, but compares array order, duplicates,
values and Python JSON scalar types. It does not compare raw lexical numbers or
XML trees. XML structural equality is explicitly **not tested**. RDF graph
isomorphism ignores serialization layout, prefix choices, ordering and blank-node
names, while retaining connectivity, language tags and datatypes. It is a graph
criterion, not OWL entailment or real-world equivalence. DataCite JSON has no
source RDF graph here, so no RDF-equivalence claim is made for it.

The DataCite projection preserves 7 fields exactly: DOI, publisher,
publicationYear, types, language, alternateIdentifiers and version. Seven fields
are partial/transformed: creators, titles, contributors, dates, relatedIdentifiers,
rightsList and descriptions; 4 are omitted (subjects,
sizes, formats and fundingReferences). The 11 residual keys cover the latter
11 fields. All field statuses and positional differences are available in
`datacite.roundtrip-report.json`.

Specific losses include translated-title role, creator scheme/affiliation
qualifiers, DataCurator role, collection interval/dateInformation, Methods
description, SPDX qualifiers and related resource class. JSON array ordering
can also change. Differences are positional, so reordering related resources
appears as transformed array entries, not necessarily lost relationship meaning.
Tests separately verify relation identity and direction.

Residuals store only top-level JSON fields whose actual reverse projection
fails equality. A partially mapped field therefore duplicates some normalized
values. They are `rdf:JSON` literals linked by `imo:residual` and `imo:jsonKey`.
These are **structured source backups**, not a semantic representation of funding
or roles. No complete raw source byte string is retained. The preserved export
proves structural reconstruction of this fixture, not general reversible
semantic mapping of arbitrary DataCite. The independent supported subset and
additional tests demonstrate actual reversibility without residuals.

The EDM source graph keeps native namespace-qualified predicates, including
`edm:currentLocation` and a custom conservation-note blank-node subgraph. This
preserves structured RDF meaning without inventing Schema.org equivalents.
Export simply replays that graph. It does not prove canonical terms alone can
reconstruct those assertions. No source XML bytes are stored, so comments,
namespace placement and lexical layout cannot be reconstructed.

Source-preserving exports require a matching source format and an unchanged
canonical digest, computed after blank-node canonicalization. Edits raise an
error; they do not silently replay the original. This is a conservative editing
policy, not a signature or tamper-proof archive. The digest does not authenticate
native/residual data. Reconciling edits with preserved source graphs is unresolved.

The cross-schema report lists all 31 native assertions with their projection or
exclusion reason. Titles, creator labels, contributor name, publisher,
description (Other), local accession, unqualified date (Other), language,
CHO rights and collection relationship map. Spatial detail, conservation note,
digital-resource properties, service roles and EDM classification do not.
Required DOI, publicationYear, resourceTypeGeneral and contributorType are absent;
`require_complete=True` raises. The minimum-field check is not a complete schema
validator, and no target registration or publication is attempted.

## Dataset versus directory versus file

A common graph envelope is sufficient for this demonstration; separate complete
metadata models would duplicate identifiers, labels, agents, licences and dates.
Use type-specific constraints and adapters instead of a single mandatory-field
record for every entity.

| Resource | Demonstrated type and properties |
| --- | --- |
| Dataset | `schema:Dataset`; typed identifiers, title, description, creator, publisher, version, dates, rights, `dct:hasPart` |
| Directory | `schema:Dataset` + proposed `imo:Directory` + `prov:Collection`; label, `dct:isPartOf`, `dct:hasPart`, `prov:hadMember` |
| File | `schema:MediaObject`; identifier, filename label, creation date, MIME type, contentSize, sha256, parent |

Directory-as-Dataset follows a packaging view comparable to RO-Crate; it does
not assert that every filesystem directory is a curated research dataset. The
extra Directory type preserves operational distinction. A file can also be a
scientific dataset, so multiple types may be appropriate. No `schema:File` class
is invented. If implementing RO-Crate, use its File alias/context conventions.

[contentSize](https://schema.org/contentSize) is text describing file size,
so the example uses `"119 bytes"`-style values, not an untyped numeric count;
[encodingFormat](https://schema.org/encodingFormat) holds the MIME type.
[sha256](https://schema.org/sha256) on a MediaObject is the checksum of actual
fixture bytes; the term is in Schema.org's newer vocabulary area. Teams needing
a more stable checksum profile could evaluate SPDX checksum nodes.
All actual sizes/digests are computed at runtime, never hardcoded in the report.

`dct:hasPart` and `dct:isPartOf` preserve direction; the builder adds both
explicitly. The graph engine performs no inverse inference. Creator and licence
assertions on the files are explicitly copied for the synthetic fixture; no
licence inheritance rule is implied. A future DCAT export must distinguish a
logical dataset's representation/distribution from arbitrary constituent files.

## Problems, trade-offs and Erlang feasibility

**Semantic scope.** A digital reproduction, physical original, dataset and
metadata record have distinct identities. Similar field names do not justify
merging them. Date roles, contributor roles and rights scope often matter more
than vocabulary choice. Projection rules need source and target profiles.

**Cardinality and order.** RDF graphs are sets. Duplicate titles and author order
are not preserved by ordinary repeated predicates. This implementation keeps
those differences in residuals and demonstrates the loss with tests. A future
semantic profile could use qualified contributions with explicit positions and
roles, or RDF lists on an explicitly defined ordered-contribution property.
Putting a list directly where an agent is required would change the property's
meaning. Multiple publishers and conflicting publication years need selection;
this exporter omits ambiguous values rather than choosing one arbitrarily.
Multilingual contextual names and other unsupported cardinalities need further
adapter work; the POC does not promise general graph-to-record conversion.

**Unknown properties.** Native RDF is an open extension mechanism. Non-RDF JSON
keys are retained as labelled JSON, not automatically promoted to globally
meaningful predicates. A production profile needs namespace governance, limits,
validation and clear behavior when only the canonical graph is exported.

**Provenance and conflicts.** Named graphs isolate source and normalized claims.
Conversion provenance is modelled; field-level derivation, import timestamps,
concurrent sources, authority, conflict resolution, editable residuals and
selective invalidation are future work. There is no inference engine or global
identity reconciliation. Checksums authenticate no metadata by themselves.

**Contexts and validity.** Compact JSON appearance does not determine RDF
meaning; explicit `@id`, literals, datatypes and graph scope do. The profile must
pin context versions and reject or control remote loading. DTDs are rejected by
the XML input adapter. Tests demonstrate these boundaries, but this is not a
hardened ingestion service. SHACL/profile validation and full target validators
are proposed next steps, not demonstrated behavior.

**Scale.** The fixture fits in memory. Full native graphs plus residuals increase
storage; whole-record canonicalization and JSON-LD serialization are not tested
for millions of files. Prefer separately addressable per-resource records,
paginated containment edges, immutable source blobs/graphs and selective graph
retrieval. Preserve identity across moves instead of using paths as permanent
IDs. Dataset aggregation may require snapshots or manifests. No performance
conclusion follows from these tiny examples.

**Erlang.** Normalized node maps or tagged RDF terms can represent IRIs, blank
nodes, language literals, typed literals and graph identifiers. Simple property
lookup and explicit adapter functions translate naturally to maps and binaries.
Separate the conceptual RDF dataset from the choice of database or runtime RDF
library. Arbitrary JSON-LD expansion, RDF graph canonicalization, large-graph
validation and semantic diffing are the harder parts; interoperability and
library evaluation are needed. A restricted, versioned inline JSON-LD profile
could keep the first Erlang implementation tractable. No Erlang code was changed
or interoperability verified.

## Recommendation and next decisions

Continue evaluating a **small RDF application profile with JSON-LD interchange**,
using established Schema.org, DCT and PROV terms, native named graphs for RDF
sources, and explicit residuals for non-RDF source fidelity. The evidence favors
this representation for mixed schemas and scoped relationships, while also
showing that JSON-LD alone does not make conversions lossless.

RO-Crate remains a credible alternative if the primary requirement is portable
research packaging. It shares the underlying graph approach and could be an
export profile; it was compared, not implemented here. DataCite is a useful
target and possible citation view, but a poor universal container for the EDM
source graph tested. Custom JSON could be the simplest implementation format,
provided it preserves the same explicit identities, typed values and source
boundaries; it should not silently redefine standard semantics.

Before fixing the Onedata representation, agree on identity and filesystem
semantics, author ordering and qualified roles, source-edit reconciliation,
required target profiles and validator versions. Then prototype an RO-Crate
adapter, test external real records including mixed-schema conflicts, and
measure storage/serialization costs in the proposed Erlang representation.
The POC supports the graph direction; it does not establish a final production
schema or universal lossless crosswalk.
