"""DataCite JSON attributes and JSON:API import/export for direct JSON-LD.

Declarative rules live in imo.mappings.datacite. This adapter constructs
resources and converts values; it does not replay source backups.
"""
from copy import deepcopy

from ..json_model import JsonLDIMO, _absolute_id
from ..mappings.datacite import (
    RESOURCE_TYPE_MAP, DEFAULT_RESOURCE_TYPE,
    AGENT_TYPE_MAP, AGENT_TYPE_EXPORT_MAP, DEFAULT_AGENT_TYPE, AGENT_FIELDS,
    TYPE_FIELDS, SCALAR_FIELDS, TEXT_FIELDS, TEXT_QUALIFIER_EXCLUSIONS,
    TEXT_EXPORT_DEFAULTS, DESCRIPTION_TYPE_MAP, DESCRIPTION_TYPE_EXPORT_MAP,
    RELATION_MAP, IDENTIFIER_PREFIXES, REQUIRED_FIELDS,
)
from .common import _root, _text


def _item(value, key):
    result = {key: value["@value"]}
    if "@language" in value:
        result["lang"] = value["@language"]
    return result


def _identifier_uri(item):
    kind, value = item.get("relatedIdentifierType"), item.get("relatedIdentifier", "")
    if kind in IDENTIFIER_PREFIXES and value:
        return IDENTIFIER_PREFIXES[kind] + value
    if kind == "URL" and value.startswith(("https://", "http://")):
        return value
    return None


def _import_texts(attributes, node, source_field):
    target, value_key, language_key = TEXT_FIELDS[source_field]
    qualifier = TEXT_QUALIFIER_EXCLUSIONS.get(source_field)
    values = [
        _text(item[value_key], item.get(language_key) if language_key else None)
        for item in attributes.get(source_field, [])
        if qualifier is None or not item.get(qualifier)
    ]
    if values:
        node[target] = values


def _export_texts(root, result, source_field):
    target, value_key, language_key = TEXT_FIELDS[source_field]
    if root.get(target):
        values = []
        for value in root[target]:
            if "@value" not in value:
                continue
            item = {value_key: value["@value"]}
            if language_key and "@language" in value:
                item[language_key] = value["@language"]
            item.update(TEXT_EXPORT_DEFAULTS.get(source_field, {}))
            values.append(item)
        result[source_field] = values


def parse_datacite(document, source_uri="urn:example:datacite"):
    """Accept DataCite attributes or a single-record JSON:API response."""
    if not isinstance(document, dict):
        raise ValueError("Expected a DataCite object")
    attributes = document
    if "data" in document:
        record = document["data"]
        if not isinstance(record, dict) or record.get("type") != "dois" or not isinstance(record.get("attributes"), dict):
            raise ValueError("Expected a single DataCite DOI API record")
        attributes = record["attributes"]
    doi = attributes.get("doi")
    root = IDENTIFIER_PREFIXES["DOI"] + doi if doi else "urn:imo:datacite-resource"
    general = (attributes.get("types") or {}).get("resourceTypeGeneral")
    node = {"@id": root, "@type": RESOURCE_TYPE_MAP.get(general, DEFAULT_RESOURCE_TYPE)}
    for source_field, target in TYPE_FIELDS.items():
        value = (attributes.get("types") or {}).get(source_field)
        if value:
            node[target] = value
    if doi:
        node["doi"] = doi
    resources = [node]
    warnings = []
    _import_texts(attributes, node, "titles")
    for index, creator in enumerate(attributes.get("creators", [])):
        identifier = f"{root}#creator-{index}"
        agent = {"@id": identifier, "@type": AGENT_TYPE_MAP.get(creator.get("nameType"), DEFAULT_AGENT_TYPE), "name": creator["name"]}
        for source_field, target in AGENT_FIELDS.items():
            if creator.get(source_field):
                agent[target] = creator[source_field]
        # Bare identifier strings do not assert identifier schemes or identity.
        ids = []
        for position, item in enumerate(creator.get("nameIdentifiers", [])):
            value = item.get("nameIdentifier")
            if value:
                ids.append(value)
            else:
                warnings.append({
                    "path": f"/creators/{index}/nameIdentifiers/{position}",
                    "reason": "Identifier has no value; skipped in normalized metadata and retained in source backup",
                })
        if ids:
            agent["identifiers"] = ids
        resources.append(agent)
        node.setdefault("creators", []).append({"@id": identifier})
    publisher = attributes.get("publisher")
    if publisher:
        identifier = f"{root}#publisher"
        resources.append({"@id": identifier, "@type": "Organization",
                          "name": publisher["name"] if isinstance(publisher, dict) else publisher})
        node["publishers"] = [{"@id": identifier}]
    if attributes.get("publicationYear") is not None:
        node["publicationYear"] = str(attributes["publicationYear"])
    for description in attributes.get("descriptions", []):
        target = DESCRIPTION_TYPE_MAP.get(description.get("descriptionType"))
        if target:
            node.setdefault(target, []).append(_text(description["description"], description.get("lang")))
    for source_field in ("subjects", "dates"):
        _import_texts(attributes, node, source_field)
    for rights in attributes.get("rightsList", []):
        uri = rights.get("rightsUri")
        if uri and _absolute_id(uri):
            value = {"@id": uri}
        elif rights.get("rights"):
            value = _text(rights["rights"], rights.get("lang"))
        else:
            continue
        node.setdefault("rights", []).append(value)
    for item in attributes.get("relatedIdentifiers", []):
        predicate, target = RELATION_MAP.get(item.get("relationType")), _identifier_uri(item)
        if predicate and target:
            node.setdefault(predicate, []).append({"@id": target})
    for source_field, target in SCALAR_FIELDS.items():
        if attributes.get(source_field):
            node[target] = attributes[source_field]
    model = JsonLDIMO(root, resources, {"sourceFormat": "datacite", "source": source_uri},
                      {"format": "datacite", "document": deepcopy(document)})
    if warnings:
        model.provenance["warnings"] = warnings
    model.validate()
    return model


