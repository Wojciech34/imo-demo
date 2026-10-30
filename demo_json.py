"""Run official fixtures through the direct JSON-LD adapters, offline.

python demo_json.py --compare-rdf
python demo_json.py --example  # small manually constructed hierarchy
"""
from imo.json_model import JsonLDIMO


def example():
    return JsonLDIMO(
        root="urn:example:dataset-1",
        resources=[
            {
                "@id": "urn:example:dataset-1",
                "@type": "Dataset",
                "titles": [{"@value": "Pomiary temperatury", "@language": "pl"}],
                "creators": [{"@id": "urn:example:person-1"}],
                "hasPart": [{"@id": "urn:example:directory-1"}],
            },
            {
                "@id": "urn:example:person-1",
                "@type": "Person",
                "name": "Jan Kowalski",
            },
            {
                "@id": "urn:example:directory-1",
                "@type": "Directory",
                "name": "raw",
                "isPartOf": [{"@id": "urn:example:dataset-1"}],
                "hasPart": [{"@id": "urn:example:file-1"}],
            },
            {
                "@id": "urn:example:file-1",
                "@type": "File",
                "name": "temperatures.csv",
                "mediaType": "text/csv",
                "isPartOf": [{"@id": "urn:example:directory-1"}],
            },
        ],
        provenance={"activity": "manual-example", "source": "demo_json.py"},
    )


def official_sources():
    import json
    from pathlib import Path

    fixtures = Path(__file__).resolve().parent / "examples/input/official"
    return fixtures, json.loads((fixtures / "sources.json").read_text())["sources"]


def _load_official_model(fixtures, source):
    import hashlib
    import json
    from imo.json_adapters import parse_datacite, parse_edm

    payload = (fixtures / source["file"]).read_bytes()
    if hashlib.sha256(payload).hexdigest() != source["sha256"]:
        raise ValueError(f"Official snapshot checksum mismatch: {source['file']}")
    model = (parse_edm(payload, source["url"]) if source["format"] == "edm"
             else parse_datacite(json.loads(payload), source["url"]))
    return model, payload


# DataCite metadata properties; other attributes are API/service information.
DATACITE_METADATA = {
    "doi", "identifiers", "alternateIdentifiers", "creators", "titles", "publisher",
    "publicationYear", "subjects", "contributors", "dates", "language", "types",
    "relatedIdentifiers", "relatedItems", "sizes", "formats", "version", "rightsList",
    "descriptions", "geoLocations", "fundingReferences",
}


def _differences(before, after, path=""):
    """JSON pointers for structural differences, without dumping source values."""
    if type(before) is not type(after):
        return [path or "/"]
    if isinstance(before, dict):
        result = []
        for key in sorted(before.keys() | after.keys()):
            child = path + "/" + key.replace("~", "~0").replace("/", "~1")
            if key not in before or key not in after:
                result.append(child)
            else:
                result.extend(_differences(before[key], after[key], child))
        return result
    if isinstance(before, list):
        result = []
        for index in range(max(len(before), len(after))):
            child = path + "/" + str(index)
            if index >= len(before) or index >= len(after):
                result.append(child)
            else:
                result.extend(_differences(before[index], after[index], child))
        return result
    return [] if before == after else [path or "/"]


def _datacite_report(attributes, projection):
    fields = []
    for key, value in sorted(attributes.items()):
        if key not in DATACITE_METADATA:
            status = "api_attribute_not_projected"
        elif key in projection and value == projection[key]:
            status = "exact"
        elif key in projection:
            status = "partial"
        elif value in (None, [], {}, ""):
            status = "empty_not_projected"
        else:
            status = "not_projected"
        fields.append({"field": key, "status": status})
    return {"fields": fields, "differences": _differences(attributes, projection),
            "note": "Comparison covers the projected attributes, excluding any source backup replay."}


