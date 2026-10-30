"""RDF namespace and expanded XML names used by the direct adapters.

Expanded names use ElementTree/lxml's ``{namespace}local`` notation. These are
syntax names, not metadata mappings. Defining a name here does not mean that
every adapter supports the construct (e.g. nodeID and parseType are rejected
by the flat EDM profile).
"""

RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"

RDF_ROOT = f"{{{RDF}}}RDF"
ABOUT = f"{{{RDF}}}about"
RESOURCE = f"{{{RDF}}}resource"
DATATYPE = f"{{{RDF}}}datatype"
NODE_ID = f"{{{RDF}}}nodeID"
PARSE_TYPE = f"{{{RDF}}}parseType"
