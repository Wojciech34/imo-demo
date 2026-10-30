import hashlib
import json
from pathlib import Path

import pytest
from rdflib import BNode, Graph, Literal, RDF, RDFS, URIRef, XSD
from rdflib.compare import isomorphic

from imo.rdf_model import IMO, S, DCT, EDM, OD, PROV, fingerprint
from imo.parsers.datacite import parse_datacite
from imo.parsers.edm import parse_edm
from imo.converters.datacite import export_datacite, missing_required
from imo.converters.edm import export_edm, edm_xml
from imo.examples import dataset_hierarchy
from imo.compare import json_changes, compare_json, cross_report

INPUT = Path(__file__).resolve().parents[1] / "examples/input"


@pytest.fixture
def dc_data():
    return json.loads((INPUT / "datacite.json").read_text())


@pytest.fixture
def dc(dc_data):
    return parse_datacite(dc_data)


@pytest.fixture
def edm():
    return parse_edm((INPUT / "edm.xml").read_bytes())


def wire(imo):
    return IMO.from_jsonld(json.loads(json.dumps(imo.to_jsonld())))


def test_datacite_rich_roundtrip_and_residual_boundary(dc_data, dc):
    reconstructed = wire(dc)
    assert export_datacite(reconstructed, preserve=True) == dc_data
    projection = export_datacite(reconstructed)
    assert projection != dc_data
    assert projection["doi"] == dc_data["doi"]
    assert projection["publicationYear"] == 2026
    assert "fundingReferences" not in projection
    assert reconstructed.residual["fundingReferences"] == dc_data["fundingReferences"]
    assert projection["creators"][0]["givenName"] == "Anna"
    assert projection["dates"] == [{"date": "2026-01-12", "dateType": "Created"},
                                   {"date": "2026-02-04", "dateType": "Issued"}]
    assert "contributors[0].contributorType" in missing_required(projection)
    assert not missing_required(export_datacite(reconstructed, preserve=True))


def test_real_semantic_subset_without_residuals():
    data = {"doi": "10.82433/example", "titles": [{"title": "Observations", "lang": "en"}],
            "creators": [{"name": "Smith, Alex", "nameType": "Personal", "givenName": "Alex", "familyName": "Smith"}],
            "publisher": "Example Observatory", "publicationYear": 2026,
            "types": {"resourceTypeGeneral": "Dataset"},
            "descriptions": [{"description": "Measurements", "descriptionType": "Abstract"}],
            "relatedIdentifiers": [{"relatedIdentifier": "https://example.org/part", "relatedIdentifierType": "URL", "relationType": "HasPart"}]}
    imo = wire(parse_datacite(data))
    assert not imo.residual
    assert export_datacite(imo) == data


def test_relationship_direction_and_identifier_types(dc):
    g = dc.graph
    assert (dc.root, DCT.hasPart, URIRef("https://example.org/data/aq-2025/raw/")) in g
    assert (URIRef("https://example.org/data/aq-2025/raw/"), DCT.hasPart, dc.root) not in g
    identifiers = list(g.objects(dc.root, S.identifier))
    assert {str(g.value(node, S.propertyID)) for node in identifiers} == {"DOI", "Local accession"}
    assert (dc.root, DCT.issued, Literal("2026", datatype=XSD.gYear)) in g


def test_unknown_json_fields_survive_without_becoming_semantics(dc_data):
    dc_data["x-local-policy"] = {"values": [2, 1, 2], "approved": False, "note": None}
    dc_data["titles"].append({"title": "Unmodelled title", "titleType": "Subtitle"})
    imo = wire(parse_datacite(dc_data))
    assert export_datacite(imo, preserve=True) == dc_data
    assert "x-local-policy" not in export_datacite(imo)


def test_array_order_duplicates_and_qualifiers_are_not_claimed_as_semantic():
    data = {"doi": "10.82433/order", "titles": [{"title": "B"}, {"title": "A"}, {"title": "A"}]}
    imo = wire(parse_datacite(data))
    assert export_datacite(imo)["titles"] == [{"title": "A"}, {"title": "B"}]
    assert export_datacite(imo, preserve=True) == data
    assert "titles" in imo.residual


@pytest.mark.parametrize("source", ["dc", "edm"])
def test_stale_preservation_rejected(source, dc, edm):
    imo = wire(dc if source == "dc" else edm)
    imo.graph.add((imo.root, DCT.title, Literal("Edited title")))
    with pytest.raises(ValueError, match="unchanged canonical"):
        (export_datacite if source == "dc" else export_edm)(imo, preserve=True)


def test_edm_native_roundtrip_including_unknown_blank_nodes(edm):
    imo = wire(edm)
    target = Graph().parse(data=edm_xml(export_edm(imo, preserve=True)), format="xml")
    source = Graph().parse(data=(INPUT / "edm.xml").read_bytes(), format="xml")
    assert isomorphic(source, target)
    assert len(source) == len(target) == 31
    assert any(isinstance(o, BNode) for _, _, o in target)
    assert any(isinstance(o, Literal) and o.language == "pl" for _, _, o in target)
    assert not isomorphic(source, export_edm(imo))
    assert (URIRef("https://example.org/heritage/map-1890"), EDM.currentLocation,
            URIRef("https://example.org/archive/reading-room")) in imo.native


