"""Document loaders.

Milestone 2 supports PDF only (TRD §7 / Implementation Plan M2). Later
milestones add DOCX, TXT, CSV, JSON, and YouTube transcripts behind the same
`load_document` interface.

Uses LangChain's PyPDFLoader, which yields one Document per page so we can
carry `page_number` into chunk metadata for citations.
"""
from __future__ import annotations

from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document


class UnsupportedFileTypeError(ValueError):
    """Raised when a file type has no loader yet."""


class DocumentParseError(RuntimeError):
    """Raised when a file cannot be parsed (e.g. corrupted PDF)."""


# file_type -> loader. Extended in Milestone 4.
SUPPORTED_TYPES = {"pdf"}


def load_document(path: str, file_type: str) -> list[Document]:
    """Load a file into page-aware LangChain Documents.

    Each Document's metadata includes a 1-based ``page_number``.
    """
    if file_type not in SUPPORTED_TYPES:
        raise UnsupportedFileTypeError(
            f"'{file_type}' is not supported yet. Supported: {sorted(SUPPORTED_TYPES)}"
        )

    try:
        pages = PyPDFLoader(path).load()
    except Exception as exc:  # pypdf raises a variety of errors on bad files
        raise DocumentParseError(str(exc)) from exc

    docs: list[Document] = []
    for i, page in enumerate(pages):
        text = (page.page_content or "").strip()
        if not text:
            continue
        # PyPDFLoader sets metadata["page"] as 0-based; expose 1-based.
        page_number = int(page.metadata.get("page", i)) + 1
        docs.append(Document(page_content=text, metadata={"page_number": page_number}))

    if not docs:
        raise DocumentParseError("No extractable text found in the document.")
    return docs
