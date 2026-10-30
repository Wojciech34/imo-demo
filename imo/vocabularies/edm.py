"""EDM and ORE namespace and term URIs; no IMO mapping rules.

ORE is grouped here because it describes the EDM aggregation structure.
"""

EDM = "http://www.europeana.eu/schemas/edm/"
ORE = "http://www.openarchives.org/ore/terms/"

PROVIDED_CHO = EDM + "ProvidedCHO"
WEB_RESOURCE = EDM + "WebResource"
PLACE = EDM + "Place"
AGENT = EDM + "Agent"
AGGREGATION = ORE + "Aggregation"

TYPE = EDM + "type"
RIGHTS = EDM + "rights"
AGGREGATED_CHO = EDM + "aggregatedCHO"
IS_SHOWN_AT = EDM + "isShownAt"
IS_SHOWN_BY = EDM + "isShownBy"
HAS_VIEW = EDM + "hasView"
OBJECT = EDM + "object"
PROVIDER = EDM + "provider"
DATA_PROVIDER = EDM + "dataProvider"
