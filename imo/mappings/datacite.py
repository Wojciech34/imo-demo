"""Supported DataCite JSON mappings to the direct JSON-LD model.

These tables describe the current lossy subset, not the complete DataCite
schema. Adapters handle envelopes, resource construction and value conversion.
Import and export use the same tables; inverse mappings are derived here.
"""

RESOURCE_TYPE_MAP = {"Dataset": "Dataset", "Collection": "Collection"}
DEFAULT_RESOURCE_TYPE = "CreativeWork"

AGENT_TYPE_MAP = {"Personal": "Person", "Organizational": "Organization"}
AGENT_TYPE_EXPORT_MAP = {target: source for source, target in AGENT_TYPE_MAP.items()}
DEFAULT_AGENT_TYPE = "Agent"
AGENT_FIELDS = {"givenName": "givenName", "familyName": "familyName"}

TYPE_FIELDS = {
    "resourceTypeGeneral": "resourceTypeGeneral",
    "resourceType": "resourceType",
}
SCALAR_FIELDS = {"language": "language", "version": "version"}

# Source list -> (model field, source value key, source language key or None).
TEXT_FIELDS = {
    "titles": ("titles", "title", "lang"),
    "subjects": ("subjects", "subject", "lang"),
    "dates": ("dates", "date", None),
}
# Only unqualified titles enter the common title field.
TEXT_QUALIFIER_EXCLUSIONS = {"titles": "titleType"}
# Original date roles are not modeled; export labels these dates explicitly.
TEXT_EXPORT_DEFAULTS = {"dates": {"dateType": "Other"}}

DESCRIPTION_TYPE_MAP = {"Abstract": "abstracts", "Other": "descriptions"}
DESCRIPTION_TYPE_EXPORT_MAP = {
    target: source for source, target in DESCRIPTION_TYPE_MAP.items()
}
RELATION_MAP = {
    "HasPart": "hasPart", "IsPartOf": "isPartOf",
    "References": "references", "IsDerivedFrom": "sourceResources",
}

IDENTIFIER_PREFIXES = {"DOI": "https://doi.org/"}
REQUIRED_FIELDS = ("doi", "creators", "titles", "publisher", "publicationYear", "types")
