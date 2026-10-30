.DEFAULT_GOAL := help

PYTHON ?= python
OUTPUT_DIR ?= examples/output/official-jsonld
INPUT ?=
FROM ?= datacite
TO ?= jsonld
OUTPUT ?=
SOURCE_URI ?=
RESOURCE_ROOT ?=
EXAMPLE ?= datacite-award

# Pass paths through the environment rather than interpolating them into shell
# source. Recipes can safely quote values containing spaces or shell symbols.
export PYTHON OUTPUT_DIR INPUT FROM TO OUTPUT SOURCE_URI RESOURCE_ROOT EXAMPLE

.PHONY: help install demo examples hierarchy rdf-demo test example-datacite example-edm convert list-examples load-example roundtrip-example

help:
	@printf '%s\n' \
	  'make install           Instalacja projektu i zależności testowych' \
	  'make demo              Wszystkie oficjalne wejścia, bez porównania RDFLib' \
	  'make examples          Oficjalne wejścia wraz z porównaniem RDFLib' \
	  'make hierarchy         JSON-LD: dataset -> katalog -> plik (stdout)' \
	  'make rdf-demo          Oryginalna demonstracja RDFLib' \
	  'make test              Testy pytest' \
	  'make example-datacite  Oficjalny dataset -> quickstart/datacite.imo.jsonld' \
	  'make example-edm       Oficjalny EDM -> quickstart/edm.imo.jsonld' \
	  'make list-examples     Lista identyfikatorów oficjalnych przykładów' \
	  'make load-example EXAMPLE=datacite-award       Wczytanie wybranego wejścia do IMO' \
	  'make roundtrip-example EXAMPLE=datacite-award  Wczytanie, eksport powrotny i diff' \
	  'make convert INPUT=plik.json FROM=datacite TO=jsonld OUTPUT=wynik.jsonld' \
	  '' \
	  'Domyślny interpreter: python (z aktualnego PATH).' \
	  'Zmiana interpretera: make examples PYTHON=.venv/bin/python' \
	  'Zmiana katalogu: make examples OUTPUT_DIR=/tmp/imo-results' \
	  'EDM wymaga SOURCE_URI=https://museum.example/original.xml.'

install:
	@"$$PYTHON" -m pip install -e '.[test]'

demo:
	@"$$PYTHON" demo_json.py --output-dir "$$OUTPUT_DIR"

examples:
	@"$$PYTHON" demo_json.py --compare-rdf --output-dir "$$OUTPUT_DIR"

hierarchy:
	@"$$PYTHON" demo_json.py --example

rdf-demo:
	@"$$PYTHON" demo.py

test:
	@"$$PYTHON" -m pytest -q

list-examples:
	@"$$PYTHON" demo_json.py --list-examples

load-example:
	@"$$PYTHON" demo_json.py --case "$$EXAMPLE" --load-only --output-dir "$$OUTPUT_DIR"

roundtrip-example:
	@"$$PYTHON" demo_json.py --case "$$EXAMPLE" --show-diff --output-dir "$$OUTPUT_DIR"

example-datacite:
	@mkdir -p "$$OUTPUT_DIR/quickstart"
	@"$$PYTHON" -m imo.json_adapters examples/input/official/datacite-dataset.json \
	  --from datacite -o "$$OUTPUT_DIR/quickstart/datacite.imo.jsonld"

example-edm:
	@mkdir -p "$$OUTPUT_DIR/quickstart"
	@"$$PYTHON" -m imo.json_adapters examples/input/official/edm.xml \
	  --from edm \
	  --source-uri https://raw.githubusercontent.com/europeana/contrib/master/ntua/mint2/src/main/webapp/schemas/edm/EDM.xml \
	  -o "$$OUTPUT_DIR/quickstart/edm.imo.jsonld"

convert:
	@if [ -z "$$INPUT" ]; then \
	  printf '%s\n' 'Podaj INPUT, np. make convert INPUT=plik.json FROM=datacite TO=jsonld OUTPUT=wynik.jsonld' >&2; \
	  exit 2; \
	fi; \
	set -- "$$INPUT" --from "$$FROM" --to "$$TO"; \
	if [ -n "$$OUTPUT" ]; then set -- "$$@" -o "$$OUTPUT"; fi; \
	if [ -n "$$SOURCE_URI" ]; then set -- "$$@" --source-uri "$$SOURCE_URI"; fi; \
	if [ -n "$$RESOURCE_ROOT" ]; then set -- "$$@" --root "$$RESOURCE_ROOT"; fi; \
	"$$PYTHON" -m imo.json_adapters "$$@"
