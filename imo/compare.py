"""Comparison measures are intentionally separate; none is universal losslessness."""
from collections import Counter
from rdflib import Literal, URIRef
from rdflib.compare import graph_diff, isomorphic, to_isomorphic
from imo.converters.datacite import missing_required
from imo.rdf_model import DC, DCT


def json_changes(before, after, path=""):
    changes = []
    if isinstance(before, dict) and isinstance(after, dict):
        for key in sorted(before.keys() | after.keys()):
            child = path + "/" + key.replace("~", "~0").replace("/", "~1")
            if key not in after:
                changes.append({"path": child, "status": "lost", "original": before[key]})
            elif key not in before:
                changes.append({"path": child, "status": "added", "reconstructed": after[key]})
            else:
                changes.extend(json_changes(before[key], after[key], child))
    elif isinstance(before, list) and isinstance(after, list):
        for i in range(max(len(before), len(after))):
            child = path + f"/{i}"
            if i >= len(after):
                changes.append({"path": child, "status": "lost", "original": before[i]})
            elif i >= len(before):
                changes.append({"path": child, "status": "added", "reconstructed": after[i]})
            else:
                changes.extend(json_changes(before[i], after[i], child))
    elif before != after or type(before) is not type(after):
        changes.append({"path": path, "status": "transformed", "original": before, "reconstructed": after})
    return changes


def compare_json(original_bytes, original, reconstructed, exported_bytes):
    fields = []
    for key, value in original.items():
        status = "preserved" if reconstructed.get(key) == value else "lost" if key not in reconstructed else "transformed"
        fields.append({"property": key, "status": status})
    return {"byte_equal": original_bytes == exported_bytes,
            "structural_equal": not json_changes(original, reconstructed),
            "rdf_equivalence": "not defined for source DataCite JSON without an agreed RDF mapping",
            "properties": fields, "differences": json_changes(original, reconstructed)}


def compare_rdf(original_bytes, original, reconstructed, exported_bytes):
    common, removed, added = graph_diff(to_isomorphic(original), to_isomorphic(reconstructed))
    def counts(graph):
        return dict(sorted(Counter(str(p) for _, p, _ in graph).items()))
    return {"byte_equal": original_bytes == exported_bytes,
            "xml_structural_equal": "not tested; RDF comparison intentionally ignores XML layout",
            "rdf_isomorphic": isomorphic(original, reconstructed),
            "source_triples": len(original), "reconstructed_triples": len(reconstructed),
            "preserved_triples": len(common), "lost_triples": len(removed), "added_triples": len(added),
            "lost_by_predicate": counts(removed), "added_by_predicate": counts(added)}


def cross_report(imo, datacite):
    """Trace each native EDM assertion, including scope of excluded properties.

    'transformed' is a potential projection, never a claim of full fidelity.
    Details such as language tags on agent names may still be lost.
    """
    root = imo.root
    mapping = {DC.description: "descriptions/Other (not assumed to be an Abstract)",
               DC.identifier: "alternateIdentifiers (unqualified; never promoted to DOI)",
               DC.date: "dates/Other (not publicationYear)", DC.title: "titles (language retained)", DC.creator: "creators (labels; identifiers and contextual detail may be lost)",
               DC.contributor: "contributors (role missing; needs curation)", DC.publisher: "publisher (single value only)",
               DC.language: "language (single value only)", DCT.created: "dates/Created",
               DCT.isPartOf: "relatedIdentifiers/IsPartOf", DCT.hasPart: "relatedIdentifiers/HasPart",
               DC.rights: "rightsList (CHO scope only)"}
    details = []
    for subject, predicate, value in sorted(imo.native, key=lambda t: tuple(str(x) for x in t)):
        reason = mapping.get(predicate) if subject == root else None
        details.append({"subject": str(subject), "predicate": str(predicate), "value": str(value),
                        "object_kind": "literal" if isinstance(value, Literal) else "iri" if isinstance(value, URIRef) else "blank_node",
                        "language": value.language if isinstance(value, Literal) else None,
                        "datatype": str(value.datatype) if isinstance(value, Literal) and value.datatype else None,
                        "status": "transformed" if reason else "not_exported",
                        "target_or_reason": reason or "No implemented meaning-preserving target mapping; retained in native IMO graph"})
    return {"target_status": "incomplete DataCite draft; not registration ready",
            "missing_required": missing_required(datacite),
            "native_assertions": details,
            "warnings": ["edm:provider and edm:dataProvider are not publishers",
                         "Digital edm:rights is not the heritage object's licence",
                         "dc:date 1890 is not a publicationYear",
                         "dc:description is not assumed to be an Abstract",
                         "Local dc:identifier is not a DOI",
                         "edm:type IMAGE does not establish a DataCite resourceTypeGeneral"]}