def _compare_original(payload, document, edm_xml, source, is_edm):
    """Optional reference implementation and independent RDF/XML verification."""
    from rdflib import Graph
    from rdflib.compare import graph_diff, isomorphic, to_isomorphic
    from imo.parsers.datacite import parse_datacite as rdf_parse_datacite
    from imo.parsers.edm import parse_edm as rdf_parse_edm
    from imo.converters.datacite import export_datacite as rdf_export_datacite
    from imo.converters.edm import export_edm as rdf_export_edm

    if is_edm:
        original = Graph().parse(data=payload, format="xml", publicID=source["url"])
        projected = Graph().parse(data=edm_xml, format="xml", publicID=source["url"])
        reference = rdf_parse_edm(payload, source["url"])
        legacy_projection = rdf_export_edm(reference)
        common, removed, added = graph_diff(to_isomorphic(original), to_isomorphic(projected))
        details = {
            "status": "ok", "sourceTriples": len(original),
            "directProjectionTriples": len(projected),
            "directProjectionIsomorphic": isomorphic(original, projected),
            "preservedTriples": len(common), "lostTriples": len(removed), "addedTriples": len(added),
            "originalModelProjectionTriples": len(legacy_projection),
            "originalModelProjectionIsomorphic": isomorphic(original, legacy_projection),
            "originalModelNativeReplayIsomorphic": isomorphic(original, rdf_export_edm(reference, preserve=True)),
        }
    else:
        attributes = document["data"]["attributes"]
        reference = rdf_parse_datacite(attributes, source["url"])
        details = {
            "status": "ok",
            "originalModelDataciteRoundtrip": _datacite_report(attributes, rdf_export_datacite(reference)),
            "originalModelSourcePreservingEqual": rdf_export_datacite(reference, preserve=True) == attributes,
            "publisherNote": "The original adapter expects a publisher string; these API responses supply an object. The direct adapter extracts its name.",
        }
    return details, reference.to_jsonld()


