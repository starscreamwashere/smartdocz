"""Document loaders — multi-format (Milestone 4).

Supported sources (TRD §7): PDF, DOCX, TXT, CSV, JSON, and YouTube transcripts.
Auto file-type detection routes each upload to the right loader; everything
returns page-aware LangChain Documents that flow through the same chunk → embed
→ store pipeline.
"""
from __future__ import annotations

import json
import re

from langchain_community.document_loaders import (
    CSVLoader,
    Docx2txtLoader,
    PyPDFLoader,
    TextLoader,
)
from langchain_core.documents import Document


class UnsupportedFileTypeError(ValueError):
    """Raised when a file type has no loader."""


class DocumentParseError(RuntimeError):
    """Raised when a source cannot be parsed (corrupted file, no transcript…)."""


# Extension → internal file_type (matches uploaded_files.file_type values).
EXT_TO_TYPE = {
    ".pdf": "pdf",
    ".docx": "docx",
    ".txt": "txt",
    ".csv": "csv",
    ".json": "json",
}
# File-based types (YouTube comes from a URL, handled separately).
SUPPORTED_FILE_TYPES = set(EXT_TO_TYPE.values())


def detect_file_type(filename: str) -> str | None:
    """Return the internal file_type for a filename, or None if unsupported."""
    for ext, ftype in EXT_TO_TYPE.items():
        if filename.lower().endswith(ext):
            return ftype
    return None


def _load_json(path: str) -> list[Document]:
    """Lightweight JSON loader: pretty-print the parsed document as text.

    Avoids LangChain's JSONLoader jq dependency while keeping the data readable
    and chunkable.
    """
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (json.JSONDecodeError, OSError) as exc:
        raise DocumentParseError(f"Malformed JSON: {exc}") from exc
    text = json.dumps(data, indent=2, ensure_ascii=False)
    return [Document(page_content=text, metadata={"page_number": 0})]


def load_document(path: str, file_type: str) -> list[Document]:
    """Load a file into Documents. Each carries a (1-based) ``page_number``;
    non-paginated formats use 0."""
    if file_type not in SUPPORTED_FILE_TYPES:
        raise UnsupportedFileTypeError(
            f"'{file_type}' is not supported. Supported: {sorted(SUPPORTED_FILE_TYPES)}"
        )

    try:
        if file_type == "pdf":
            pages = PyPDFLoader(path).load()
            docs = []
            for i, page in enumerate(pages):
                text = (page.page_content or "").strip()
                if text:
                    page_number = int(page.metadata.get("page", i)) + 1
                    docs.append(Document(page_content=text, metadata={"page_number": page_number}))
        elif file_type == "json":
            docs = _load_json(path)
        else:
            loader = {"docx": Docx2txtLoader, "txt": TextLoader, "csv": CSVLoader}[file_type]
            raw = loader(path).load()
            docs = [
                Document(page_content=d.page_content.strip(), metadata={"page_number": 0})
                for d in raw
                if (d.page_content or "").strip()
            ]
    except DocumentParseError:
        raise
    except Exception as exc:  # loader-specific parse failures
        raise DocumentParseError(str(exc)) from exc

    if not docs:
        raise DocumentParseError("No extractable text found in the document.")
    return docs


# ---- YouTube transcripts ----

_YT_PATTERNS = [
    r"(?:v=|/shorts/|youtu\.be/|/embed/)([0-9A-Za-z_-]{11})",
    r"^([0-9A-Za-z_-]{11})$",  # bare video id
]


def extract_video_id(url: str) -> str | None:
    for pattern in _YT_PATTERNS:
        m = re.search(pattern, url.strip())
        if m:
            return m.group(1)
    return None


def load_youtube(url: str) -> tuple[str, list[Document]]:
    """Fetch a YouTube transcript. Returns (display_title, documents)."""
    video_id = extract_video_id(url)
    if not video_id:
        raise DocumentParseError("Could not parse a YouTube video ID from the URL.")

    from youtube_transcript_api import YouTubeTranscriptApi

    try:
        fetched = YouTubeTranscriptApi().fetch(video_id)
        text = " ".join(snippet.text for snippet in fetched).strip()
    except Exception as exc:  # NoTranscriptFound, TranscriptsDisabled, network…
        raise DocumentParseError(
            f"Could not fetch a transcript for this video: {exc}"
        ) from exc

    if not text:
        raise DocumentParseError("The transcript for this video is empty.")
    title = f"YouTube · {video_id}"
    return title, [Document(page_content=text, metadata={"page_number": 0})]
