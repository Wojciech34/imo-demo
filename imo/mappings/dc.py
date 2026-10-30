"""Supported DC/DCT term mappings to canonical IMO fields.

The source vocabulary defines names; this module defines our conversion
policy. It is reusable independently of any EDM or DC document parser.
"""
from ..vocabularies import dc

DC_PROPERTIES = {
    dc.TITLE: "titles", dc.DESCRIPTION: "descriptions",
    dc.IDENTIFIER: "identifiers", dc.DATE: "dates",
    dc.SUBJECT: "subjects", dc.RIGHTS: "rights",
    dc.COVERAGE: "coverage", dc.TYPE: "resourceTypes",
    dc.LANGUAGE: "language", dc.CREATOR: "creators",
    dc.PUBLISHER: "publishers",
}
DCT_PROPERTIES = {dc.HAS_PART: "hasPart", dc.IS_PART_OF: "isPartOf"}

DC_LINKS = {"creators", "publishers"}
DCT_LINKS = {"hasPart", "isPartOf"}
DC_STRINGS = {"language"}
