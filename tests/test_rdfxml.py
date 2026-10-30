"""Exercise shared syntax with arbitrary vocabularies, independently of EDM."""
from rdflib import Graph
from rdflib.compare import isomorphic

from imo.serialization import rdfxml


def test_generic_rdfxml_handles_bases_languages_types_and_namespace_identity():
    source_uri = "https://example.org/source/input.xml"
    xml = '''<rdf:RDF
        xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
        xmlns:a="https://example.org/a/" xmlns:b="https://example.org/b/"
        xml:base="https://example.org/catalog/" xml:lang="pl">
      <a:Thing rdf:about="object/1">
        <a:title>Tytuł</a:title>
        <b:title xml:lang="de">Titel</b:title>
        <a:title xml:lang="">No language</a:title>
        <a:image xml:base="../media/" rdf:resource="picture.png"/>
        <a:count rdf:datatype="http://www.w3.org/2001/XMLSchema#integer">7</a:count>
      </a:Thing>
    </rdf:RDF>'''
    document = rdfxml.parse_document(xml, source_uri)
    resource = document[0]
    identifier = rdfxml.resource_id(resource, source_uri)
    values = [rdfxml.read_value(child, source_uri) for child in resource]
    assert identifier == "https://example.org/catalog/object/1"
    assert values == [
        {"@value": "Tytuł", "@language": "pl"},
        {"@value": "Titel", "@language": "de"},
        {"@value": "No language"},
        {"@id": "https://example.org/media/picture.png"},
        {"@value": "7", "@type": "http://www.w3.org/2001/XMLSchema#integer"},
    ]
    # Different namespaces keep identically spelled local names distinct.
    assert rdfxml.term_uri(resource[0].tag) != rdfxml.term_uri(resource[1].tag)
    output = rdfxml.new_document({"a": "https://example.org/a/", "b": "https://example.org/b/"})
    node = rdfxml.add_resource(output, rdfxml.term_uri(resource.tag), identifier)
    for child, value in zip(resource, values):
        rdfxml.add_property(node, rdfxml.term_uri(child.tag), value)
    before = Graph().parse(data=xml, format="xml", publicID=source_uri)
    after = Graph().parse(data=rdfxml.serialize_document(output), format="xml")
    assert isomorphic(before, after)