def missing_datacite_fields(document):
    """Minimum fields only, not full DataCite schema validation."""
    return [key for key in REQUIRED_FIELDS if not document.get(key)]


def export_datacite(imo):
    """Project canonical assertions only; never replay the JSON/XML backup."""
    root = _root(imo)
    nodes = {node["@id"]: node for node in imo.resources}
    result = {}
    if root.get("doi"):
        result["doi"] = root["doi"]
    _export_texts(root, result, "titles")
    agents = []
    for ref in root.get("creators", []):
        agent = nodes.get(ref["@id"], {})
        item = {"name": agent.get("name", ref["@id"])}
        name_type = AGENT_TYPE_EXPORT_MAP.get(agent.get("@type"))
        if name_type:
            item["nameType"] = name_type
        for source_field, target in AGENT_FIELDS.items():
            if target in agent:
                item[source_field] = agent[target]
        agents.append(item)
    if agents:
        result["creators"] = agents
    publishers = root.get("publishers", [])
    if len(publishers) == 1:
        ref = publishers[0]["@id"]
        result["publisher"] = nodes.get(ref, {}).get("name", ref)
    if root.get("publicationYear"):
        result["publicationYear"] = int(root["publicationYear"])
    if root.get("resourceTypeGeneral"):
        result["types"] = {
            source_field: root[target]
            for source_field, target in TYPE_FIELDS.items() if root.get(target)
        }
    descriptions = []
    for key, kind in DESCRIPTION_TYPE_EXPORT_MAP.items():
        descriptions.extend(dict(_item(value, "description"), descriptionType=kind) for value in root.get(key, []) if "@value" in value)
    if descriptions:
        result["descriptions"] = descriptions
    for source_field in ("subjects", "dates"):
        _export_texts(root, result, source_field)
    if root.get("rights"):
        result["rightsList"] = [{"rightsUri": v["@id"]} if "@id" in v else _item(v, "rights") for v in root["rights"]]
    if root.get("identifiers"):
        result["alternateIdentifiers"] = [{"alternateIdentifier": value, "alternateIdentifierType": "Unqualified identifier"} for value in root["identifiers"]]
    related = []
    for kind, predicate in RELATION_MAP.items():
        for ref in root.get(predicate, []):
            uri = ref["@id"]
            if uri.startswith(IDENTIFIER_PREFIXES["DOI"]):
                value, scheme = uri.removeprefix(IDENTIFIER_PREFIXES["DOI"]), "DOI"
            elif uri.startswith(("https://", "http://")):
                value, scheme = uri, "URL"
            else:
                continue
            related.append({"relatedIdentifier": value, "relatedIdentifierType": scheme, "relationType": kind})
    if related:
        result["relatedIdentifiers"] = related
    for source_field, target in SCALAR_FIELDS.items():
        if target in root:
            result[source_field] = root[target]
    return result


