import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest
from rdflib import Dataset, Literal, RDF, URIRef

from demo_json import example
from imo.json_model import CONTEXT, JsonLDIMO
from imo.rdf_model import DCT, S


def test_jsonld_roundtrip_preserves_values_and_copies():
    model = example()
    model.resources[0]["titles"].append(copy.deepcopy(model.resources[0]["titles"][0]))
    model.source = {"format": "example", "document": {"unmapped": [3, 1, 3], "@context": "opaque backup"}}
    restored = JsonLDIMO.from_json(model.to_json())
    assert restored.to_jsonld() == model.to_jsonld()
    document = model.to_jsonld()
    document["@graph"][1]["name"] = "Changed"
    document["@context"]["name"] = "changed"
    assert restored.resources[1]["name"] == model.resources[1]["name"] == "Jan Kowalski"
    assert CONTEXT["name"] == "schema:name"


def test_document_has_real_jsonld_semantics():
    # RDFLib is an independent verifier here, not part of the new model.
    model = example()
    model.source = {"format": "test", "document": {"values": [2, 1, 2]}}
    dataset = Dataset().parse(data=model.to_json(), format="json-ld")
    graph = dataset.graph(URIRef("urn:imo:record"))
    root = URIRef(model.root)
    assert (root, RDF.type, S.Dataset) in graph
    assert (root, DCT.title, Literal("Pomiary temperatury", lang="pl")) in graph
    assert (root, DCT.creator, URIRef("urn:example:person-1")) in graph
    assert (URIRef("urn:example:person-1"), S.name, Literal("Jan Kowalski")) in graph
    backup = dataset.value(URIRef("urn:imo:record"), URIRef(CONTEXT["imo"] + "sourceBackup"))
    assert backup.datatype == RDF.JSON
    assert json.loads(str(backup)) == model.source


def test_model_and_demo_work_without_third_party_packages():
    subprocess.run([sys.executable, "-S", "-c",
                    "import sys; from demo_json import example; from imo import JsonLDIMO; "
                    "JsonLDIMO.from_json(example().to_json()); assert 'rdflib' not in sys.modules"],
                   cwd=Path(__file__).resolve().parents[1], check=True)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), (1, 2), {1: "value"}, object()])
def test_rejects_non_json_backups(value):
    model = example()
    model.source = {"invalid": value}
    with pytest.raises(ValueError):
        model.to_json()


@pytest.mark.parametrize("change", [
    {"@context": "https://example.org/remote-context"},
    {"root": {"@id": "urn:example:missing"}},
    {"modelVersion": "2.0"},
])
def test_rejects_invalid_documents(change):
    document = example().to_jsonld()
    document.update(change)
    with pytest.raises(ValueError):
        JsonLDIMO.from_jsonld(document)


@pytest.mark.parametrize("change", [
    {"@context": {}},
    {"@id": "relative-id"},
    {"creators": ["urn:example:person-1"]},
    {"titles": [{"@value": 42}]},
    {"titles": [{"@value": "Title", "@language": "pl", "@type": "schema:Text"}]},
    {"unknownProperty": "would silently disappear"},
])
def test_rejects_nodes_outside_profile(change):
    model = example()
    model.resources[0].update(change)
    with pytest.raises(ValueError):
        model.to_jsonld()


def test_rejects_duplicate_ids_but_accepts_external_references():
    model = example()
    model.resources[0]["hasPart"].append({"@id": "https://example.org/external"})
    model.validate()
    model.resources.append(copy.deepcopy(model.resources[0]))
    with pytest.raises(ValueError):
        model.validate()
