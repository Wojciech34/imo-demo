# Onedata IMO architecture POC

A standalone Python experiment with DataCite JSON → IMO → DataCite,
EDM RDF/XML → IMO → EDM, both cross-schema projections, and a dataset containing
a directory and two actual example files. No Onedata services are required.
`main.py` and `demo.py` run the same demonstration.

Polska dokumentacja z diagramami Mermaid:
[jak działa IMO](docs/README.md), [architektura](docs/architektura.md),
[EDM → JSON-LD krok po kroku](docs/edm-jsonld.md).

## Run locally

Python 3.10+ is required (tested with 3.12.3). From this directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
python demo.py
python -m pytest -q
```

For the exact dependency versions used for the checked-in results, install
`python -m pip install -r requirements-lock.txt` instead. On Windows, activate
with `.venv\Scripts\activate`. After installation, the demo runs offline.
If using an IDE, select `.venv/bin/python` and run `main.py`.

## Ready-made Make targets

The [Makefile](Makefile) uses `python` from your current `PATH`. After activating
the environment (`source .venv/bin/activate`), run commands from the project root:

```bash
make help
make examples
make hierarchy
make test
```

| Target | Action |
| --- | --- |
| `make install` | Install the project and test dependencies into the selected interpreter's environment |
| `make demo` | Process all official inputs without the RDFLib reference comparison |
| `make examples` | Process all official inputs, compare with RDFLib, generate reports and output index |
| `make hierarchy` | Print the small Dataset → Directory → File example |
| `make rdf-demo` | Run the original RDFLib demonstration |
| `make test` | Run pytest |
| `make example-datacite` | Convert the official dataset to `OUTPUT_DIR/quickstart/datacite.imo.jsonld` |
| `make example-edm` | Convert the original official EDM record to `OUTPUT_DIR/quickstart/edm.imo.jsonld` |
| `make list-examples` | List all official example IDs |
| `make load-example EXAMPLE=datacite-award` | Load a selected input, validate it and save its JSON-LD model |
| `make roundtrip-example EXAMPLE=datacite-award` | Load, serialize/reload, export back to the source format and print the diff |
| `make convert` | Convert your own file using the variables below |

`OUTPUT_DIR` defaults to `examples/output/official-jsonld`. Override the
interpreter or output location without activating the environment:

```bash
make examples PYTHON=.venv/bin/python OUTPUT_DIR=/tmp/imo-results
```

For your own file, set `INPUT`, `FROM` (`datacite`, `edm`, `jsonld`), `TO`
(the same choices), and optional `OUTPUT`. Defaults are `FROM=datacite` and
`TO=jsonld`; without `OUTPUT` the result is printed to stdout. Parent directories
of a custom `OUTPUT` must exist, as with the underlying CLI.

```bash
make convert INPUT=examples/input/official/datacite-dataset.json FROM=datacite TO=jsonld OUTPUT=wynik.jsonld
make convert INPUT=wynik.jsonld FROM=jsonld TO=edm OUTPUT=wynik.xml
make convert INPUT=twoj-plik.xml FROM=edm SOURCE_URI=https://museum.example/original.xml OUTPUT=wynik.jsonld
```

`SOURCE_URI` is required for EDM input; optional `RESOURCE_ROOT` selects a
ProvidedCHO when the file contains several. Shell-quote paths containing spaces,
e.g. `INPUT='my record.json'`. The targets call the existing Python entry points
and retain their mapping and validation limitations.

For a single official example, `EXAMPLE` defaults to `datacite-award`:

```bash
make list-examples
make load-example EXAMPLE=datacite-award
make roundtrip-example EXAMPLE=datacite-award
make roundtrip-example EXAMPLE=edm-3d-complete
```

These commands read local snapshots, not upload them to a service. The manifest
supplies the format, source URI and checksum automatically. Results are written
to `OUTPUT_DIR/selected/EXAMPLE/`, separately from batch reports. Loading writes
`imo.jsonld`, `report.json` and a local README. A round trip also writes the
source-format projection and `diff.txt`, which is printed to the terminal.
For DataCite, comparison covers metadata attributes only, excluding the API
envelope and service fields such as the base64 XML payload and usage counts.
For EDM, comparison covers RDF assertions rather than XML layout and prefixes.
The diff uses `-` for removed and `+` for added content; differences do not
cause a failing exit status. `make load-example` removes previous generated
round-trip files for that selected case, so its report reflects loading only.

Equivalent Python commands are `python demo_json.py --case datacite-award
--load-only` and `python demo_json.py --case datacite-award --show-diff`.
The source backup is not used for reconstruction, and no full schema validation
is performed. These targets compare the new model's round trip; `make examples`
additionally compares the historical RDFLib implementation.

The original `python demo.py` prints DataCite-derived IMO JSON-LD, field preservation statuses,
and measured results. It regenerates all files in `examples/output/`. Absolute
paths are based on the script location, so running from another directory works.
The original `demo.py` input records are representative **synthetic fixtures**,
not harvested records. `demo_json.py` additionally uses downloaded official
examples, documented below. The original fixture DOIs, personal details and relationships are illustrative;
no identifiers are registered or resolved. The tiny file payloads stand in for
a larger observation dataset; their recorded sizes and SHA-256 values are real.

## A five-minute presentation

1. Open `examples/input/datacite.json`: multilingual titles, identified creators,
   contributor role, collection interval, licence, typed relations and funding.
2. Run `python demo.py`. Open `examples/output/datacite.imo.jsonld` and point out
   `urn:imo:canonical` and `urn:imo:provenance`. A residual is labelled source
   JSON, distinct from normalized assertions.
3. Compare `datacite.projected.json` with `datacite.preserved.json` and inspect
   `datacite.roundtrip-report.json`. The rich record only reconstructs fully
   with residuals. A separately constructed supported subset needs no backup.
4. Open `examples/input/edm.xml`: the heritage object, digital WebResource and
   aggregation are distinct. `edm.imo.jsonld` retains the native source graph.
   `edm.roundtrip-report.json` demonstrates 31/31 triples preserved by native
   replay, versus 11/31 original triples retained by the narrow projection.
5. Inspect `edm-to-datacite.draft.json` and its report: a publication year and DOI
   are absent, and the digital image's licence is not assigned to the physical
   heritage object. This is an **incomplete draft**, not a registration record.
6. Show `dataset-hierarchy.imo.jsonld`: one graph model, different resource types,
   explicit containment, real checksums and file sizes. Finish with the
   recommendation and open questions in [POC_REPORT.md](POC_REPORT.md).

## Output guide

| File in `examples/output/` | Purpose |
| --- | --- |
| `datacite.imo.jsonld`, `edm.imo.jsonld` | Serialized IMO RDF datasets with inline contexts |
| `datacite.projected.json` | Canonical semantic projection; intentional losses |
| `datacite.preserved.json` | Source structure reconstructed with labelled JSON residuals |
| `datacite.roundtrip-report.json` | Byte/structure measures, per-field statuses, JSON pointer differences |
| `edm.projection.xml` | Narrow projection, incomplete EDM delivery package |
| `edm.native.xml` | Replay of native RDF graph; no original XML text retained |
| `edm.roundtrip-report.json` | RDF isomorphism, exact triple differences by predicate |
| `edm-to-datacite.draft.json` | Cross-schema projection requiring curation |
| `edm-to-datacite.report.json` | Every source assertion, mapping/exclusion reason, missing fields |
| `datacite-to-edm.draft.xml` | CHO-view draft; digital aggregation cannot be inferred |
| `dataset-hierarchy.imo.jsonld` | Dataset → directory → two files, agents, provenance |
| `summary.json` | Compact machine-readable experiment results |

## Code layout and API

`imo/rdf_model.py` owns the three named graphs, pinned JSON-LD context and stale
source check. `imo/parsers/` projects inputs; `imo/converters/` exports targets;
`imo/compare.py` measures losses. `imo/examples.py` builds the physical hierarchy.

```python
import json
from pathlib import Path
from imo import IMO
from imo.parsers.datacite import parse_datacite
from imo.converters.datacite import export_datacite

