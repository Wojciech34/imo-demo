"""Small operations on the common dictionary-based JSON-LD model."""


def _root(imo):
    imo.validate()
    return next(node for node in imo.resources if node["@id"] == imo.root)


def _text(text, language=None):
    result = {"@value": text}
    if language:
        result["@language"] = language
    return result


