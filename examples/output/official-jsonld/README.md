# Wyniki oficjalnych przykładów

Generowane przez `demo_json.py`. Każdy przykład ma osobny katalog z modelem, obiema projekcjami i raportem.

Źródła i sumy kontrolne: [sources.json](../../input/official/sources.json).

| Przykład | Format | Zasoby | EDM: równoważność RDF | Raport |
| --- | --- | ---: | --- | --- |
| [datacite-full](datacite/datacite-full/README.md) | datacite | 4 | — | [raport](datacite/datacite-full/report.json) |
| [datacite-dataset](datacite/datacite-dataset/README.md) | datacite | 3 | — | [raport](datacite/datacite-dataset/report.json) |
| [edm](edm/edm/README.md) | edm | 6 | — | [raport](edm/edm/report.json) |
| [datacite-award](datacite/datacite-award/README.md) | datacite | 3 | — | [raport](datacite/datacite-award/report.json) |
| [datacite-project](datacite/datacite-project/README.md) | datacite | 3 | — | [raport](datacite/datacite-project/report.json) |
| [datacite-multilingual](datacite/datacite-multilingual/README.md) | datacite | 4 | — | [raport](datacite/datacite-multilingual/report.json) |
| [datacite-related-item](datacite/datacite-related-item/README.md) | datacite | 3 | — | [raport](datacite/datacite-related-item/report.json) |
| [edm-image-tier1](edm/edm-image-tier1/README.md) | edm | 3 | — | [raport](edm/edm-image-tier1/report.json) |
| [edm-sound-tier1](edm/edm-sound-tier1/README.md) | edm | 3 | — | [raport](edm/edm-sound-tier1/report.json) |
| [edm-3d-complete](edm/edm-3d-complete/README.md) | edm | 10 | — | [raport](edm/edm-3d-complete/report.json) |

Kolumna równoważności dotyczy EDM → JSON-LD → EDM i jest sprawdzana przez RDFLib z `--compare-rdf`.
Kreska oznacza brak takiego porównania. Pomyślne parsowanie nie oznacza bezstratnej konwersji.
Wielojęzyczne nazwy autorów, nieobsługiwane terminy, role dat i inne szczegóły mogą ginąć; sprawdź raport konkretnego przykładu.
Błędy starej implementacji są raportowane niezależnie od wyniku nowego adaptera.
