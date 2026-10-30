"""RDFLib and direct dictionary-based JSON-LD metadata models."""
from .json_model import JsonLDIMO

__all__ = ["IMO", "JsonLDIMO"]


def __getattr__(name):
    # Importing the JSON model must not load the RDF implementation.
    if name == "IMO":
        from .rdf_model import IMO
        return IMO
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
