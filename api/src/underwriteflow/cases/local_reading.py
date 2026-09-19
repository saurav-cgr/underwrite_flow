"""Local document reading for one submission: page text and typed failures.

Reading happens in-process before any provider sees anything, so these helpers
own the upload-volume paths, the local extractor, and the bound on
administrator reference text. They never call a provider and never persist.
"""

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from underwriteflow.persistence.models import (
    Case,
    Document,
    ProductVersion,
    ReferenceDocument,
)
from underwriteflow.providers.extraction import (
    ExtractionError,
    LocalDocumentExtractor,
)
from underwriteflow.providers.service import document_content

MAX_REFERENCE_CHARS = 50_000


# Read local text for every document, recording typed extraction failures.
def extract_documents(
    upload_root: Path, documents: list[Document]
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    extractor = LocalDocumentExtractor()
    inputs: list[dict[str, object]] = []
    failures: list[dict[str, object]] = []
    for document in documents:
        try:
            local = extractor.extract(
                upload_root / document.storage_key,
                document.content_type,
            )
        except ExtractionError:
            failures.append(
                {
                    "document_id": str(document.id),
                    "filename": document.filename,
                    "error_code": "extraction_failed",
                }
            )
            continue
        inputs.append(
            {
                "document_id": str(document.id),
                "document_code": document.document_code or "",
                "filename": document.filename,
                # Page locators stay in the content so a provider line number
                # can be mapped back to trusted page evidence.
                "content": document_content(local.pages),
                "pages": [
                    page.model_dump(mode="json") for page in local.pages
                ],
            }
        )
    return inputs, failures


# Read the pinned version's administrator references as background text.
async def load_reference_content(
    session: AsyncSession, upload_root: Path, case: Case
) -> str:
    product_version = await session.scalar(
        select(ProductVersion).where(
            ProductVersion.id == case.product_version_id
        )
    )
    if product_version is None:
        return ""
    documents = list(
        await session.scalars(
            select(ReferenceDocument).where(
                ReferenceDocument.product_id
                == product_version.product_id,
                ReferenceDocument.version == product_version.version,
            )
        )
    )
    extractor = LocalDocumentExtractor()
    texts: list[str] = []
    for document in documents:
        if not document.storage_key or not document.content_type:
            continue
        try:
            local = extractor.extract(
                upload_root / document.storage_key,
                document.content_type,
            )
        except ExtractionError:
            continue
        texts.append(
            document.filename
            + ":\n"
            + "\n".join(page.text for page in local.pages)
        )
    # Reference text is background only and stays inside the provider bound.
    return "\n\n".join(texts)[:MAX_REFERENCE_CHARS]
