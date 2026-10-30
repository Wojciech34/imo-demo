"""Conservative DataCite projection. Missing mandatory fields remain missing."""
import copy
from rdflib import Literal, RDF, RDFS, URIRef, XSD
from imo.rdf_model import S, DCT, OD
from imo.parsers.datacite import DATE_MAP, REL_MAP


def values(graph, root, predicate):
    return sorted(graph.objects(root, predicate), key=lambda v: (str(v), getattr(v, "language", "") or ""))


def text_item(value, key):
    result = {key: str(value)}
    if isinstance(value, Literal) and value.language:
        result["lang"] = value.language
    return result


def agent_item(graph, node):
    name = graph.value(node, S.name)
    result = {"name": str(name if name is not None else node)}
    if (node, RDF.type, S.Person) in graph:
        result["nameType"] = "Personal"
    elif (node, RDF.type, S.Organization) in graph:
        result["nameType"] = "Organizational"
    for key in ("givenName", "familyName"):
        value = graph.value(node, S[key])
        if value is not None:
            result[key] = str(value)
    identifiers = []
    for identifier in values(graph, node, S.identifier):
        scheme, value = graph.value(identifier, S.propertyID), graph.value(identifier, S.value)
        if scheme is not None and value is not None:
            identifiers.append({"nameIdentifier": str(value), "nameIdentifierScheme": str(scheme)})
    if identifiers:
        result["nameIdentifiers"] = identifiers
    affiliations = [{"name": str(graph.value(org, S.name))} for org in values(graph, node, S.affiliation)]
    if affiliations:
        result["affiliation"] = affiliations
    return result


def export_datacite(imo, preserve=False, overrides=None, require_complete=False):
    g, root = imo.graph, imo.root
    out = {}
    alternate = []
    for node in values(g, root, S.identifier):
        scheme, value = g.value(node, S.propertyID), g.value(node, S.value)
        if scheme == Literal("DOI") and value is not None:
            if "doi" in out:
                raise ValueError("Multiple primary DOI candidates require selection")
            out["doi"] = str(value)
        elif scheme is not None and value is not None:
            alternate.append({"alternateIdentifier": str(value), "alternateIdentifierType": str(scheme)})
    # An unqualified heritage accession can be carried as an alternate identifier;
    # the label records uncertainty rather than guessing DOI/ISBN semantics.
    for value in values(g, root, DCT.identifier):
        if isinstance(value, Literal):
            alternate.append({"alternateIdentifier": str(value), "alternateIdentifierType": "Unqualified identifier"})
    if alternate:
        out["alternateIdentifiers"] = alternate
    titles = [text_item(value, "title") for value in values(g, root, DCT.title)]
    if titles:
        out["titles"] = titles
    for key, predicate in [("creators", DCT.creator), ("contributors", DCT.contributor)]:
        agents = [agent_item(g, node) for node in values(g, root, predicate)]
        if agents:
            out[key] = agents
    publishers = values(g, root, DCT.publisher)
    if len(publishers) == 1:
        node = publishers[0]
        out["publisher"] = str(g.value(node, S.name) or node)
    years = {int(str(v)) for v in g.objects(root, DCT.issued) if isinstance(v, Literal) and v.datatype == XSD.gYear and str(v).isdigit()}
    if len(years) == 1:
        out["publicationYear"] = years.pop()
    general = g.value(root, OD.dataciteResourceTypeGeneral)
    if general is not None:
        types = {"resourceTypeGeneral": str(general)}
        resource_types = values(g, root, OD.dataciteResourceType)
        if len(resource_types) == 1:
            types["resourceType"] = str(resource_types[0])
        out["types"] = types
    descriptions = [dict(text_item(v, "description"), descriptionType="Abstract") for v in values(g, root, DCT.abstract)]
    descriptions.extend(dict(text_item(v, "description"), descriptionType="Other")
                        for v in values(g, root, DCT.description))
    if descriptions:
        out["descriptions"] = descriptions
    dates = []
    for kind, predicate in DATE_MAP.items():
        dates.extend({"date": str(v), "dateType": kind} for v in values(g, root, predicate))
    dates.extend({"date": str(v), "dateType": "Other", "dateInformation": "Unqualified dcterms:date"}
                 for v in values(g, root, DCT.date))
    if dates:
        out["dates"] = dates
    rights = []
    for node in values(g, root, DCT.rights):
        if isinstance(node, Literal):
            rights.append(text_item(node, "rights"))
            continue
        item = {}
        label = g.value(node, RDFS.label)
        if label is not None:
            item.update(text_item(label, "rights"))
        if isinstance(node, URIRef):
            item["rightsUri"] = str(node)
        if item:
            rights.append(item)
    if rights:
        out["rightsList"] = rights
    related = []
    for kind, predicate in REL_MAP.items():
        for node in values(g, root, predicate):
            if not isinstance(node, URIRef):
                continue
            uri = str(node)
            if uri.startswith("https://doi.org/"):
                related.append({"relatedIdentifier": uri.removeprefix("https://doi.org/"), "relatedIdentifierType": "DOI", "relationType": kind})
            elif uri.startswith(("http://", "https://")):
                related.append({"relatedIdentifier": uri, "relatedIdentifierType": "URL", "relationType": kind})
    if related:
        out["relatedIdentifiers"] = related
    for key, predicate in [("language", S.inLanguage), ("version", S.version)]:
        items = values(g, root, predicate)
        if len(items) == 1:
            out[key] = str(items[0])
    if preserve:
        imo.assert_fresh("datacite")
        out.update(copy.deepcopy(imo.residual))
    if overrides:
        out.update(copy.deepcopy(overrides))
    missing = missing_required(out)
    if require_complete and missing:
        raise ValueError("Incomplete DataCite projection: " + ", ".join(missing))
    return out


def missing_required(data):
    """A minimum-field check, NOT full DataCite schema validation."""
    missing = [key for key in ("doi", "creators", "titles", "publisher", "publicationYear", "types") if not data.get(key)]
    if data.get("types") and not data["types"].get("resourceTypeGeneral"):
        missing.append("types.resourceTypeGeneral")
    for i, agent in enumerate(data.get("contributors", [])):
        if not agent.get("contributorType"):
            missing.append(f"contributors[{i}].contributorType")
    return missing
