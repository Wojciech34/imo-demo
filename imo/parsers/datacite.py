"""Import DataCite 4.6-style JSON attributes (not REST API envelopes).

Only projections below carry normalized semantics. Residuals are whole JSON
fields that cannot be reconstructed exactly, explicitly not semantic mappings.
"""
import copy
from rdflib import BNode, Literal, RDF, RDFS, URIRef, XSD
from imo.rdf_model import IMO, S, DCT, OD

DATE_MAP = {"Created": DCT.created, "Updated": DCT.modified, "Issued": S.datePublished}
REL_MAP = {"HasPart": DCT.hasPart, "IsPartOf": DCT.isPartOf,
           "IsVersionOf": DCT.isVersionOf, "IsReferencedBy": DCT.isReferencedBy,
           "References": DCT.references, "IsDerivedFrom": DCT.source}
TYPE_MAP = {"Dataset": S.Dataset, "Software": S.CreativeWork, "Text": S.CreativeWork,
            "Image": S.CreativeWork, "Collection": S.Collection, "Other": S.CreativeWork}


def identifier_uri(value, kind):
    if kind == "DOI":
        return URIRef("https://doi.org/" + value)
    if kind == "URL" and value.startswith(("https://", "http://")):
        return URIRef(value)
    return None


def add_identifier(graph, subject, value, scheme):
    node = BNode()
    graph.add((subject, S.identifier, node))
    graph.add((node, RDF.type, S.PropertyValue))
    graph.add((node, S.propertyID, Literal(scheme)))
    graph.add((node, S.value, Literal(value)))


def add_agent(graph, resource, predicate, data, index):
    # ORCID is not inferred from a bare name; internal identity is record scoped.
    node = URIRef(f"{resource}#agent-{index}")
    graph.add((resource, predicate, node))
    kind = {"Personal": S.Person, "Organizational": S.Organization}.get(data.get("nameType"), DCT.Agent)
    graph.add((node, RDF.type, kind))
    graph.add((node, S.name, Literal(data["name"])))
    for key in ("givenName", "familyName"):
        if key in data:
            graph.add((node, S[key], Literal(data[key])))
    for identifier in data.get("nameIdentifiers", []):
        add_identifier(graph, node, identifier["nameIdentifier"], identifier["nameIdentifierScheme"])
    for i, affiliation in enumerate(data.get("affiliation", [])):
        if isinstance(affiliation, dict):
            org = URIRef(f"{node}-affiliation-{i}")
            graph.add((node, S.affiliation, org))
            graph.add((org, RDF.type, S.Organization))
            graph.add((org, S.name, Literal(affiliation["name"])))
    # contributorType remains a residual: a generic contributor loses the role.


def parse_datacite(data, source_uri="urn:example:datacite-input"):
    if not isinstance(data, dict) or "data" in data:
        raise ValueError("Expected a DataCite attributes object, not a REST envelope")
    root = identifier_uri(data.get("doi", ""), "DOI") if data.get("doi") else URIRef("urn:imo:datacite-resource")
    imo = IMO(root)
    g = imo.graph
    types = data.get("types", {})
    general = types.get("resourceTypeGeneral")
    g.add((root, RDF.type, TYPE_MAP.get(general, S.Thing)))
    if general:
        # Keep the actual source classification; do not infer Dataset from EDM TEXT.
        g.add((root, OD.dataciteResourceTypeGeneral, Literal(general)))
    if "resourceType" in types:
        g.add((root, OD.dataciteResourceType, Literal(types["resourceType"])))
    if "doi" in data:
        add_identifier(g, root, data["doi"], "DOI")
    for item in data.get("alternateIdentifiers", []):
        add_identifier(g, root, item["alternateIdentifier"], item["alternateIdentifierType"])
    for item in data.get("titles", []):
        # Typed titles are not all equivalent to the primary title.
        if item.get("titleType") is None:
            g.add((root, DCT.title, Literal(item["title"], lang=item.get("lang"))))
    for predicate, key in [(DCT.creator, "creators"), (DCT.contributor, "contributors")]:
        for i, item in enumerate(data.get(key, [])):
            add_agent(g, root, predicate, item, f"{key}-{i}")
    if "publisher" in data:
        publisher = URIRef(f"{root}#publisher")
        g.add((root, DCT.publisher, publisher))
        g.add((publisher, RDF.type, S.Organization))
        g.add((publisher, S.name, Literal(data["publisher"])))
    if "publicationYear" in data:
        g.add((root, DCT.issued, Literal(str(data["publicationYear"]), datatype=XSD.gYear)))
    for item in data.get("dates", []):
        predicate = DATE_MAP.get(item["dateType"])
        if predicate:
            # Intervals/uncertain dates remain strings: never assert an invalid xsd:date.
            g.add((root, predicate, Literal(item["date"])))
    for item in data.get("descriptions", []):
        if item["descriptionType"] in ("Abstract", "Other"):
            predicate = DCT.abstract if item["descriptionType"] == "Abstract" else DCT.description
            g.add((root, predicate, Literal(item["description"], lang=item.get("lang"))))
    for item in data.get("rightsList", []):
        rights = URIRef(item["rightsUri"]) if item.get("rightsUri") else BNode()
        g.add((root, DCT.rights, rights))
        g.add((rights, RDF.type, DCT.RightsStatement))
        if "rights" in item:
            g.add((rights, RDFS.label, Literal(item["rights"], lang=item.get("lang"))))
        uri = str(rights)
        if uri.startswith(("https://creativecommons.org/licenses/", "http://creativecommons.org/licenses/", "https://spdx.org/licenses/")):
            g.add((root, DCT.license, rights))
            g.add((rights, RDF.type, DCT.LicenseDocument))
    for item in data.get("relatedIdentifiers", []):
        predicate = REL_MAP.get(item["relationType"])
        target = identifier_uri(item["relatedIdentifier"], item["relatedIdentifierType"])
        if predicate and target:
            g.add((root, predicate, target))
    for key, predicate in [("language", S.inLanguage), ("version", S.version)]:
        if key in data:
            g.add((root, predicate, Literal(data[key])))
    # Residual detection exercises the actual reverse projection rather than a field allowlist.
    from imo.converters.datacite import export_datacite
    projected = export_datacite(imo)
    imo.residual = {key: copy.deepcopy(value) for key, value in data.items() if projected.get(key) != value}
    imo.seal("datacite", source_uri)
    return imo
