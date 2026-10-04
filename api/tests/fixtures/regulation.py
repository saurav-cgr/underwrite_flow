"""Shared helpers for building disposable regulation folders in tests."""

import hashlib
from pathlib import Path

import yaml

from fixtures.synthetic_pdf import text_pdf

# Two numbered clauses plus preamble text that is not a clause.
CLAUSE_LINES = [
    "Cover page text that is not a clause.",
    "1. Scope\nThis clause covers motor sum insured duties.",
    "2. Claim settlement\nInsurers settle claims within thirty days.",
]


# Write one synthetic PDF document into the regulation folder.
def write_document(root: Path, name: str, lines: list[str]) -> bytes:
    content = text_pdf(lines)
    (root / name).write_bytes(content)
    return content


# Build one manifest entry with the real checksum of a local file.
def listed_entry(root: Path, name: str, **overrides) -> dict:
    entry = {
        "id": Path(name).stem,
        "file": name,
        "title": f"Synthetic regulation {name}",
        "issuer": "IRDAI",
        "date": "2024-05-29",
        "product_lines": ["motor"],
        "sha256": hashlib.sha256((root / name).read_bytes()).hexdigest(),
    }
    entry.update(overrides)
    return entry


# Write the manifest listing the supplied documents.
def write_manifest(root: Path, documents: list[dict]) -> None:
    (root / "manifest.yaml").write_text(
        yaml.safe_dump({"documents": documents})
    )


# Build one listed manifest entry for bytes that are not on disk yet.
def entry_for_bytes(name: str, content: bytes, **overrides) -> dict:
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
