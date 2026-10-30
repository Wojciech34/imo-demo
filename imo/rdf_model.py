"""JSON-LD is the interchange; RDFLib graphs keep adapter code explicit.

Three named graphs separate normalized assertions, native source assertions,
and conversion provenance. DataCite residuals are labelled JSON backups.
"""
from dataclasses import dataclass, field
import hashlib
import json

from rdflib import Dataset, Graph, Literal, Namespace, RDF, URIRef
from rdflib.compare import to_canonical_graph

S = Namespace("https://schema.org/")
DCT = Namespace("http://purl.org/dc/terms/")
DC = Namespace("http://purl.org/dc/elements/1.1/")
PROV = Namespace("http://www.w3.org/ns/prov#")
EDM = Namespace("http://www.europeana.eu/schemas/edm/")
ORE = Namespace("http://www.openarchives.org/ore/terms/")
# A POC namespace, not a published Onedata vocabulary.
OD = Namespace("https://example.org/onedata/imo/0.1/")
CORE = URIRef("urn:imo:canonical")
NATIVE = URIRef("urn:imo:source")
AUDIT = URIRef("urn:imo:provenance")
CONTEXT = {"schema": str(S), "dct": str(DCT), "dc": str(DC),
           "prov": str(PROV), "edm": str(EDM), "ore": str(ORE),
           "imo": str(OD), "rdf": str(RDF),
           "xsd": "http://www.w3.org/2001/XMLSchema#"}


def fingerprint(graph):
    """Stable across RDF blank-node renaming and triple ordering."""
    lines = sorted(to_canonical_graph(graph).serialize(format="nt").splitlines())
    return hashlib.sha256("\n".join(lines).encode()).hexdigest()


def copy_graph(graph):
    result = Graph()
    for triple in graph:
        result.add(triple)
    return result


@dataclass
class IMO:
    root: URIRef
    graph: Graph = field(default_factory=Graph)
    native: Graph = field(default_factory=Graph)
    audit: Graph = field(default_factory=Graph)
    source_format: str | None = None
    baseline: str | None = None
    residual: dict = field(default_factory=dict)

    def seal(self, source_format, source_uri):
        self.source_format = source_format
        self.baseline = fingerprint(self.graph)
        record = URIRef("urn:imo:record")
        activity = URIRef("urn:imo:conversion")
        self.audit.add((record, RDF.type, PROV.Entity))
        self.audit.add((record, S.about, self.root))
        self.audit.add((record, PROV.wasGeneratedBy, activity))
        self.audit.add((activity, RDF.type, PROV.Activity))
        self.audit.add((activity, PROV.used, URIRef(source_uri)))
        self.audit.add((activity, PROV.wasAssociatedWith, URIRef("urn:imo:poc:0.1")))
        self.audit.add((record, OD.sourceFormat, Literal(source_format)))
        self.audit.add((record, OD.canonicalDigest, Literal(self.baseline)))

    def assert_fresh(self, source_format):
        if self.source_format != source_format or self.baseline != fingerprint(self.graph):
            raise ValueError("Source-preserving export requires an unchanged canonical graph and matching source format")

    def to_jsonld(self):
        dataset = Dataset()
        for name, graph in [(CORE, self.graph), (NATIVE, self.native), (AUDIT, self.audit)]:
            for triple in graph:
                dataset.graph(name).add(triple)
        for key, value in self.residual.items():
            node = URIRef("urn:imo:residual:" + key)
            dataset.graph(AUDIT).add((URIRef("urn:imo:record"), OD.residual, node))
            dataset.graph(AUDIT).add((node, OD.jsonKey, Literal(key)))
            dataset.graph(AUDIT).add((node, RDF.value, Literal(json.dumps(value, ensure_ascii=False, sort_keys=True), datatype=RDF.JSON)))
        return json.loads(dataset.serialize(format="json-ld", context=CONTEXT, auto_compact=True))

    @classmethod
    def from_jsonld(cls, document):
        # Only our embedded context is accepted: loading an IMO never fetches URLs.
        if document.get("@context") != CONTEXT:
            raise ValueError("Expected the pinned inline IMO context")
        def check_contexts(value):
            if isinstance(value, dict):
                if "@context" in value:
                    raise ValueError("Nested contexts are outside this POC profile")
                for item in value.values():
                    check_contexts(item)
            elif isinstance(value, list):
                for item in value:
                    check_contexts(item)
        check_contexts({k: v for k, v in document.items() if k != "@context"})
        dataset = Dataset().parse(data=json.dumps(document), format="json-ld")
        audit = copy_graph(dataset.graph(AUDIT))
        record = URIRef("urn:imo:record")
        root = audit.value(record, S.about)
        if not isinstance(root, URIRef):
            raise ValueError("IMO record must identify its root")
        result = cls(root, copy_graph(dataset.graph(CORE)), copy_graph(dataset.graph(NATIVE)), audit)
        result.source_format = str(audit.value(record, OD.sourceFormat))
        digest = audit.value(record, OD.canonicalDigest)
        result.baseline = str(digest) if digest is not None else None
        for node in audit.objects(record, OD.residual):
            result.residual[str(audit.value(node, OD.jsonKey))] = json.loads(str(audit.value(node, RDF.value)))
        return result
