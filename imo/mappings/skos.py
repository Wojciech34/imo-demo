"""Supported SKOS term mappings to canonical IMO fields and types."""
from ..vocabularies import skos

SKOS_PROPERTIES = {skos.PREF_LABEL: "labels", skos.ALT_LABEL: "alternativeLabels"}
SKOS_TYPES = {skos.CONCEPT: "Concept"}