imo = parse_datacite(json.loads(Path("examples/input/datacite.json").read_text()))
restored = IMO.from_jsonld(imo.to_jsonld())
projection = export_datacite(restored)
reconstructed = export_datacite(restored, preserve=True)
```

`preserve=True` is only for an unchanged canonical graph from the matching
source format. After an edit, use a projection and curate missing fields;
source-preserving export raises an error. `require_complete=True` adds a
minimum-field check for DataCite. It does **not** perform full schema validation.
Explicit target values may be supplied through `overrides`; the demo deliberately
does not invent them.

## Alternative direct JSON-LD model

`imo/json_model.py` provides `JsonLDIMO`: JSON-LD operated on directly as
Python dictionaries, without RDFLib. The original `imo/rdf_model.py` remains
available for comparison. Run `python demo_json.py --example` to print a small
dataset → directory → file example. The default `python demo_json.py` now runs
official DataCite/EDM fixtures through the new adapters exposed by `imo/json_adapters.py`.
The adapters in `imo/parsers/` and `imo/converters/` still use the original model.

The direct JSON-LD code separates term definitions, conversion mappings,
document syntax and adapters:

```text
imo/
  vocabularies/
    dc.py           # DC/DCT namespace and term definitions
    edm.py          # EDM/ORE namespace and term definitions
    skos.py         # SKOS namespace and term definitions
    rdf.py          # RDF namespace and syntax names: about, resource, datatype, ...
    xml.py          # XML namespace and attributes: base, lang, space, id
  mappings/
    dc.py           # DC/DCT terms -> canonical IMO fields
    skos.py         # SKOS terms -> canonical IMO fields and types
    edm.py          # native EDM/ORE rules; composes the full EDM profile
    datacite.py     # DataCite JSON field, type, relation and projection rules
  adapters/
    common.py       # shared JSON-LD value operations
    datacite.py     # DataCite resource construction; imports mappings/datacite.py
    edm.py          # applies mappings/edm.py; constructs/selects resources
  serialization/
    rdfxml.py       # shared flat RDF/XML reader/writer, base and language scope
  json_adapters.py  # existing import interface and CLI
  json_model.py     # shared JSON-LD model and validation
