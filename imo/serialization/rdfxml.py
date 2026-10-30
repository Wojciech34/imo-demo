"""Read/write a flat, named RDF/XML subset without metadata-specific rules.

Values are represented as JSON-LD @id or @value objects. This module handles
XML base, language scope and RDF syntax, but knows nothing about EDM, DC or
the IMO model. It is not a general RDF/XML or JSON-LD processor.
"""
from urllib.parse import urljoin

from lxml import etree

from ..vocabularies.rdf import (
    RDF, RDF_ROOT, ABOUT, RESOURCE, DATATYPE, NODE_ID, PARSE_TYPE,
)
from ..vocabularies.xml import BASE, LANG


def term_uri(tag):
    """Expand an XML name, independently of the document's chosen prefix."""
    name = etree.QName(tag)
    return (name.namespace or "") + name.localname


def parse_document(xml, source_uri):
    parser = etree.XMLParser(
        resolve_entities=False, no_network=True, load_dtd=False,
        remove_comments=True, remove_pis=True,
    )
    tree = etree.fromstring(
        xml.encode() if isinstance(xml, str) else xml,
        parser, base_url=source_uri,
    )
    if tree.getroottree().docinfo.doctype:
        raise ValueError("DTD is outside the supported RDF/XML profile")
    if tree.tag != RDF_ROOT:
        raise ValueError("Expected rdf:RDF")
    return tree


def resolve_identifier(element, identifier, source_uri):
    """lxml's element.base accounts for inherited and relative xml:base."""
    return urljoin(element.base or source_uri, identifier)


def language(element):
    """Nearest xml:lang wins; an empty value cancels the inherited language."""
    for ancestor in (element, *element.iterancestors()):
        value = ancestor.get(LANG)
        if value is not None:
            return value or None
    return None


def resource_id(element, source_uri):
    about = element.get(ABOUT)
    if about is None:
        raise ValueError("The flat RDF/XML profile requires rdf:about")
    if set(element.attrib) - {ABOUT, BASE, LANG}:
        raise ValueError("RDF/XML node attributes outside the supported profile")
    return resolve_identifier(element, about, source_uri)


def read_value(element, source_uri):
    """Decode one flat RDF property; the caller interprets its predicate."""
    if len(element) or PARSE_TYPE in element.attrib or NODE_ID in element.attrib:
        raise ValueError("Nested/anonymous RDF/XML syntax is outside the flat profile")
    if set(element.attrib) - {RESOURCE, LANG, BASE, DATATYPE}:
        raise ValueError("RDF/XML property attributes outside the supported profile")
    reference = element.get(RESOURCE)
    datatype = element.get(DATATYPE)
    if reference is not None:
        if datatype is not None or (element.text or "").strip():
            raise ValueError("An RDF reference cannot also have a datatype or literal text")
        return {"@id": resolve_identifier(element, reference, source_uri)}
    value = {"@value": element.text or ""}
    if datatype is not None:
        # RDF typed literals do not inherit xml:lang.
        value["@type"] = resolve_identifier(element, datatype, source_uri)
    else:
        lang = language(element)
        if lang:
            value["@language"] = lang
    return value


def new_document(namespaces):
    return etree.Element(RDF_ROOT, nsmap={"rdf": RDF, **namespaces})


def _expanded_name(uri, element):
    namespaces = sorted(set(element.nsmap.values()), key=len, reverse=True)
    for namespace in namespaces:
        if uri.startswith(namespace) and uri != namespace:
            return f"{{{namespace}}}{uri[len(namespace):]}"
    raise ValueError(f"No declared XML namespace for term: {uri}")


def add_resource(document, type_uri, identifier):
    element = etree.SubElement(document, _expanded_name(type_uri, document))
    element.set(ABOUT, identifier)
    return element


def add_property(resource, predicate, value):
    """Encode an expanded JSON-LD reference or string literal value."""
    if set(value) == {"@id"}:
        child = etree.SubElement(resource, _expanded_name(predicate, resource))
        child.set(RESOURCE, value["@id"])
        return child
    if ("@value" not in value or value.keys() - {"@value", "@language", "@type"}
            or not isinstance(value["@value"], str)
            or ("@language" in value and "@type" in value)):
        raise ValueError("Expected an @id reference or a string JSON-LD literal")
    child = etree.SubElement(resource, _expanded_name(predicate, resource))
    child.text = value["@value"]
    if "@type" in value:
        child.set(DATATYPE, value["@type"])
    elif "@language" in value:
        child.set(LANG, value["@language"])
    return child


def serialize_document(document):
    return etree.tostring(document, encoding="unicode", pretty_print=True)