def test_edm_scope_and_cross_schema_semantics(edm):
    imo = wire(edm)
    out = export_datacite(imo)
    assert out["publisher"] == "Example Municipal Archive"
    assert "Example Regional Heritage Portal" not in out["publisher"]
    assert out["dates"] == [{"date": "1890", "dateType": "Other", "dateInformation": "Unqualified dcterms:date"}]
    assert out["descriptions"][0]["descriptionType"] == "Other"
    assert out["alternateIdentifiers"][0]["alternateIdentifier"] == "MA-KRK-1890-17"
    assert "doi" not in out and "publicationYear" not in out and "types" not in out
    assert "rightsUri" not in out["rightsList"][0]
    assert str(imo.graph.value(imo.graph.value(imo.root, DCT.rights), RDFS.label)).startswith("Physical original")
    assert (imo.root, RDF.type, S.Dataset) not in imo.graph
    report = cross_report(imo, out)
    assert any(row["predicate"] == str(EDM.rights) and row["status"] == "not_exported" for row in report["native_assertions"])
    with pytest.raises(ValueError, match="Incomplete DataCite"):
        export_datacite(imo, require_complete=True)


def test_edm_parser_selection_and_dtd_rejection():
    header = '<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:edm="http://www.europeana.eu/schemas/edm/">'
    xml = header + '<edm:ProvidedCHO rdf:about="urn:a"/><edm:ProvidedCHO rdf:about="urn:b"/></rdf:RDF>'
    with pytest.raises(ValueError, match="Select"):
        parse_edm(xml)
    assert parse_edm(xml, root="urn:b").root == URIRef("urn:b")
    with pytest.raises(ValueError, match="DTD"):
        parse_edm('<!DOCTYPE rdf:RDF [<!ENTITY x "bad">]>' + xml)


def test_hierarchy_and_real_file_checksums(dc):
    imo = wire(dataset_hierarchy(dc, INPUT / "files"))
    g = imo.graph
    directory = URIRef("https://example.org/data/aq-2025/raw/")
    assert (imo.root, DCT.hasPart, directory) in g
    assert (directory, RDF.type, OD.Directory) in g
    assert (directory, RDF.type, S.Dataset) in g
    files = list(g.objects(directory, DCT.hasPart))
    assert len(files) == 2
    for node in files:
        payload = (INPUT / "files/raw" / str(node).split("/")[-1]).read_bytes()
        assert (node, RDF.type, S.MediaObject) in g
        assert (node, DCT.isPartOf, directory) in g
        assert str(g.value(node, S.contentSize)) == f"{len(payload)} bytes"
        assert str(g.value(node, S.sha256)) == hashlib.sha256(payload).hexdigest()
        assert set(g.objects(node, DCT.license)) == set(g.objects(imo.root, DCT.license))
    assert list(imo.audit.triples((None, PROV.wasGeneratedBy, None)))


def test_jsonld_roundtrip_graph_equivalence(dc, edm):
    for imo in [dc, edm]:
        restored = wire(imo)
        assert isomorphic(imo.graph, restored.graph)
        assert isomorphic(imo.native, restored.native)
        assert fingerprint(imo.graph) == fingerprint(restored.graph)
        # Stable on a second wire traversal, including residual nodes.
        assert export_datacite(wire(restored)) == export_datacite(restored)


def test_context_is_pinned_and_nested_remote_context_is_rejected(dc):
    document = dc.to_jsonld()
    document["@context"] = "https://example.org/context"
    with pytest.raises(ValueError, match="pinned"):
        IMO.from_jsonld(document)
    document = dc.to_jsonld()
    document["@graph"].append({"@id": "urn:bad", "@context": "https://example.org/remote"})
    with pytest.raises(ValueError, match="Nested"):
        IMO.from_jsonld(document)


def test_measurements_distinguish_structure_bytes_and_numbers():
    report = compare_json(b'{ "x": 1 }', {"x": 1}, {"x": 1}, b'{"x":1}')
    assert report["structural_equal"] and not report["byte_equal"]
    assert json_changes({"x": 1}, {"x": True})
    assert json_changes({"x": [1, 2]}, {"x": [2, 1]})


def test_cross_format_preservation_does_not_replay_unrelated_source(dc, edm):
    with pytest.raises(ValueError):
        export_edm(dc, preserve=True)
    with pytest.raises(ValueError):
        export_datacite(edm, preserve=True)


def test_missing_cardinality_requires_curation(edm):
    edm.graph.add((edm.root, DCT.publisher, URIRef("urn:second-publisher")))
    assert "publisher" not in export_datacite(edm)


def test_native_typed_literals_and_unmapped_referenced_dates_survive():
    xml = '''<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
      xmlns:dc="http://purl.org/dc/elements/1.1/"
      xmlns:edm="http://www.europeana.eu/schemas/edm/"
      xmlns:ex="https://example.org/vocab/">
      <edm:ProvidedCHO rdf:about="urn:test:cho">
        <dc:title xml:lang="en">Sample</dc:title>
        <dc:date rdf:resource="urn:test:timespan"/>
        <ex:count rdf:datatype="http://www.w3.org/2001/XMLSchema#integer">42</ex:count>
      </edm:ProvidedCHO></rdf:RDF>'''
    imo = wire(parse_edm(xml))
    assert not list(imo.graph.objects(imo.root, DCT.date))
    assert "dates" not in export_datacite(imo)
    native = Graph().parse(data=edm_xml(export_edm(imo, preserve=True)), format="xml")
    assert isomorphic(native, Graph().parse(data=xml, format="xml"))
    assert native.value(imo.root, URIRef("https://example.org/vocab/count")).datatype == XSD.integer