```

`vocabularies/` defines namespace strings and term names only, e.g.
`dc.TITLE` is the URI of `dc:title`. `mappings/` defines all source-to-model
conversion rules, including RDF term mappings and DataCite JSON rules.
`mappings/edm.py` composes DC/DCT, native EDM/ORE and SKOS rules; the EDM adapter
imports this completed profile instead of assembling mappings itself. Another
adapter can reuse `mappings/dc.py` without importing the EDM adapter.
Vocabulary modules never import mappings, adapters or the model. Mapping
modules may import vocabulary definitions or other mapping modules, but not
the model or parsers. Neither layer depends on lxml or RDFLib. The shared
model still uses vocabulary namespace strings in its own JSON-LD context;
that context describes the canonical document rather than a source adapter.
There is not yet a standalone DC/OAI-DC document adapter.
DataCite's JSON field mappings live in `imo/mappings/datacite.py`, alongside
DC, EDM and SKOS conversion mappings. The DataCite parser and exporter share tables for
text lists, scalar fields, resource/agent types, description types and relations.
The same module records title exclusions, lossy date export defaults and the
minimum required fields. Resource construction and value conversion remain
in the adapter. Extracting these rules does not expand mapping coverage.
The shared `serialization/rdfxml.py` imports RDF/XML names such as `ABOUT`
and `LANG` from the vocabulary modules. It handles document parsing, named
resource IDs, relative URI resolution, inherited `xml:lang` (including reset
with an empty value), typed literals and XML writing. This syntax layer has
no dependency on EDM, DC or the IMO model. The EDM adapter uses decoded JSON-LD
value objects, applies its metadata mappings and selects the ProvidedCHO root.
It still reports typed literals as unmapped because they are outside its
current metadata profile, even though the common syntax layer can read/write
them. Nested/anonymous RDF/XML and DTDs remain unsupported. Vocabulary
definitions alone do not enable additional syntax or metadata mappings.
Existing `from imo.json_adapters import parse_edm` imports and CLI commands
continue to work. Direct imports such as `from imo.adapters.datacite import
parse_datacite` load only that format's adapter and do not load lxml or RDFLib.

```python
from imo import JsonLDIMO

