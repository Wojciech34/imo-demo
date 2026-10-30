"""Supported EDM profile composed from DC/DCT, native EDM/ORE and SKOS.

All tables are declarative and independent of the adapter and model. Import
and reverse projection share the same composed property and type mappings.
"""
from ..vocabularies import edm
from .dc import DC_PROPERTIES, DCT_PROPERTIES, DC_LINKS, DCT_LINKS, DC_STRINGS
from .skos import SKOS_PROPERTIES, SKOS_TYPES

EDM_NATIVE_PROPERTIES = {
    edm.TYPE: "edmType", edm.RIGHTS: "digitalRights",
    edm.AGGREGATED_CHO: "aggregatedCHO",
    edm.IS_SHOWN_AT: "isShownAt", edm.IS_SHOWN_BY: "isShownBy",
    edm.HAS_VIEW: "hasView", edm.OBJECT: "preview",
    edm.PROVIDER: "provider", edm.DATA_PROVIDER: "dataProvider",
}
EDM_NATIVE_TYPES = {
    edm.PROVIDED_CHO: "ProvidedCHO", edm.WEB_RESOURCE: "WebResource",
    edm.AGGREGATION: "Aggregation", edm.PLACE: "Place", edm.AGENT: "Agent",
}
EDM_LINKS = {"aggregatedCHO", "isShownAt", "isShownBy", "hasView", "preview"}
EDM_STRINGS = {"edmType", "provider", "dataProvider"}

# Composition is part of the profile, not XML parsing or serialization.
EDM_PROPERTIES = {
    **DC_PROPERTIES, **DCT_PROPERTIES, **EDM_NATIVE_PROPERTIES, **SKOS_PROPERTIES,
}
EDM_TYPES = {**EDM_NATIVE_TYPES, **SKOS_TYPES}
XML_LINKS = DC_LINKS | DCT_LINKS | EDM_LINKS
XML_STRINGS = DC_STRINGS | EDM_STRINGS
