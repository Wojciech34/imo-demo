import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest
from rdflib import Dataset, Graph, Literal, RDF, URIRef
from rdflib.compare import isomorphic

from demo_json import run_official
from imo.json_adapters import parse_datacite, parse_edm, export_datacite, export_edm, missing_datacite_fields
from imo.json_model import JsonLDIMO
from imo.rdf_model import DCT, EDM, S

FIXTURES = Path(__file__).resolve().parents[1] / "examples/input/official"
MANIFEST = json.loads((FIXTURES / "sources.json").read_text())
EDM_URL = next(s["url"] for s in MANIFEST["sources"] if s["file"] == "edm.xml")


def test_official_snapshots_match_manifest():
    for source in MANIFEST["sources"]:
        assert hashlib.sha256((FIXTURES / source["file"]).read_bytes()).hexdigest() == source["sha256"]


@pytest.mark.parametrize("filename", [s["file"] for s in MANIFEST["sources"] if s["format"] == "datacite"])
def test_official_datacite_api_envelope_publisher_and_jsonld_semantics(filename):
    document = json.loads((FIXTURES / filename).read_text())
    attributes = document["data"]["attributes"]
    model = JsonLDIMO.from_json(parse_datacite(document).to_json())
    result = export_datacite(model)
    assert result["publisher"] == attributes["publisher"]["name"]
    assert result["doi"] == attributes["doi"]
    assert result["publicationYear"] == attributes["publicationYear"]
    assert not missing_datacite_fields(result)
    assert result != attributes  # source backup is not replayed as a projection
    dataset = Dataset().parse(data=model.to_json(), format="json-ld")
    graph = dataset.graph(URIRef("urn:imo:record"))
    expected_type = {"Dataset": S.Dataset, "Collection": S.Collection}.get(attributes["types"]["resourceTypeGeneral"], S.CreativeWork)
    assert (URIRef(model.root), RDF.type, expected_type) in graph
    assert (URIRef(model.root), DCT.title, Literal(attributes["titles"][0]["title"], lang=attributes["titles"][0].get("lang"))) in graph
    assert (URIRef(model.root), DCT.issued, Literal(str(attributes["publicationYear"]), datatype=URIRef("http://www.w3.org/2001/XMLSchema#gYear"))) in graph
    model.source = None
    assert export_datacite(model) == result
    model.resources[0]["titles"] = [{"@value": "Edited title"}]
    assert export_datacite(model)["titles"] == [{"title": "Edited title"}]


def test_official_edm_roundtrip_is_independently_isomorphic_without_backup():
    payload = (FIXTURES / "edm.xml").read_bytes()
    model = JsonLDIMO.from_json(parse_edm(payload, EDM_URL).to_json())
    assert len(model.resources) == 6
    model.source = None
    original = Graph().parse(data=payload, format="xml", publicID=EDM_URL)
    projected = Graph().parse(data=export_edm(model), format="xml", publicID=EDM_URL)
    assert len(original) == len(projected) == 29
    assert isomorphic(original, projected)
    # Relative source IDs are resolved against the document URL.
    assert model.root == EDM_URL + "#ULEI:M0003309"
    assert all(row["status"] == "mapped" for row in model.provenance["mapping"])


def test_cross_edm_to_datacite_keeps_rights_on_the_digital_resource():
    model = parse_edm((FIXTURES / "edm.xml").read_bytes(), EDM_URL)
    image = next(node for node in model.resources if node["@type"] == "WebResource")
    assert image["digitalRights"] == [{"@id": "http://creativecommons.org/licenses/by-nc-sa/3.0/"}]
    result = export_datacite(model)
    assert "rightsList" not in result
    assert result["dates"] == [{"date": "ca. 1890/1930", "dateType": "Other"}]
    assert missing_datacite_fields(result) == ["doi", "creators", "publisher", "publicationYear", "types"]


def test_cross_datacite_to_edm_is_a_cho_view_without_invented_digital_objects():
    model = parse_datacite(json.loads((FIXTURES / "datacite-dataset.json").read_text()))
    graph = Graph().parse(data=export_edm(model), format="xml")
    root = URIRef(model.root)
    assert (root, RDF.type, EDM.ProvidedCHO) in graph
    assert not list(graph.subjects(RDF.type, EDM.WebResource))
    assert not list(graph.objects(root, EDM.rights))


