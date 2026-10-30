"""Dublin Core namespace and term URIs; no IMO mapping rules."""

DC = "http://purl.org/dc/elements/1.1/"
DCT = "http://purl.org/dc/terms/"

# DC Elements terms used by the current adapters.
TITLE = DC + "title"
DESCRIPTION = DC + "description"
IDENTIFIER = DC + "identifier"
DATE = DC + "date"
SUBJECT = DC + "subject"
RIGHTS = DC + "rights"
COVERAGE = DC + "coverage"
TYPE = DC + "type"
LANGUAGE = DC + "language"
CREATOR = DC + "creator"
PUBLISHER = DC + "publisher"

# Additional DCT terms used by the current adapters.
HAS_PART = DCT + "hasPart"
IS_PART_OF = DCT + "isPartOf"
