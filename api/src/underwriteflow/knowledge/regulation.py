"""Checksum-verified loading of public regulatory documents.

Only documents listed in ``data/regulatory/manifest.yaml`` whose SHA-256
matches are read. Every clause is badged with the informational label and
never participates in route calculation.
"""

import hashlib
import re
from dataclasses import dataclass
from datetime import date as DateType
from pathlib import Path

import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
)

from underwriteflow.providers.extraction import (
    ExtractionError,
    LocalDocumentExtractor,
)

REGULATION_LABEL = "PUBLIC REGULATION - INFORMATIONAL"
REGULATION_TOPIC = "regulation"
MANIFEST_NAME = "manifest.yaml"
CLAUSE_HEADING = re.compile(r"^\s*(\d+(?:\.\d+)*)\.\s+\S")
MAX_TITLE_CHARS = 300
MAX_CLAUSE_CHARS = 6000
PDF_SUFFIX = ".pdf"

# Deterministic tag suggestions; only administrator-accepted tags ever match.
SUGGESTED_TAG_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("claim-settlement", ("claim", "settle")),
    ("cover-amount", ("cover", "sum insured", "sum assured")),
    ("disclosure", ("disclosure", "prospectus")),
    ("grievance", ("grievance", "ombudsman")),
    ("policyholder-protection", ("policyholder", "insured")),
    ("renewal", ("renew",)),
)

# The closed vocabulary an administrator may accept for a clause.
ACCEPTED_TAGS = frozenset(tag for tag, _ in SUGGESTED_TAG_KEYWORDS)


class ManifestError(ValueError):
    """Raised when the regulatory manifest cannot be read."""


