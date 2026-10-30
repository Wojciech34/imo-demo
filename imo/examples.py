"""Compose a tiny physical hierarchy; checksum/size describe the actual fixtures."""
import hashlib
from rdflib import Literal, RDF, URIRef, XSD
from imo.rdf_model import IMO, S, DCT, OD, PROV, copy_graph


def dataset_hierarchy(source, fixture_dir):
    imo = IMO(source.root, graph=copy_graph(source.graph))
    g, root = imo.graph, imo.root
    directory = URIRef("https://example.org/data/aq-2025/raw/")
    g.add((directory, RDF.type, S.Dataset))
    g.add((directory, RDF.type, OD.Directory))
    g.add((directory, RDF.type, PROV.Collection))
    g.add((directory, DCT.title, Literal("Raw observations and station metadata", lang="en")))
    g.add((root, DCT.hasPart, directory))
    g.add((directory, DCT.isPartOf, root))
    for filename, media in [("stations.csv", "text/csv"), ("stations.json", "application/json")]:
        payload = (fixture_dir / "raw" / filename).read_bytes()
        node = URIRef(str(directory) + filename)
        g.add((directory, DCT.hasPart, node))
        g.add((directory, PROV.hadMember, node))
        g.add((node, DCT.isPartOf, directory))
        g.add((node, RDF.type, S.MediaObject))
        g.add((node, DCT.title, Literal(filename)))
        g.add((node, DCT.identifier, Literal("fixture:raw/" + filename)))
        g.add((node, S.contentSize, Literal(f"{len(payload)} bytes")))
        g.add((node, S.encodingFormat, Literal(media)))
        g.add((node, S.sha256, Literal(hashlib.sha256(payload).hexdigest())))
        g.add((node, DCT.created, Literal("2026-01-12", datatype=XSD.date)))
    # Direct assertions in this synthetic fixture, not a general inheritance rule.
    for node in [directory, URIRef(str(directory) + "stations.csv"), URIRef(str(directory) + "stations.json")]:
        for predicate in [DCT.creator, DCT.license]:
            for value in g.objects(root, predicate):
                g.add((node, predicate, value))
    imo.seal("composite-example", "urn:example:physical-fixtures")
    return imo
