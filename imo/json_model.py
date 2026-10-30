"""JSON-LD IMO operated on directly as Python dictionaries, without RDFLib.

This is a pinned compact JSON-LD profile, not a general JSON-LD processor.
The original RDF model and its adapters remain in rdf_model.py.
"""
from copy import deepcopy
from dataclasses import dataclass, field
import json
import math
from urllib.parse import urlsplit

from .vocabularies.dc import DCT
from .vocabularies.edm import EDM, ORE
from .vocabularies.skos import SKOS


CONTEXT = {
    "schema": "https://schema.org/",
    "dct": DCT,
    "imo": "https://example.org/onedata/imo/0.1/",
    "edm": EDM,
    "ore": ORE,
    "skos": SKOS,
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "Dataset": "schema:Dataset",
    "Collection": "schema:Collection",
    "Directory": "imo:Directory",
    "File": "schema:MediaObject",
    "Person": "schema:Person",
    "Organization": "schema:Organization",
    "CreativeWork": "schema:CreativeWork",
    "root": {"@id": "schema:about", "@type": "@id"},
    "modelVersion": "imo:modelVersion",
    "titles": {"@id": "dct:title", "@container": "@set"},
    "name": "schema:name",
    "identifiers": {"@id": "dct:identifier", "@container": "@set"},
    "creators": {"@id": "dct:creator", "@type": "@id", "@container": "@set"},
    "hasPart": {"@id": "dct:hasPart", "@type": "@id", "@container": "@set"},
    "isPartOf": {"@id": "dct:isPartOf", "@type": "@id", "@container": "@set"},
    "mediaType": "schema:encodingFormat",
    "sizeBytes": "imo:sizeBytes",
    "sha256": "schema:sha256",
    "provenance": {"@id": "imo:provenance", "@type": "@json"},
    "source": {"@id": "imo:sourceBackup", "@type": "@json"},
}
# Both adapters use these explicit mappings; no RDF inference is performed.
EXTRA_TYPES = {
    "ProvidedCHO": "edm:ProvidedCHO", "WebResource": "edm:WebResource",
    "Aggregation": "ore:Aggregation", "Place": "edm:Place",
    "Concept": "skos:Concept", "Agent": "edm:Agent",
}
TEXT_SETS = {
    "descriptions": "dct:description", "abstracts": "dct:abstract",
    "dates": "dct:date", "subjects": "dct:subject", "rights": "dct:rights",
    "coverage": "dct:coverage", "resourceTypes": "dct:type",
    "labels": "skos:prefLabel", "alternativeLabels": "skos:altLabel",
    "digitalRights": "edm:rights",
}
LINKS = {
    "publishers": "dct:publisher", "references": "dct:references",
    "sourceResources": "dct:source", "aggregatedCHO": "edm:aggregatedCHO",
    "isShownAt": "edm:isShownAt", "isShownBy": "edm:isShownBy",
    "hasView": "edm:hasView", "preview": "edm:object",
}
STRINGS = {
    "doi": "imo:doi", "resourceTypeGeneral": "imo:dataciteResourceTypeGeneral",
    "resourceType": "imo:dataciteResourceType", "language": "schema:inLanguage",
    "version": "schema:version", "edmType": "edm:type",
    "provider": "edm:provider", "dataProvider": "edm:dataProvider",
    "givenName": "schema:givenName", "familyName": "schema:familyName",
}
CONTEXT.update(EXTRA_TYPES)
CONTEXT.update({key: {"@id": uri, "@container": "@set"} for key, uri in TEXT_SETS.items()})
CONTEXT.update({key: {"@id": uri, "@type": "@id", "@container": "@set"} for key, uri in LINKS.items()})
CONTEXT.update(STRINGS)
CONTEXT["publicationYear"] = {"@id": "dct:issued", "@type": "xsd:gYear"}
TYPES = {"Dataset", "Collection", "Directory", "File", "Person", "Organization", "CreativeWork"} | EXTRA_TYPES.keys()
RELATIONS = {"creators", "hasPart", "isPartOf"} | LINKS.keys()
PROPERTIES = {"titles", "name", "identifiers", "mediaType", "sizeBytes", "sha256", "publicationYear"} | RELATIONS | TEXT_SETS.keys() | STRINGS.keys()


def _check_json(value):
    """Reject Python-only values instead of silently changing them on export."""
    if value is None or type(value) in (str, bool, int):
        return
    if type(value) is float and math.isfinite(value):
        return
    if type(value) is list:
        for item in value:
            _check_json(item)
        return
    if type(value) is dict and all(type(key) is str for key in value):
        for item in value.values():
            _check_json(item)
        return
    raise ValueError("Expected JSON values with string keys and finite numbers")


