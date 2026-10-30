"""Public adapter imports and command-line entry point for direct JSON-LD.

Format implementations live in imo.adapters; conversion rules live in
imo.mappings and term definitions in imo.vocabularies.
"""
from lxml import etree

from .adapters.datacite import parse_datacite, export_datacite, missing_datacite_fields
from .adapters.edm import parse_edm, export_edm
from .json_model import JsonLDIMO, _absolute_id

__all__ = ["parse_datacite", "export_datacite", "missing_datacite_fields",
           "parse_edm", "export_edm", "main"]


def main(argv=None):
    """Convert one local file; the default output format is JSON-LD."""
    import argparse
    import json
    from pathlib import Path
    import sys

    parser = argparse.ArgumentParser(description="Convert DataCite, EDM or direct-profile JSON-LD without RDFLib")
    parser.add_argument("input", type=Path, help="Input file")
    parser.add_argument("--from", dest="input_format", required=True, choices=("datacite", "edm", "jsonld"))
    parser.add_argument("--to", dest="output_format", default="jsonld", choices=("jsonld", "datacite", "edm"))
    parser.add_argument("-o", "--output", type=Path, help="Output file; omit to print to stdout")
    parser.add_argument("--source-uri", help="Original document URL, required for EDM to resolve relative IDs; no download occurs")
    parser.add_argument("--root", help="Select a ProvidedCHO by absolute ID when reading EDM")
    args = parser.parse_args(argv)
    if args.input_format == "edm" and (not args.source_uri or not _absolute_id(args.source_uri) or not args.source_uri.startswith(("https://", "http://"))):
        parser.error("EDM requires --source-uri with the original HTTP(S) document URL")
    if args.root and args.input_format != "edm":
        parser.error("--root is only supported with --from edm")
    if args.output and args.output.resolve() == args.input.resolve():
        parser.error("Input and output must be different files")
    try:
        if args.input_format == "edm":
            model = parse_edm(args.input.read_bytes(), args.source_uri, args.root)
        elif args.input_format == "datacite":
            model = parse_datacite(json.loads(args.input.read_text(encoding="utf-8")), args.source_uri or args.input.resolve().as_uri())
        else:
            model = JsonLDIMO.from_json(args.input.read_text(encoding="utf-8"))
        if args.output_format == "jsonld":
            result = model.to_json()
        elif args.output_format == "edm":
            result = export_edm(model)
        else:
            projection = export_datacite(model)
            result = json.dumps(projection, ensure_ascii=False, indent=2)
            missing = missing_datacite_fields(projection)
            if missing:
                print("DataCite draft; missing fields: " + ", ".join(missing), file=sys.stderr)
        if args.output:
            args.output.write_text(result.rstrip("\n") + "\n", encoding="utf-8")
        else:
            print(result)
    except (OSError, ValueError, etree.XMLSyntaxError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