def run_official(output_dir=None, compare_rdf=False):
    import json
    import os
    from pathlib import Path
    from imo.json_adapters import parse_edm, export_datacite, export_edm, missing_datacite_fields

    base = Path(__file__).resolve().parent
    fixtures, sources = official_sources()
    output_root = Path(output_dir) if output_dir is not None else base / "examples/output/official-jsonld"
    output_root.mkdir(parents=True, exist_ok=True)
    summary = {"model": "direct-jsonld", "sourceManifest": "examples/input/official/sources.json", "records": []}
    index = ["# Wyniki oficjalnych przykładów", "",
             "Generowane przez `demo_json.py`. Każdy przykład ma osobny katalog z modelem, obiema projekcjami i raportem.", "",
             "Źródła i sumy kontrolne: [sources.json](" + Path(os.path.relpath(fixtures / "sources.json", output_root)).as_posix() + ").", "",
             "| Przykład | Format | Zasoby | EDM: równoważność RDF | Raport |",
             "| --- | --- | ---: | --- | --- |"]

    def save_json(directory, name, value):
        (directory / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    for source in sources:
        filename, label, source_format = source["file"], source["id"], source["format"]
        model, payload = _load_official_model(fixtures, source)
        is_edm = source_format == "edm"
        output = output_root / source_format / label
        output.mkdir(parents=True, exist_ok=True)
        # Prevent a previous optional comparison from looking like a current result.
        (output / "original-model.imo.jsonld").unlink(missing_ok=True)
        document = None if is_edm else json.loads(payload)
        serialized = model.to_json()
        model = JsonLDIMO.from_json(serialized)
        (output / "imo.jsonld").write_text(serialized + "\n", encoding="utf-8")
        datacite = export_datacite(model)
        edm_xml = export_edm(model)
        dc_filename = f"datacite.{'draft' if is_edm else 'projected'}.json"
        edm_filename = f"edm.{'projected' if is_edm else 'draft'}.xml"
        save_json(output, dc_filename, datacite)
        (output / edm_filename).write_text(edm_xml, encoding="utf-8")
        relative = output.relative_to(output_root)
        outputs = {name: (relative / file).as_posix() for name, file in {
            "jsonld": "imo.jsonld", "datacite": dc_filename, "edm": edm_filename, "report": "report.json"}.items()}
        report = {
            "id": label, "input": filename, "source": source["url"], "format": source_format,
            "resources": len(model.resources), "outputs": outputs,
            "jsonldRoundtripEqual": JsonLDIMO.from_json(model.to_json()).to_jsonld() == model.to_jsonld(),
            "missingDataCiteFields": missing_datacite_fields(datacite),
            "schemaValidated": False, "sourceBackupUsedForExport": False,
            "warnings": model.provenance.get("warnings", []),
            "rdfComparison": {"status": "not_requested"},
        }
        if is_edm:
            report["mapping"] = model.provenance["mapping"]
            reparsed = parse_edm(edm_xml, source["url"])
            report["edmResourceRoundtripEqual"] = reparsed.resources == model.resources
            report["crossConversionNotes"] = [
                "Only the ProvidedCHO is projected to DataCite; image and aggregation metadata are excluded.",
                "Digital edm:rights is not assigned as the physical object's licence.",
                "No DOI, creator, publisher, publication year or Dataset type is invented.",
            ]
        else:
            report["dataciteRoundtrip"] = _datacite_report(document["data"]["attributes"], datacite)
            report["crossConversionNotes"] = [
                "EDM output is a narrow ProvidedCHO-view draft; it has no invented WebResource or Aggregation.",
                "Typed titles, creator identifier schemes, affiliations, date roles and other details can be lost; see field differences.",
            ]
        if compare_rdf:
            try:
                report["rdfComparison"], reference_document = _compare_original(payload, document, edm_xml, source, is_edm)
                save_json(output, "original-model.imo.jsonld", reference_document)
                outputs["originalModel"] = (relative / "original-model.imo.jsonld").as_posix()
            except (KeyError, TypeError, ValueError) as error:
                # Failure of the historical adapter does not erase the new result.
                report["rdfComparison"] = {"status": "error", "errorType": type(error).__name__, "message": str(error)}
        save_json(output, "report.json", report)
        row = {key: value for key, value in report.items() if key in {
            "id", "input", "format", "resources", "outputs", "jsonldRoundtripEqual", "missingDataCiteFields", "edmResourceRoundtripEqual", "schemaValidated", "warnings"}}
        row["comparisonStatus"] = report["rdfComparison"]["status"]
        for key in ("sourceTriples", "directProjectionTriples", "directProjectionIsomorphic", "preservedTriples", "lostTriples", "addedTriples"):
            if key in report["rdfComparison"]:
                row[key] = report["rdfComparison"][key]
        summary["records"].append(row)
        equivalent = report["rdfComparison"].get("directProjectionIsomorphic")
        fidelity = ("tak" if equivalent else "nie") if equivalent is not None else "—"
        index.append(f"| [{label}]({relative.as_posix()}/README.md) | {source_format} | {len(model.resources)} | {fidelity} | [raport]({outputs['report']}) |")
        source_path = Path(os.path.relpath(fixtures / filename, output)).as_posix()
        case_lines = [f"# {label}", "", source["description"], "",
                      f"Wejście: [{filename}]({source_path}) · [oryginalne źródło]({source['url']}).", "",
                      f"- [Wspólny model JSON-LD](imo.jsonld)",
                      f"- [Projekcja DataCite]({dc_filename})",
                      f"- [Projekcja EDM]({edm_filename})", "- [Raport konwersji](report.json)"]
        if "originalModel" in outputs:
            case_lines.append("- [Model oryginalnej implementacji RDFLib](original-model.imo.jsonld)")
        case_lines += ["", f"Zasoby: {len(model.resources)}. Pełna walidacja schematów: nie.",
                       "Backup źródła nie jest używany do odtworzenia projekcji.", ""]
        if report["rdfComparison"]["status"] == "error":
            case_lines += ["Porównanie ze starą implementacją zakończyło się błędem; szczegóły są w raporcie.", ""]
        (output / "README.md").write_text("\n".join(case_lines), encoding="utf-8")
        print(f"{filename}: {len(model.resources)} resources -> {relative}; RDF comparison: {report['rdfComparison']['status']}")
    save_json(output_root, "summary.json", summary)
    index += ["", "Kolumna równoważności dotyczy EDM → JSON-LD → EDM i jest sprawdzana przez RDFLib z `--compare-rdf`.",
              "Kreska oznacza brak takiego porównania. Pomyślne parsowanie nie oznacza bezstratnej konwersji.",
              "Wielojęzyczne nazwy autorów, nieobsługiwane terminy, role dat i inne szczegóły mogą ginąć; sprawdź raport konkretnego przykładu.",
              "Błędy starej implementacji są raportowane niezależnie od wyniku nowego adaptera.", ""]
    (output_root / "README.md").write_text("\n".join(index), encoding="utf-8")
    print(f"Outputs: {output_root}")
    return summary


def run_example(example_id, output_dir=None, load_only=False, show_diff=False):
    """Load one official fixture, optionally export back and compare meaning."""
    import difflib
    import json
    import os
    from pathlib import Path
    from imo.adapters.datacite import export_datacite
    from imo.adapters.edm import export_edm

    fixtures, sources = official_sources()
    source = next((item for item in sources if item["id"] == example_id), None)
    if source is None:
        raise ValueError("Unknown example: " + example_id + ". Available: " + ", ".join(item["id"] for item in sources))
    model, payload = _load_official_model(fixtures, source)
    output_root = Path(output_dir) if output_dir is not None else Path(__file__).resolve().parent / "examples/output/official-jsonld"
    output = output_root / "selected" / example_id
    output.mkdir(parents=True, exist_ok=True)
    # Only remove known generated comparison artifacts for this selected case.
    for filename in ("report.json", "source-metadata.json", "roundtrip.datacite.json", "roundtrip.edm.xml", "diff.txt"):
        (output / filename).unlink(missing_ok=True)
    serialized = model.to_json()
    (output / "imo.jsonld").write_text(serialized + "\n", encoding="utf-8")
    restored = JsonLDIMO.from_json(serialized)
    report = {"id": example_id, "input": source["file"], "source": source["url"],
              "format": source["format"], "resources": len(restored.resources),
              "mode": "load" if load_only else "roundtrip", "schemaValidated": False,
              "sourceBackupUsedForExport": False, "warnings": restored.provenance.get("warnings", [])}
    lines = [f"# {example_id}: {report['mode']}", "",
             f"[Wejście]({Path(os.path.relpath(fixtures / source['file'], output)).as_posix()}) · [źródło]({source['url']})", "",
             "- [Wczytany model JSON-LD](imo.jsonld)", "- [Raport](report.json)"]
    print(f"Przykład: {example_id}; wczytano {len(restored.resources)} zasobów")
    if not load_only:
        if source["format"] == "datacite":
            attributes = json.loads(payload)["data"]["attributes"]
            before = {key: value for key, value in attributes.items() if key in DATACITE_METADATA}
            after = export_datacite(restored)
            before_text = json.dumps(before, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
            after_text = json.dumps(after, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
            (output / "source-metadata.json").write_text(before_text, encoding="utf-8")
            target = "roundtrip.datacite.json"
            (output / target).write_text(after_text, encoding="utf-8")
            report.update(equal=before == after, scope="DataCite metadata attributes; API/service fields excluded",
                          comparison=_datacite_report(before, after))
            difference = "".join(difflib.unified_diff(before_text.splitlines(keepends=True), after_text.splitlines(keepends=True),
                                                       fromfile="source-metadata.json", tofile=target))
            lines.append("- [Metadane źródłowe porównywane w diffie](source-metadata.json)")
            print("Porównanie: metadane DataCite; pomijamy pola techniczne API i kopertę data.attributes")
        else:
            from rdflib import Graph
            from rdflib.compare import graph_diff, to_isomorphic

            target = "roundtrip.edm.xml"
            exported = export_edm(restored)
            (output / target).write_text(exported, encoding="utf-8")
            original = Graph().parse(data=payload, format="xml", publicID=source["url"])
            projected = Graph().parse(data=exported, format="xml", publicID=source["url"])
            common, removed, added = graph_diff(to_isomorphic(original), to_isomorphic(projected))
            report.update(equal=not removed and not added, scope="RDF assertions; XML formatting and prefixes ignored",
                          preservedTriples=len(common), lostTriples=len(removed), addedTriples=len(added))
            difference = ""
            if removed or added:
                difference = "--- source RDF\n+++ roundtrip RDF\n"
                difference += "".join("- " + line + "\n" for line in sorted(removed.serialize(format="nt").splitlines()))
                difference += "".join("+ " + line + "\n" for line in sorted(added.serialize(format="nt").splitlines()))
            print(f"Porównanie RDF: zachowane {len(common)}, utracone {len(removed)}, dodane {len(added)}")
        difference = difference or "Brak różnic w porównywanym zakresie.\n"
        (output / "diff.txt").write_text(difference, encoding="utf-8")
        lines += [f"- [Eksport powrotny]({target})", "- [Różnice: usunięcia (-), dodania (+)](diff.txt)", "",
                  f"Równoważność w porównywanym zakresie: {'tak' if report['equal'] else 'nie'}.",
                  f"Zakres: {report['scope']}."]
        print("Wynik: " + ("bez różnic" if report["equal"] else "są różnice"))
        if show_diff:
            print(difference, end="")
    (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wyniki: {output}")
    return report


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--example", action="store_true", help="Print the small manually constructed hierarchy")
    mode.add_argument("--case", help="Select one official example ID (default action: round trip)")
    mode.add_argument("--list-examples", action="store_true", help="List official example IDs")
    parser.add_argument("--load-only", action="store_true", help="With --case: load and save JSON-LD only")
    parser.add_argument("--show-diff", action="store_true", help="With --case: print the source-format round-trip diff")
    parser.add_argument("--output-dir", help="Directory for per-format, per-example outputs and index")
    parser.add_argument("--compare-rdf", action="store_true", help="Also run the original RDF model and independent RDF/XML comparison")
    args = parser.parse_args()
    if (args.load_only or args.show_diff) and not args.case:
        parser.error("--load-only and --show-diff require --case")
    if args.load_only and args.show_diff:
        parser.error("--load-only cannot be combined with --show-diff")
    if args.case and args.compare_rdf:
        parser.error("--compare-rdf compares the historical model in batch mode; --case compares the new round trip")
    if args.example:
        print(example().to_json())
    elif args.list_examples:
        for source in official_sources()[1]:
            print(f"{source['id']}: {source['format']} — {source['description']}")
    elif args.case:
        try:
            run_example(args.case, args.output_dir, args.load_only, args.show_diff)
        except (ValueError, OSError) as error:
            parser.error(str(error))
    else:
        run_official(output_dir=args.output_dir, compare_rdf=args.compare_rdf)