imo = JsonLDIMO(root="urn:example:dataset-1", resources=[
    {
        "@id": "urn:example:dataset-1",
        "@type": "Dataset",
        "titles": [{"@value": "Observations", "@language": "en"}],
        "creators": [{"@id": "urn:example:person-1"}],
    },
    {
        "@id": "urn:example:person-1",
        "@type": "Person",
        "name": "Alex Smith",
    },
])
restored = JsonLDIMO.from_jsonld(imo.to_jsonld())
# Or use to_json()/from_json() for JSON text.
```

The embedded `@context` maps `titles` to `dct:title`, `creators` to
`dct:creator`, `name` to `schema:name` and `Dataset` to `schema:Dataset`.
Language-tagged text uses `@value`/`@language`; resource links use explicit
`{"@id": "..."}` objects. These are semantic JSON-LD assertions, not an opaque
JSON payload wrapped in a context.

| Aspect | Original model (`IMO`) | Direct JSON-LD model (`JsonLDIMO`) |
| --- | --- | --- |
| In memory | RDFLib graphs | Python lists and dictionaries |
| Properties | RDF URI objects such as `DCT.title` | Context-defined keys such as `titles` |
| Resources | RDF nodes | JSON-LD objects with `@id` and `@type` |
| Relations | RDF triples | Properties containing `@id` references |
| Serialization | JSON-LD with three named graphs | JSON-LD record with a named `@graph` of resources |
| Semantics | RDF | RDF expressed directly as JSON-LD |
| Source preservation | Existing adapters, residuals and stale checks | Optional explicit JSON backup; no source exporter |

This is a limited compact JSON-LD profile, not a general JSON-LD processor.
Validation requires the exact inline context, supported property shapes,
unique HTTP(S)/URN IDs, and a root present in `@graph`. Remote or nested contexts
and unknown resource properties are rejected; external relation targets are
allowed. Inverse relations are explicit, not inferred. Python serialization
preserves array structure, but `@set` properties do not assert semantic order
or duplicate occurrences in RDF.

The record's `provenance` and optional `source` fields are opaque JSON values
mapped through `@type: @json`. They are separate from resource assertions and
are not automatically used to reconstruct a source format. Imports and exports
copy mutable data. The public models are `JsonLDIMO` (direct JSON-LD) and
`IMO` (the original RDFLib model). The obsolete plain-JSON prototype alias
`JsonIMO` has been removed; use `from imo import JsonLDIMO`.

Local CLI output files named `wynik.jsonld`, `wynik.xml` and `edm-wynik.jsonld`
are ignored at the project root. The examples and reports under
`examples/output/` remain available for review and comparison.

The new model uses only the Python standard library. Installing the complete
project still installs the original model's RDF dependencies. Tests use RDFLib
as an independent verifier of the generated JSON-LD semantics and separately
check that the new model runs with third-party packages disabled.

## Official DataCite and EDM conversion experiment

To convert your own file from the project directory:

```bash
python -m imo.json_adapters input.json --from datacite -o output.jsonld
python -m imo.json_adapters output.jsonld --from jsonld --to edm -o output.xml
python -m imo.json_adapters input.xml --from edm --source-uri https://example.org/original.xml -o output.jsonld
```

Use `--to jsonld` (the default), `--to datacite`, or `--to edm`. Without `-o`,
the result is printed to stdout. For EDM, `--source-uri` is the original document
URL used to resolve relative identifiers; it is never downloaded. Use `--root`
with an absolute ProvidedCHO ID if the input contains several objects.
JSON-LD input must conform to this project's pinned direct-model profile.
These exports have the same subset/draft limitations described below.

```bash
python demo_json.py --compare-rdf
```

This command runs offline against **10 snapshots: 6 DataCite and 4 EDM** in
`examples/input/official/`. Their URLs, per-file retrieval timestamps and
SHA-256 values are recorded in
[`sources.json`](examples/input/official/sources.json). The DataCite records
(full metadata, dataset, award, project, multilingual metadata and a journal
RelatedItem) are linked from the official
[DataCite 4.6 examples page](https://schema.datacite.org/meta/kernel-4.6/).
Their JSON data is intact from the test API, including `data.attributes`
and structured publisher objects. Local JSON files use two-space indentation;
the manifest's `sha256` covers the formatted file and `downloadSha256` records
the original download. Values and ordering are unchanged. EDM includes the historical musical
instrument sample plus image, sound and complete 3D records from
[Europeana's test dataset](https://github.com/europeana/test_dataset), pinned
to a commit. Source details and the retained licence are described in the
[input catalogue](examples/input/official/README.md).

Every input is parsed into the direct JSON-LD model, serialized to JSON text,
loaded again and projected to both DataCite JSON attributes and EDM RDF/XML.
The optional `--compare-rdf` also runs the original model and independently
compares RDF/XML graphs through RDFLib. The direct adapters use dictionaries
and lxml; they do not import RDFLib. The original `imo/rdf_model.py` remains
for comparison.

Browse the generated [output index](examples/output/official-jsonld/README.md).
Results are grouped by format and record:

```text
examples/output/official-jsonld/
  README.md                         # clickable index of every example
  summary.json                      # machine-readable results and file paths
  datacite/
    datacite-full/
      README.md
      imo.jsonld
      datacite.projected.json
      edm.draft.xml
      report.json
      original-model.imo.jsonld      # only when reference conversion succeeds
    datacite-award/
    ...
  edm/
    edm/                            # the original musical-instrument sample
      README.md
      imo.jsonld
      datacite.draft.json
      edm.projected.xml
      report.json
      original-model.imo.jsonld
    edm-image-tier1/
    edm-sound-tier1/
    edm-3d-complete/