def _absolute_id(value):
    # Compact vocabulary terms are only allowed for types, not resource IDs.
    return (isinstance(value, str) and value.startswith(("urn:", "https://", "http://"))
            and not any(c.isspace() for c in value)
            and bool(value.removeprefix("urn:"))
            and (value.startswith("urn:") or bool(urlsplit(value).netloc)))


@dataclass
class JsonLDIMO:
    """Direct JSON-LD nodes; all relations use explicit {"@id": ...} objects.

    Only the inline context and property shapes below are supported. JSON
    provenance/source backups are opaque @json values, not mapped assertions.
    External relation targets are allowed. No network requests are performed.
    """

    root: str
    resources: list = field(default_factory=list)
    provenance: dict = field(default_factory=dict)
    source: dict | None = None

    def validate(self):
        _check_json(self.resources)
        _check_json(self.provenance)
        _check_json(self.source)
        if not isinstance(self.resources, list) or not isinstance(self.provenance, dict):
            raise ValueError("Resources must be a list and provenance an object")
        if self.source is not None and not isinstance(self.source, dict):
            raise ValueError("Source must be an object or null")
        if not _absolute_id(self.root):
            raise ValueError("Root must be an absolute HTTP(S) or URN identifier")
        ids = set()
        for node in self.resources:
            if not isinstance(node, dict) or not {"@id", "@type"} <= node.keys() or node.keys() - ({"@id", "@type"} | PROPERTIES):
                raise ValueError("Expected a resource with @id, @type and supported properties")
            identifier = node["@id"]
            if not _absolute_id(identifier) or identifier in ids or identifier == "urn:imo:record":
                raise ValueError("Resource IDs must be absolute, unique and distinct from the record")
            ids.add(identifier)
            if not isinstance(node["@type"], str) or node["@type"] not in TYPES:
                raise ValueError("Unsupported resource type")
            for key, value in node.items():
                if key in RELATIONS:
                    if not isinstance(value, list) or any(not isinstance(ref, dict) or set(ref) != {"@id"} or not _absolute_id(ref["@id"]) for ref in value):
                        raise ValueError("Relations must be lists of absolute @id references")
                elif key == "titles" or key in TEXT_SETS:
                    if not isinstance(value, list):
                        raise ValueError("Titles must be a list of JSON-LD value objects")
                    for title in value:
                        if key in TEXT_SETS and isinstance(title, dict) and set(title) == {"@id"} and _absolute_id(title["@id"]):
                            continue
                        if (not isinstance(title, dict) or "@value" not in title
                                or title.keys() - {"@value", "@language"}
                                or not isinstance(title["@value"], str)
                                or ("@language" in title and (not isinstance(title["@language"], str) or not title["@language"]))):
                            raise ValueError("Titles need string @value and optional @language")
                elif key == "identifiers":
                    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
                        raise ValueError("Identifiers must be a list of strings")
                elif key == "sizeBytes":
                    if type(value) is not int or value < 0:
                        raise ValueError("sizeBytes must be a nonnegative integer")
                elif key == "publicationYear":
                    if not isinstance(value, str) or len(value) != 4 or not value.isascii() or not value.isdigit():
                        raise ValueError("publicationYear must be a four-digit year string")
                elif key in ({"name", "mediaType", "sha256"} | STRINGS.keys()) and not isinstance(value, str):
                    raise ValueError(f"{key} must be a string")
        if self.root not in ids:
            raise ValueError("Root must identify a resource in @graph")

    def to_jsonld(self):
        self.validate()
        document = {"@context": CONTEXT, "@id": "urn:imo:record", "@type": "imo:Record",
                    "modelVersion": "1.0", "root": {"@id": self.root},
                    "@graph": self.resources, "provenance": self.provenance}
        if self.source is not None:
            document["source"] = self.source
        return deepcopy(document)

    def to_json(self):
        return json.dumps(self.to_jsonld(), ensure_ascii=False, indent=2, allow_nan=False)

    @classmethod
    def from_jsonld(cls, document):
        required = {"@context", "@id", "@type", "modelVersion", "root", "@graph", "provenance"}
        if not isinstance(document, dict) or not required <= document.keys() or document.keys() - (required | {"source"}):
            raise ValueError("Expected a complete JsonLDIMO document")
        if document["@context"] != CONTEXT:
            raise ValueError("Expected the pinned inline JSON-LD context")
        if document["modelVersion"] != "1.0" or document["@id"] != "urn:imo:record" or document["@type"] != "imo:Record":
            raise ValueError("Unsupported JSON-LD record or model version")
        root = document["root"]
        if not isinstance(root, dict) or set(root) != {"@id"}:
            raise ValueError("Root must be an @id reference")
        data = deepcopy(document)
        result = cls(data["root"]["@id"], data["@graph"], data["provenance"], data.get("source"))
        result.validate()
        return result

    @classmethod
    def from_json(cls, text):
        return cls.from_jsonld(json.loads(text))
