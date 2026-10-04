"""Manifest, checksum, and clause-splitting checks for regulation."""

import hashlib
from pathlib import Path

import pytest
import yaml

from fixtures.synthetic_pdf import blank_pdf, text_pdf
from underwriteflow.knowledge.regulation import (
    REGULATION_LABEL,
    load_manifest_folder,
    read_manifest,
    split_clauses,
)


# Write one synthetic PDF document and return its bytes.
def write_pdf(directory: Path, name: str, lines: list[str]) -> bytes:
    content = text_pdf(lines)
    (directory / name).write_bytes(content)
    return content


# Write a manifest listing the supplied documents beside them.
def write_manifest(directory: Path, documents: list[dict]) -> Path:
    path = directory / "manifest.yaml"
    path.write_text(yaml.safe_dump({"documents": documents}))
    return path


# Build one manifest entry for a document written to the same folder.
def entry_for(directory: Path, name: str, **overrides) -> dict:
    content = (directory / name).read_bytes()
    entry = {
        "id": Path(name).stem,
        "file": name,
        "title": f"Synthetic regulation {name}",
        "issuer": "IRDAI",
        "date": "2024-05-29",
        "product_lines": ["motor"],
        "sha256": hashlib.sha256(content).hexdigest(),
    }
    entry.update(overrides)
    return entry


# Read the two-clause synthetic circular used by most cases here.
CLAUSE_PAGES = [
    "Cover page text that is not a clause.",
    "1. Scope\nThis clause applies to motor cover.\n"
    "It explains sum insured duties.",
    "2. Claim settlement\nInsurers settle claims within thirty days.\n"
    "2. Claim settlement\nRepeated page heading is body text.",
]


# Verify a manifest file name cannot escape the regulatory folder.
def test_read_manifest_rejects_a_path(tmp_path: Path) -> None:
    write_pdf(tmp_path, "circular.pdf", CLAUSE_PAGES)
    entry = entry_for(tmp_path, "circular.pdf", file="../escape.pdf")
    manifest = write_manifest(tmp_path, [entry])

    with pytest.raises(ValueError):
        read_manifest(manifest)


# Verify an unquoted YAML date is accepted like the shipped manifest.
def test_read_manifest_accepts_yaml_dates(tmp_path: Path) -> None:
    write_pdf(tmp_path, "circular.pdf", CLAUSE_PAGES)
    entry = entry_for(tmp_path, "circular.pdf")
    entry.pop("date")
    body = [
        "documents:",
        "  - id: circular",
        "    file: circular.pdf",
        "    title: Synthetic circular",
        "    issuer: IRDAI",
        "    date: 2024-05-29",
        f"    sha256: {entry['sha256']}",
        "    product_lines: [motor]",
    ]
    path = tmp_path / "manifest.yaml"
    path.write_text("\n".join(body) + "\n")

    entries = read_manifest(path)

    assert entries[0].id == "circular"
    assert str(entries[0].date) == "2024-05-29"


# Verify a manifest is read into typed entries with its declared fields.
def test_read_manifest_returns_typed_entries(tmp_path: Path) -> None:
    write_pdf(tmp_path, "circular.pdf", CLAUSE_PAGES)
    manifest = write_manifest(
        tmp_path, [entry_for(tmp_path, "circular.pdf")]
    )

    entries = read_manifest(manifest)

    assert [entry.id for entry in entries] == ["circular"]
    assert entries[0].file == "circular.pdf"
    assert entries[0].product_lines == ["motor"]
    assert entries[0].sha256


# Verify an unreadable manifest is rejected instead of silently empty.
def test_read_manifest_rejects_invalid_shape(tmp_path: Path) -> None:
    path = tmp_path / "manifest.yaml"
    path.write_text("documents: not-a-list\n")

    with pytest.raises(ValueError):
        read_manifest(path)


# Verify clauses split at numbered headings and keep page locators.
def test_split_clauses_at_numbered_headings(tmp_path: Path) -> None:
    write_pdf(tmp_path, "circular.pdf", CLAUSE_PAGES)
    manifest = write_manifest(
        tmp_path, [entry_for(tmp_path, "circular.pdf")]
    )

    result = load_manifest_folder(tmp_path, read_manifest(manifest)[0:1])

    keys = [clause.passage_key for clause in result.clauses]
    assert keys == ["circular#1", "circular#2"]
    first = result.clauses[0]
    assert first.title == "1. Scope"
    # The synthetic fixture is one page, so both clauses locate there.
    assert first.source_locator == "circular#page:1"
    assert "motor cover" in first.body
    assert "sum insured duties" in first.body
    assert result.clauses[1].source_locator == "circular#page:1"


# Verify a clause continues across page breaks and keeps its first page.
def test_clause_spans_pages_and_keeps_first_locator() -> None:
    clauses = split_clauses(
        "act",
        [
            "Preface text without a heading.",
            "12. Duties of insurers\nInsurers must keep records.",
            "Continuing body text on the next page.",
            "13. Penalties\nFines apply.",
        ],
        ["life"],
    )

    assert [clause.passage_key for clause in clauses] == [
        "act#12",
        "act#13",
    ]
    assert clauses[0].source_locator == "act#page:2"
    assert "next page" in clauses[0].body
    assert clauses[0].product_lines == ["life"]
    assert clauses[1].source_locator == "act#page:4"


# Verify a repeated heading number never creates a duplicate passage key.
def test_repeated_heading_number_stays_one_clause(tmp_path: Path) -> None:
    write_pdf(tmp_path, "circular.pdf", CLAUSE_PAGES)
    manifest = write_manifest(
        tmp_path, [entry_for(tmp_path, "circular.pdf")]
    )

    result = load_manifest_folder(tmp_path, read_manifest(manifest)[0:1])

    assert len(result.clauses) == len(
        {clause.passage_key for clause in result.clauses}
    )
    assert "Repeated page heading" in result.clauses[1].body


