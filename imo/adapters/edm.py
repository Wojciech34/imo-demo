"""Flat EDM RDF/XML adapter composed from shared vocabulary mappings.

This adapter applies the profile in imo.mappings.edm and owns resource
construction, metadata projection and resource selection. Shared RDF/XML syntax lives in imo.serialization.rdfxml.
"""
from ..json_model import JsonLDIMO
from ..serialization import rdfxml
from ..mappings.edm import EDM_PROPERTIES, EDM_TYPES, XML_LINKS, XML_STRINGS
from ..vocabularies.dc import DC, DCT
from ..vocabularies.edm import EDM, ORE
from ..vocabularies.skos import SKOS
from .common import _root, _text


def parse_edm(xml, source_uri, root=None):
    """Parse the documented flat EDM subset, resolving relative IDs by XML base."""
    tree = rdfxml.parse_document(xml, source_uri)
    resources, pending_agents, report = [], [], []
    for element in tree:
        kind = EDM_TYPES.get(rdfxml.term_uri(element.tag))
        identifier = rdfxml.resource_id(element, source_uri)
        if not kind:
            report.append({"resource": identifier, "property": "@type", "status": "unmapped", "reason": "Unsupported resource class; retained in XML backup"})
            continue
        node = {"@id": identifier, "@type": kind}
        for index, child in enumerate(element):
            value = rdfxml.read_value(child, source_uri)
            predicate = rdfxml.term_uri(child.tag)
            target = EDM_PROPERTIES.get(predicate)
            entry = {"resource": identifier, "property": predicate, "occurrence": index, "status": "mapped", "target": target}
            if not target or "@type" in value:
                entry.update(status="unmapped", reason="Unsupported property/datatype; retained in XML backup")
                report.append(entry)
                continue
            if target in {"creators", "publishers"} and "@value" in value:
                agent_id = identifier + f"-agent-{index}"
                pending_agents.append({"@id": agent_id, "@type": "Agent", "name": value["@value"]})
                value = {"@id": agent_id}
                entry["reason"] = "Literal name represented by a record-scoped agent"
            if target in XML_LINKS:
                if "@id" not in value:
                    entry.update(status="unmapped", reason="Relation requires a resource reference")
                else:
                    node.setdefault(target, []).append(value)
            elif target in XML_STRINGS:
                if "@value" not in value or target in node or "@language" in value:
                    entry.update(status="unmapped", reason="Scalar field requires one untagged literal")
                else:
                    node[target] = value["@value"]
            elif target == "identifiers":
                if "@value" in value and "@language" not in value:
                    node.setdefault(target, []).append(value["@value"])
                else:
                    entry.update(status="unmapped", reason="Identifier field requires an untagged literal")
            elif target == "titles" and "@value" not in value:
                entry.update(status="unmapped", reason="Title requires a literal")
            else:
                node.setdefault(target, []).append(value)
            report.append(entry)
        resources.append(node)
    roots = [n["@id"] for n in resources if n["@type"] == "ProvidedCHO"]
    if root is None:
        if len(roots) != 1:
            raise ValueError("Select a root when input does not contain exactly one ProvidedCHO")
        root = roots[0]
    if root not in roots:
        raise ValueError("Root must identify a ProvidedCHO")
    resources.extend(pending_agents)
    model = JsonLDIMO(root, resources, {"sourceFormat": "edm", "source": source_uri, "mapping": report},
                      {"format": "edm", "xml": xml.decode() if isinstance(xml, bytes) else xml})
    model.validate()
    return model


def export_edm(imo):
    """Export a flat RDF/XML projection; cross-format CHO views are drafts."""
    _root(imo)
    namespaces = {"dc": DC, "dcterms": DCT, "edm": EDM, "ore": ORE, "skos": SKOS}
    tree = rdfxml.new_document(namespaces)
    reverse_types = {value: key for key, value in EDM_TYPES.items()}
    reverse_properties = {value: key for key, value in EDM_PROPERTIES.items()}
    nodes = {node["@id"]: node for node in imo.resources}
    for node in imo.resources:
        identifier = node["@id"]
        kind = reverse_types.get(node["@type"])
        # A DataCite resource can be viewed as a CHO, but no image/aggregation is invented.
        if kind is None and identifier == imo.root:
            kind = EDM + "ProvidedCHO"
        if kind is None:
            continue
        element = rdfxml.add_resource(tree, kind, identifier)
        properties = dict(node)
        if node.get("abstracts"):
            properties["descriptions"] = node.get("descriptions", []) + node["abstracts"]
        for key, predicate in reverse_properties.items():
            if key not in properties:
                continue
            values = properties[key]
            if isinstance(values, str):
                values = [_text(values)]
            for value in values:
                if isinstance(value, str):
                    value = _text(value)
                # Agent nodes from DataCite are projected as literal names.
                if key in {"creators", "publishers"} and "@id" in value:
                    agent = nodes.get(value["@id"])
                    if agent and agent.get("name"):
                        value = _text(agent["name"])
                rdfxml.add_property(element, predicate, value)
    return rdfxml.serialize_document(tree)


