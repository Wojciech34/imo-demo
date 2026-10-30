"""Run with python demo.py after installing dependencies; no network is used."""
from pathlib import Path
import json
from rdflib import Graph
from imo.rdf_model import IMO
from imo.parsers.datacite import parse_datacite
from imo.parsers.edm import parse_edm
from imo.converters.datacite import export_datacite
from imo.converters.edm import export_edm, edm_xml
from imo.compare import compare_json, compare_rdf, cross_report
from imo.examples import dataset_hierarchy

BASE = Path(__file__).resolve().parent


def encode(value):
    return (json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode()


def main():
    inputs, outputs = BASE / "examples/input", BASE / "examples/output"
    outputs.mkdir(exist_ok=True)
    def save(name, value):
        payload = value if isinstance(value, bytes) else value.encode() if isinstance(value, str) else encode(value)
        (outputs / name).write_bytes(payload)
        return payload

    original_dc = (inputs / "datacite.json").read_bytes()
    dc_data = json.loads(original_dc)
    dc = parse_datacite(dc_data)
    dc_document = dc.to_jsonld()
    save("datacite.imo.jsonld", dc_document)
    print("DataCite → IMO JSON-LD (three named graphs):")
    print(encode(dc_document).decode())
    # All experiments cross the serialized IMO boundary; no Python-only state.
    dc = IMO.from_jsonld(json.loads((outputs / "datacite.imo.jsonld").read_bytes()))
    dc_projection = export_datacite(dc)
    dc_preserved = export_datacite(dc, preserve=True)
    projection_bytes = save("datacite.projected.json", dc_projection)
    preserved_bytes = save("datacite.preserved.json", dc_preserved)
    dc_reports = {"semantic_projection": compare_json(original_dc, dc_data, dc_projection, projection_bytes),
                  "with_json_residuals": compare_json(original_dc, dc_data, dc_preserved, preserved_bytes),
                  "json_residual_keys": sorted(dc.residual),
                  "preservation_note": "JSON residuals are structured source backups, not semantic mappings; no raw bytes retained"}
    # Prove an independently constructed supported subset really is reversible.
    subset = {"doi": "10.82433/imo-demo.subset", "titles": [{"title": "Minimal supported mapping", "lang": "en"}],
              "creators": [{"name": "Example Institute", "nameType": "Organizational"}],
              "publisher": "Example Institute", "publicationYear": 2026,
              "types": {"resourceTypeGeneral": "Dataset"}}
    subset_imo = IMO.from_jsonld(parse_datacite(subset).to_jsonld())
    subset_out = export_datacite(subset_imo)
    dc_reports["supported_subset"] = {"structural_equal": subset_out == subset,
                                       "residual_count": len(subset_imo.residual), "input": subset, "output": subset_out}
    save("datacite.roundtrip-report.json", dc_reports)

    original_edm = (inputs / "edm.xml").read_bytes()
    edm = parse_edm(original_edm)
    save("edm.imo.jsonld", edm.to_jsonld())
    edm = IMO.from_jsonld(json.loads((outputs / "edm.imo.jsonld").read_bytes()))
    native_source = Graph().parse(data=original_edm, format="xml")
    edm_reports = {}
    for mode, preserve in [("projection", False), ("native", True)]:
        target = export_edm(edm, preserve=preserve)
        payload = save(f"edm.{mode}.xml", edm_xml(target))
        # Parse the actual target bytes, including serializer effects.
        reparsed = Graph().parse(data=payload, format="xml")
        edm_reports[mode] = compare_rdf(original_edm, native_source, reparsed, payload)
    edm_reports["preservation_note"] = "Native graph replay preserves RDF terms and connections, not XML syntax or a reversible canonical projection"
    save("edm.roundtrip-report.json", edm_reports)

    cross = export_datacite(edm)
    save("edm-to-datacite.draft.json", cross)
    cross_results = cross_report(edm, cross)
    save("edm-to-datacite.report.json", cross_results)
    save("datacite-to-edm.draft.xml", edm_xml(export_edm(dc)))
    hierarchy = dataset_hierarchy(dc, inputs / "files")
    save("dataset-hierarchy.imo.jsonld", hierarchy.to_jsonld())
    summary = {"datacite": {"projection_structural_equal": dc_reports["semantic_projection"]["structural_equal"],
                            "residual_structural_equal": dc_reports["with_json_residuals"]["structural_equal"],
                            "byte_equal": dc_reports["with_json_residuals"]["byte_equal"],
                            "residual_keys": dc_reports["json_residual_keys"],
                            "supported_subset": dc_reports["supported_subset"]},
               "edm": edm_reports, "cross_schema_missing_required": cross_results["missing_required"],
               "hierarchy": "Dataset → directory (Dataset + imo:Directory) → 2 MediaObject files; actual fixture sizes and SHA-256"}
    save("summary.json", summary)
    print("\nDataCite semantic projection, field by field:")
    for row in dc_reports["semantic_projection"]["properties"]:
        print(f"  {row['property']}: {row['status']}")
    print("\nEDM → DataCite draft (requires curation):")
    print(encode(cross).decode())
    print("\nMeasured results:")
    print(encode(summary).decode())
    print("Property-level preserved/transformed/lost reports and all outputs:", outputs)
    assert dc_reports["with_json_residuals"]["structural_equal"]
    assert dc_reports["supported_subset"]["structural_equal"]
    assert edm_reports["native"]["rdf_isomorphic"]
    return summary


if __name__ == "__main__":
    main()
