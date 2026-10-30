"""Native semantic replay or a draft EDM projection, never XML byte replay."""
from rdflib import Graph, RDF, RDFS
from imo.rdf_model import S, DC, DCT, EDM, copy_graph
from imo.parsers.edm import TEXT_MAP, AGENT_MAP


def export_edm(imo, preserve=False):
    if preserve:
        imo.assert_fresh("edm")
        return copy_graph(imo.native)
    g, root = imo.graph, imo.root
    result = Graph()
    # Choosing a ProvidedCHO view is an export policy, not an inferred equivalence.
    result.add((root, RDF.type, EDM.ProvidedCHO))
    for source, canonical in TEXT_MAP.items():
        for value in g.objects(root, canonical):
            result.add((root, source, value))
    for source, canonical in AGENT_MAP.items():
        for agent in g.objects(root, canonical):
            name = g.value(agent, S.name)
            result.add((root, source, name if name is not None else agent))
    for value in g.objects(root, DCT.abstract):
        result.add((root, DC.description, value))
    for value in g.objects(root, DCT.rights):
        result.add((root, DC.rights, value))
    # Convert rights nodes to their URI or statement; never emit orphan blank nodes.
    from rdflib import BNode
    for value in list(result.objects(root, DC.rights)):
        if isinstance(value, BNode):
            result.remove((root, DC.rights, value))
            label = g.value(value, RDFS.label)
            if label is not None:
                result.add((root, DC.rights, label))
    return result


def edm_xml(graph):
    for prefix, namespace in [("dc", DC), ("dcterms", DCT), ("edm", EDM)]:
        graph.bind(prefix, namespace)
    return graph.serialize(format="pretty-xml")