```

Use a different output location with:

```bash
python demo_json.py --compare-rdf --output-dir /tmp/imo-results
```

Reports distinguish actual source/target RDF equality from successful parsing:

| EDM input | Resources | Source triples | Preserved triples | Lost | Added |
| --- | ---: | ---: | ---: | ---: | ---: |
| `edm.xml` | 6 | 29 | 29 | 0 | 0 |
| `edm-image-tier1.xml` | 3 | 19 | 13 | 6 | 2 |
| `edm-sound-tier1.xml` | 3 | 18 | 13 | 5 | 2 |
| `edm-3d-complete.xml` | 10 | 106 | 56 | 50 | 2 |

Only the historical sample round-trips without RDF losses in this corpus.
The richer records expose unsupported properties/classes, literal relations
and language loss on creator names. Record-scoped agent resources can also
add assertions. The original RDFLib adapter's native replay preserves all
source triples; its narrower projection does not. These differences reflect
mapping coverage and projection policy, not an inherent advantage of either
in-memory representation.

All six DataCite records parse with the new adapter and their projections
contain the six minimum required top-level fields. Per-field reports show
real losses, including typed titles, identifier schemes, affiliations, date
roles, funding and RelatedItem details. This is not full schema validation.
The Award example includes a creator identifier without a value: it is skipped
with an explicit warning and kept in the source backup. The historical adapter
raises `KeyError` for Award and Project. These failures appear under
`rdfComparison.status: error` and do not interrupt the other cases. A previous
optional reference document is removed before rerunning a case, so an old
successful result cannot be mistaken for the current comparison.

The source backup is never replayed by the new exporters. EDM → DataCite can
lack DOI, publisher, publication year, resource type and sometimes creators;
the image's `edm:rights` is not assigned to the physical object. DataCite → EDM
is a narrow CHO-view draft without invented images or aggregations. Neither
cross-format draft has been validated as a registration or delivery package.

The old flat output files have been replaced by per-example directories.
`report.json` and `summary.json` contain paths relative to the output root.
Source hashes are checked before a record is processed; the demo performs no
network requests.

The new EDM adapter deliberately accepts only flat, named RDF/XML resources
and explicit supported properties. It resolves relative IDs and XML base,
rejects DTDs and unsupported nested/anonymous syntax, and reports unmapped
properties. It is not a general RDF/XML parser.

## Boundaries

The original adapters implement a subset of DataCite **4.6-style JSON attributes**,
not DataCite XML or REST envelopes; the direct JSON-LD adapter additionally
unwraps single-record REST responses. EDM inputs are RDF/XML with one selected
ProvidedCHO; arbitrary predicates and contextual nodes survive native replay.
JSON-LD input is limited to this POC's inline context. This is not a generic
JSON-LD or metadata conversion framework. Resource identifiers should be absolute.

Neither cross-schema draft is certified by a DataCite schema or Europeana
validator. No automatic equivalence reasoning, RO-Crate adapter, OpenAIRE
adapter, or Onedata/Erlang integration is included. RO-Crate is evaluated in the
report; a packaging adapter is a subsequent experiment.

Tests cover serialized round trips, direction of relations, language tags,
unknown fields and blank nodes, duplicate/order loss, stale preservation,
rights scope, incomplete targets, XML DTD rejection, remote context rejection,
and checksums of actual fixture files. RDFLib 7.6 emits upstream deprecation
warnings from its JSON-LD parser/serializer, and pytest introspection warns about
the XSD namespace; these do not affect the demonstrated results.