class ManifestEntry(BaseModel):
    """One approved regulatory document with its verified checksum."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(min_length=1, max_length=200)
    file: str = Field(min_length=1, max_length=300)
    title: str = Field(min_length=1, max_length=300)
    issuer: str = Field(min_length=1, max_length=200)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    product_lines: list[str] = Field(default_factory=list, max_length=10)
    # YAML reads an unquoted date as a date, so accept both shapes.
    date: DateType | None = None
    reference: str | None = Field(default=None, max_length=200)
    note: str | None = Field(default=None, max_length=500)
    sections_of_interest: str | None = Field(default=None, max_length=200)
    source: str | None = Field(default=None, max_length=500)

    # Keep every manifest file name inside the regulatory folder.
    @field_validator("file")
    @classmethod
    def validate_file_name(cls, value: str) -> str:
        if Path(value).name != value or value in {".", ".."}:
            raise ValueError("manifest_file_path")
        return value


class RegulationClause(BaseModel):
    """One citable public clause with its manifest document and page."""

    passage_key: str = Field(min_length=1, max_length=200)
    title: str = Field(min_length=1, max_length=MAX_TITLE_CHARS)
    body: str = Field(min_length=1)
    source_locator: str = Field(min_length=1, max_length=500)
    product_lines: list[str] = Field(default_factory=list, max_length=10)
    suggested_tags: list[str] = Field(default_factory=list, max_length=20)
    label: str = REGULATION_LABEL


@dataclass(frozen=True)
class FileReport:
    """One manifest document and the outcome of trying to load it."""

    file: str
    status: str
    reason: str | None
    clause_count: int


@dataclass(frozen=True)
class FolderLoad:
    """One derived regulation version built from the manifest folder."""

    version: str
    content_hash: str
    clauses: list[RegulationClause]
    files: list[FileReport]


# Hash one file's bytes for the manifest allowlist check.
def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


# Hash one uploaded byte string for the manifest allowlist check.
def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


# Read and validate every approved document in the manifest.
def read_manifest(path: Path) -> list[ManifestEntry]:
    try:
        raw = yaml.safe_load(path.read_text())
    except (OSError, yaml.YAMLError) as error:
        raise ManifestError("manifest_unreadable") from error
    if not isinstance(raw, dict):
        raise ManifestError("manifest_invalid")
    documents = raw.get("documents")
    if not isinstance(documents, list) or not documents:
        raise ManifestError("manifest_invalid")
    entries: list[ManifestEntry] = []
    for document in documents:
        if not isinstance(document, dict):
            raise ManifestError("manifest_invalid")
        try:
            entries.append(ManifestEntry.model_validate(document))
        except ValidationError as error:
            raise ManifestError("manifest_invalid") from error
    return entries


# Pick the administrator-visible tags a clause text suggests.
def suggest_tags(text: str) -> list[str]:
    folded = text.casefold()
    return [
        tag
        for tag, keywords in SUGGESTED_TAG_KEYWORDS
        if any(keyword in folded for keyword in keywords)
    ]


# Collapse whitespace so a clause body is stable across page breaks.
def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


# Split page texts into clauses keyed by document and heading number.
def split_clauses(
    document_id: str,
    pages: list[str],
    product_lines: list[str] | None = None,
) -> list[RegulationClause]:
    lines: list[tuple[int, str]] = []
    for index, page in enumerate(pages, 1):
        for line in page.splitlines():
            lines.append((index, line))
    clauses: list[RegulationClause] = []
    used: set[str] = set()
    current: dict | None = None
    for page_number, line in lines:
        heading = CLAUSE_HEADING.match(line)
        if heading is not None:
            key = f"{document_id}#{heading.group(1)}"
            if key not in used:
                used.add(key)
                if current is not None:
                    clauses.append(_clause_from(current))
                current = {
                    "key": key,
                    "page": page_number,
                    "heading": line.strip(),
                    "buffer": [line.strip()],
                }
                continue
        if current is not None:
            current["buffer"].append(line)
    if current is not None:
        clauses.append(_clause_from(current))
    return [
        clause.model_copy(
            update={"product_lines": list(product_lines or [])}
        )
        for clause in clauses
    ]


# Build one stored clause from its collected heading and body lines.
def _clause_from(current: dict) -> RegulationClause:
    title = current["heading"][:MAX_TITLE_CHARS]
    body = _normalize(" ".join(current["buffer"]))
    if len(body) > MAX_CLAUSE_CHARS:
        body = body[: MAX_CLAUSE_CHARS - 1] + "…"
    return RegulationClause(
        passage_key=current["key"],
        title=title,
        body=body,
        source_locator=(
            f'{current["key"].split("#")[0]}#page:{current["page"]}'
        ),
        suggested_tags=suggest_tags(body),
    )


# Read every page, OCR-ing only pages that carry no text layer.
def document_pages(
    extractor: LocalDocumentExtractor,
    path: Path,
) -> list[str]:
    document = extractor.extract(path, "application/pdf")
    pages: list[str] = []
    for page in document.pages:
        text = page.text
        if not text.strip():
            try:
                text = extractor.ocr_page(path, page.page_number)
            except ExtractionError:
                text = ""
        pages.append(text)
    return pages


# Derive one stable regulation version name from the manifest and clauses.
def regulation_version(
    entries: list[ManifestEntry],
    clauses: list[RegulationClause],
) -> tuple[str, str]:
    parts = [
        f"{name}:{checksum}"
        for name, checksum in sorted(
            (entry.id, entry.sha256) for entry in entries
        )
    ]
    # Clauses decide the version too, so an upload or edit renames it.
    parts.extend(
        f"clause:{clause.passage_key}:{','.join(clause.product_lines)}:"
        f"{clause.title}:{clause.body}"
        for clause in sorted(clauses, key=lambda item: item.passage_key)
    )
    digest = hashlib.sha256("\n".join(parts).encode()).hexdigest()
    return f"r-{digest[:12]}", digest


# Load every manifest document that is present locally into clauses.
def load_manifest_folder(
    root: Path,
    entries: list[ManifestEntry],
    extractor: LocalDocumentExtractor | None = None,
) -> FolderLoad:
    reader = extractor or LocalDocumentExtractor()
    clauses: list[RegulationClause] = []
    reports: list[FileReport] = []
    for entry in entries:
        path = root / entry.file
        if not path.is_file():
            reports.append(
                FileReport(entry.file, "reported", "missing_file", 0)
            )
            continue
        if path.suffix.casefold() != PDF_SUFFIX:
            reports.append(
                FileReport(entry.file, "reported", "unsupported_format", 0)
            )
            continue
        try:
            checksum = sha256_file(path)
        except OSError:
            reports.append(
                FileReport(entry.file, "reported", "unreadable", 0)
            )
            continue
        if checksum != entry.sha256:
            reports.append(
                FileReport(entry.file, "rejected", "checksum_mismatch", 0)
            )
            continue
        try:
            pages = document_pages(reader, path)
        except ExtractionError:
            reports.append(
                FileReport(entry.file, "reported", "unreadable", 0)
            )
            continue
        found = split_clauses(entry.id, pages, entry.product_lines)
        if not found:
            reports.append(
                FileReport(entry.file, "reported", "no_text", 0)
            )
            continue
        clauses.extend(found)
        reports.append(
            FileReport(entry.file, "loaded", None, len(found))
        )
    version, digest = regulation_version(entries, clauses)
    return FolderLoad(
        version=version,
        content_hash=digest,
        clauses=clauses,
        files=reports,
    )
