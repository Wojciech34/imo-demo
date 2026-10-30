"""EDM ingestion retains native RDF, with a deliberately narrow core projection."""
from lxml import etree
from rdflib import BNode, Literal, RDF, RDFS, URIRef
from imo.rdf_model import IMO, S, DC, DCT, EDM, copy_graph

# DC elements allow literals; DCT agents have stronger resource ranges. Resolve
# agent literals into nodes instead of asserting dct:creator "a name".
TEXT_MAP = {DC.title: DCT.title, DC.description: DCT.description,
            DC.identifier: DCT.identifier, DC.language: S.inLanguage,
            DC.date: DCT.date,
            DCT.created: DCT.created, DCT.issued: DCT.issued,
            DCT.hasPart: DCT.hasPart, DCT.isPartOf: DCT.isPartOf,
            DC.relation: DCT.relation}
AGENT_MAP = {DC.creator: DCT.creator, DC.contributor: DCT.contributor, DC.publisher: DCT.publisher}


def parse_edm(xml, source_uri="urn:example:edm-input", root=None):
    from rdflib import Graph
    # No DTD, entity expansion, or network access through XML ingestion.
    tree = etree.fromstring(xml.encode() if isinstance(xml, str) else xml,
                            parser=etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False))
    if tree.getroottree().docinfo.doctype:
        raise ValueError("DTD is outside the EDM POC input profile")
    native = Graph().parse(data=etree.tostring(tree), format="xml", publicID=source_uri)
    roots = list(native.subjects(RDF.type, EDM.ProvidedCHO))
    if root is None and len(roots) != 1:
        raise ValueError("Select a ProvidedCHO explicitly when the source does not contain exactly one")
    root = URIRef(root) if root is not None else roots[0]
    if root not in roots:
        raise ValueError("Selected root is not an edm:ProvidedCHO")
    imo = IMO(root, native=copy_graph(native))
    g = imo.graph
    # A heritage object is not automatically a dataset or its digital image.
    g.add((root, RDF.type, S.Thing))
    g.add((root, RDF.type, EDM.ProvidedCHO))
    links = {DCT.hasPart, DCT.isPartOf, DC.relation}
    for source, target in TEXT_MAP.items():
        for value in native.objects(root, source):
            # EDM may refer to contextual resources where record formats expect
            # text. A referenced TimeSpan is not the URI string as a date.
            if source in links and not isinstance(value, Literal):
                g.add((root, target, value))
            elif source not in links and isinstance(value, Literal):
                g.add((root, target, value))
    for value in native.objects(root, DC.rights):
        if isinstance(value, Literal):
            statement = BNode()
            g.add((statement, RDF.type, DCT.RightsStatement))
            g.add((statement, RDFS.label, value))
        else:
            statement = value
        g.add((root, DCT.rights, statement))
    for source, target in AGENT_MAP.items():
        for i, value in enumerate(sorted(native.objects(root, source), key=str)):
            if isinstance(value, Literal):
                agent = URIRef(f"{root}#agent-{source.split('/')[-1]}-{i}")
                g.add((agent, RDF.type, DCT.Agent))
                g.add((agent, S.name, value))
            else:
                agent = value
                # Copy contextual descriptions, including connected blank nodes.
                pending, seen = [agent], set()
                while pending:
                    subject = pending.pop()
                    if subject in seen:
                        continue
                    seen.add(subject)
                    for p, o in native.predicate_objects(subject):
                        g.add((subject, p, o))
                        if isinstance(o, BNode):
                            pending.append(o)
                from rdflib import SKOS
                for label in native.objects(agent, SKOS.prefLabel):
                    g.add((agent, S.name, label))
            g.add((root, target, agent))
    # edm:provider/dataProvider are NOT publishers; edm:rights is NOT a CHO licence.
    imo.seal("edm", source_uri)
    return imo