def test_demo_generates_reports_and_original_model_comparison(tmp_path):
    summary = run_official(tmp_path, compare_rdf=True)
    assert len(summary["records"]) == len(MANIFEST["sources"])
    for record in summary["records"]:
        for output_file in record["outputs"].values():
            assert (tmp_path / output_file).is_file()
    report = json.loads((tmp_path / "edm/edm/report.json").read_text())
    assert report["rdfComparison"]["directProjectionIsomorphic"]
    assert report["rdfComparison"]["originalModelNativeReplayIsomorphic"]
    full = json.loads((tmp_path / "datacite/datacite-full/report.json").read_text())
    fields = {entry["field"]: entry["status"] for entry in full["dataciteRoundtrip"]["fields"]}
    assert fields["doi"] == "exact"
    assert fields["titles"] == "partial"
    assert fields["fundingReferences"] == "not_projected"
    assert fields["xml"] == "api_attribute_not_projected"
    assert not full["sourceBackupUsedForExport"]
    assert not full["schemaValidated"]
    award = json.loads((tmp_path / "datacite/datacite-award/report.json").read_text())
    assert award["rdfComparison"]["status"] == "error"
    assert award["rdfComparison"]["errorType"] == "KeyError"
    assert award["warnings"][0]["path"] == "/creators/0/nameIdentifiers/0"
    assert (tmp_path / "README.md").is_file()
    rerun = run_official(tmp_path, compare_rdf=False)
    assert all(row["comparisonStatus"] == "not_requested" for row in rerun["records"])
    assert not list(tmp_path.rglob("original-model.imo.jsonld"))


def test_missing_creator_identifier_is_reported_and_kept_in_source_backup():
    document = json.loads((FIXTURES / "datacite-award.json").read_text())
    model = parse_datacite(document)
    assert model.source["document"] == document
    assert model.provenance["warnings"][0]["path"] == "/creators/0/nameIdentifiers/0"
    assert "identifiers" not in model.resources[1]
    assert export_datacite(model)["creators"][0]["name"] == "The Research Trust"


@pytest.mark.parametrize("filename", ["edm-image-tier1.xml", "edm-sound-tier1.xml", "edm-3d-complete.xml"])
def test_extended_edm_examples_parse_but_expose_actual_projection_losses(filename):
    source = next(s for s in MANIFEST["sources"] if s["file"] == filename)
    payload = (FIXTURES / filename).read_bytes()
    model = JsonLDIMO.from_json(parse_edm(payload, source["url"]).to_json())
    model.source = None
    original = Graph().parse(data=payload, format="xml", publicID=source["url"])
    projected = Graph().parse(data=export_edm(model), format="xml")
    assert not isomorphic(original, projected)
    assert any(row["status"] == "unmapped" for row in model.provenance["mapping"])


@pytest.mark.parametrize("body", [
    '<!DOCTYPE rdf:RDF [<!ENTITY value "text">]><rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"/>',
    '<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:edm="http://www.europeana.eu/schemas/edm/" xmlns:dc="http://purl.org/dc/elements/1.1/"><edm:ProvidedCHO rdf:about="https://example.org/object"><dc:creator rdf:parseType="Resource"><dc:title>Name</dc:title></dc:creator></edm:ProvidedCHO></rdf:RDF>',
])
def test_edm_rejects_unsupported_xml_syntax(body):
    with pytest.raises(ValueError):
        parse_edm(body, "https://example.org/source.xml")


def test_unknown_edm_property_is_reported_and_backed_up():
    payload = (FIXTURES / "edm.xml").read_text().replace('<dc:date>', '<dc:unknown>').replace('</dc:date>', '</dc:unknown>')
    model = parse_edm(payload, EDM_URL)
    unmapped = [row for row in model.provenance["mapping"] if row["status"] == "unmapped"]
    assert len(unmapped) == 1
    assert unmapped[0]["property"].endswith("unknown")
    assert "<dc:unknown>" in model.source["xml"]


def test_direct_adapters_do_not_import_rdflib():
    subprocess.run([sys.executable, "-c", "import sys; from imo import json_adapters; assert 'rdflib' not in sys.modules"],
                   cwd=FIXTURES.parents[2], check=True)