# Verify every loaded clause carries the informational badge verbatim.
def test_every_clause_is_labelled(tmp_path: Path) -> None:
    write_pdf(tmp_path, "circular.pdf", CLAUSE_PAGES)
    manifest = write_manifest(
        tmp_path, [entry_for(tmp_path, "circular.pdf")]
    )

    result = load_manifest_folder(tmp_path, read_manifest(manifest)[0:1])

    assert result.clauses
    assert {clause.label for clause in result.clauses} == {
        REGULATION_LABEL
    }


# Verify clauses carry the manifest product lines and deterministic tags.
def test_clauses_carry_product_lines_and_suggested_tags(
    tmp_path: Path,
) -> None:
    write_pdf(tmp_path, "circular.pdf", CLAUSE_PAGES)
    manifest = write_manifest(
        tmp_path,
        [entry_for(tmp_path, "circular.pdf", product_lines=["motor"])],
    )

    result = load_manifest_folder(tmp_path, read_manifest(manifest)[0:1])

    assert [clause.product_lines for clause in result.clauses] == [
        ["motor"],
        ["motor"],
    ]
    assert "cover-amount" in result.clauses[0].suggested_tags
    assert "claim-settlement" in result.clauses[1].suggested_tags


# Verify an altered file is rejected and never contributes clauses.
def test_altered_file_is_rejected(tmp_path: Path) -> None:
    write_pdf(tmp_path, "circular.pdf", CLAUSE_PAGES)
    entry = entry_for(tmp_path, "circular.pdf", sha256="0" * 64)
    write_manifest(tmp_path, [entry])

    result = load_manifest_folder(tmp_path, read_manifest(
        tmp_path / "manifest.yaml"
    ))

    assert result.clauses == []
    report = result.files[0]
    assert (report.status, report.reason) == (
        "rejected",
        "checksum_mismatch",
    )


# Verify a file that is absent locally is reported, not fatal.
def test_missing_file_is_reported(tmp_path: Path) -> None:
    write_pdf(tmp_path, "circular.pdf", CLAUSE_PAGES)
    manifest = write_manifest(
        tmp_path,
        [
            entry_for(tmp_path, "circular.pdf"),
            {
                "id": "absent",
                "file": "absent.pdf",
                "title": "Absent circular",
                "issuer": "IRDAI",
                "date": "2024-05-29",
                "product_lines": ["life"],
                "sha256": "1" * 64,
            },
        ],
    )

    result = load_manifest_folder(tmp_path, read_manifest(manifest))

    absent = [item for item in result.files if item.file == "absent.pdf"]
    assert (absent[0].status, absent[0].reason) == (
        "reported",
        "missing_file",
    )
    assert result.clauses


# Verify the `.doc` Insurance Act is reported rather than parsed.
def test_unsupported_document_is_reported(tmp_path: Path) -> None:
    (tmp_path / "insurance_act_1938.doc").write_bytes(b"synthetic")
    manifest = write_manifest(
        tmp_path,
        [
            {
                "id": "insurance_act_1938",
                "file": "insurance_act_1938.doc",
                "title": "The Insurance Act, 1938",
                "issuer": "IRDAI",
                "date": "2023-07-04",
                "product_lines": ["motor"],
                "sha256": hashlib.sha256(b"synthetic").hexdigest(),
            }
        ],
    )

    result = load_manifest_folder(tmp_path, read_manifest(manifest))

    assert result.clauses == []
    assert (result.files[0].status, result.files[0].reason) == (
        "reported",
        "unsupported_format",
    )


# Verify a file present locally but absent from the manifest is ignored.
def test_unlisted_file_is_ignored(tmp_path: Path) -> None:
    write_pdf(tmp_path, "circular.pdf", CLAUSE_PAGES)
    write_pdf(tmp_path, "extra.pdf", ["9. Not listed\nIgnored body."])
    manifest = write_manifest(
        tmp_path, [entry_for(tmp_path, "circular.pdf")]
    )

    result = load_manifest_folder(tmp_path, read_manifest(manifest))

    listed = {item.file for item in result.files}
    assert "extra.pdf" not in listed
    assert all(not key.startswith("extra#") for key in (
        clause.passage_key for clause in result.clauses
    ))


# Verify an image-only PDF is reported instead of failing the import.
def test_scanned_document_without_text_is_reported(
    tmp_path: Path,
) -> None:
    (tmp_path / "scanned.pdf").write_bytes(blank_pdf())
    manifest = write_manifest(
        tmp_path, [entry_for(tmp_path, "scanned.pdf")]
    )

    result = load_manifest_folder(tmp_path, read_manifest(manifest))

    assert result.clauses == []
    assert (result.files[0].status, result.files[0].reason) == (
        "reported",
        "no_text",
    )


# Verify the derived version name follows the manifest content.
def test_version_name_follows_manifest_content(tmp_path: Path) -> None:
    write_pdf(tmp_path, "circular.pdf", CLAUSE_PAGES)
    manifest = write_manifest(
        tmp_path, [entry_for(tmp_path, "circular.pdf")]
    )

    first = load_manifest_folder(tmp_path, read_manifest(manifest))
    second = load_manifest_folder(tmp_path, read_manifest(manifest))

    assert first.version == second.version
    assert first.version.startswith("r-")


# Verify a heading-free document yields no clause rather than a preamble.
def test_document_without_headings_yields_no_clauses(
    tmp_path: Path,
) -> None:
    clauses = split_clauses("circular", ["Plain text without headings."])

    assert clauses == []
