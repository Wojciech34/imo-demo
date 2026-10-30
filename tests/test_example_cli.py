import json

import pytest

from demo_json import run_example


def test_single_datacite_roundtrip_shows_metadata_diff_without_api_payload(tmp_path, capsys):
    report = run_example("datacite-award", tmp_path, show_diff=True)
    output = tmp_path / "selected/datacite-award"
    assert report["mode"] == "roundtrip"
    assert not report["equal"]
    assert not report["sourceBackupUsedForExport"]
    assert report["warnings"][0]["path"] == "/creators/0/nameIdentifiers/0"
    original = json.loads((output / "source-metadata.json").read_text())
    assert "fundingReferences" in original
    assert "xml" not in original and "viewCount" not in original
    assert (output / "roundtrip.datacite.json").is_file()
    difference = (output / "diff.txt").read_text()
    assert "--- source-metadata.json" in difference
    assert '"fundingReferences"' in difference
    assert difference in capsys.readouterr().out


@pytest.mark.parametrize("example_id, expected_equal", [("edm", True), ("edm-3d-complete", False)])
def test_single_edm_roundtrip_compares_assertions_instead_of_xml_layout(tmp_path, example_id, expected_equal):
    report = run_example(example_id, tmp_path, show_diff=True)
    output = tmp_path / "selected" / example_id
    assert report["equal"] is expected_equal
    assert (output / "roundtrip.edm.xml").is_file()
    if expected_equal:
        assert report["preservedTriples"] == 29
        assert report["lostTriples"] == report["addedTriples"] == 0
        assert "Brak różnic" in (output / "diff.txt").read_text()
    else:
        assert report["lostTriples"] > 0
        assert "--- source RDF" in (output / "diff.txt").read_text()


def test_load_only_has_model_and_report_without_stale_roundtrip_results(tmp_path):
    run_example("datacite-award", tmp_path)
    report = run_example("datacite-award", tmp_path, load_only=True)
    output = tmp_path / "selected/datacite-award"
    assert report["mode"] == "load"
    assert "equal" not in report
    assert {p.name for p in output.iterdir()} == {"imo.jsonld", "README.md", "report.json"}


def test_unknown_example_is_rejected_before_creating_output(tmp_path):
    with pytest.raises(ValueError, match="Unknown example"):
        run_example("missing", tmp_path)
    assert not list(tmp_path.iterdir())
