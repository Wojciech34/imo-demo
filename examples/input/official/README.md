# Official example snapshots

The corpus contains **10 source files: 6 DataCite JSON records and 4 EDM
RDF/XML records**. They are downloaded official examples, separate from this
project's original synthetic fixtures. `sources.json` records each file's ID,
format, source URL, retrieval timestamp, description and SHA-256. The demo
verifies these hashes and runs offline.

## DataCite

All six records are linked from the official
[DataCite Metadata Schema 4.6 examples](https://schema.datacite.org/meta/kernel-4.6/).
The original JSON:API envelopes, metadata and service attributes are intact.
These are **test-environment records**, not production DOI registrations.

| File | Official example | Test DOI |
| --- | --- | --- |
| `datacite-full.json` | Full metadata example | `10.82433/B09Z-4K37` |
| `datacite-dataset.json` | Dataset / environmental observations | `10.82433/9184-DY35` |
| `datacite-award.json` | Award / grant | `10.82433/p1zt-4c67` |
| `datacite-project.json` | Project | `10.82433/84dj-am41` |
| `datacite-multilingual.json` | Multilingual metadata | `10.82433/byt7-2g42` |
| `datacite-related-item.json` | Article with its journal as RelatedItem | `10.82433/q54d-pf76` |

The Award snapshot has a creator name identifier with a scheme but no value.
The direct adapter reports its JSON pointer in `provenance.warnings`, skips
that empty identifier in normalized metadata and retains it in the source
backup. The historical RDFLib adapter fails on the Award and Project examples;
those comparison errors are reported separately from the new conversion.

## EDM

| File | Official source | Purpose |
| --- | --- | --- |
| `edm.xml` | [europeana/contrib](https://github.com/europeana/contrib/blob/master/ntua/mint2/src/main/webapp/schemas/edm/EDM.xml) | Historical First Implementation sample: musical instrument and contextual resources |
| `edm-image-tier1.xml` | [europeana/test_dataset](https://github.com/europeana/test_dataset) | EPF Content Tier 1 image |
| `edm-sound-tier1.xml` | Same test dataset | EPF Content Tier 1 sound, with an indirect media link |
| `edm-3d-complete.xml` | Same test dataset | Rich 3D example with multiple WebResources, contextual resources and services |

The three new Europeana records are pinned to commit
`b939d3cf0c99fb445b6cf80a78e80cb3a8d69279`. Full raw-file URLs are in the
manifest. Their repository's EUPL licence is included in
[europeana-test-dataset.LICENSE.md](europeana-test-dataset.LICENSE.md). The
original EUPL 1.1 notice of `edm.xml` remains in that XML file.

Relative IDs are resolved against each source URL in the manifest, not the
local file path. These are official samples/test records; the historical
sample and the 3D record marked as under development are not presented as
validated modern delivery packages. Source documents are not rewritten to fit
our parser. Unsupported properties are exposed by mapping and RDF comparison
reports.

## Inputs and outputs

Run from the project root:

```bash
make examples
```

This uses `python` from the active environment. Without activation, run
`make examples PYTHON=.venv/bin/python`. The equivalent direct command is
`python demo_json.py --compare-rdf`.

Browse the generated [output index](../../output/official-jsonld/README.md).
Each record has its own directory, grouped by source format. The index links
the source, JSON-LD, projections, report and optional original-model comparison.
Source URLs can change; the snapshots, pinned revisions and hashes make this
experiment repeatable.
