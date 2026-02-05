"""Core OCR processing and Markdown formatting logic."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import TYPE_CHECKING

from mistralai import Mistral
from mistralai.extra import response_format_from_pydantic_model
from mistralai.models.file import File

from mistral_ocr.models import DocumentAnnotation, ImageAnnotation

if TYPE_CHECKING:
    from collections.abc import Iterable

DEFAULT_MODEL = "mistral-ocr-latest"


def load_dotenv(env_path: Path = Path(".env")) -> dict[str, str]:
    """Load key-value pairs from a .env file into ``os.environ``."""
    loaded: dict[str, str] = {}
    if not env_path.exists():
        return loaded

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'\"")
        if key and value:
            os.environ.setdefault(key, value)
            loaded[key] = value
    return loaded


def ensure_api_key() -> str:
    """Return the Mistral API key from the environment, loading .env if needed."""
    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        load_dotenv()
        api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        raise RuntimeError("MISTRAL_API_KEY environment variable is not set.")
    return api_key


def resolve_output_path(pdf_path: Path, explicit_output: Path | None) -> Path:
    if explicit_output:
        return explicit_output
    return pdf_path.with_suffix(".md")


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------


def format_image_annotation(
    annotation_payload: str | None, page_index: int, image_index: int
) -> str | None:
    if not annotation_payload:
        return None
    try:
        parsed = json.loads(annotation_payload)
    except json.JSONDecodeError:
        return None

    lines: list[str] = []
    image_type = parsed.get("image_type")
    description = (
        parsed.get("short_description")  # backward compatibility
        or parsed.get("description")
        or parsed.get("summary")
    )
    if not description:
        return None

    header = f"<!-- Page {page_index + 1} Figure {image_index} -->"
    lines.append(header)
    if image_type:
        lines.append(f"> **Type:** {image_type}")
    lines.append(f"> **Description:** {description}")

    summary = parsed.get("summary")
    if summary and summary != description:
        lines.append(f"> **Details:** {summary}")
    lines.append("")
    return "\n".join(lines)


def format_document_annotation(annotation_payload: str | None) -> str | None:
    if not annotation_payload:
        return None
    try:
        parsed = json.loads(annotation_payload)
    except json.JSONDecodeError:
        return None

    parts = ["<!-- Document Annotation -->"]

    language = parsed.get("language")
    authors = parsed.get("authors")
    summary = parsed.get("summary")

    if language:
        parts.append(f"> **Language:** {language}")
    if authors:
        if isinstance(authors, list):
            author_list = ", ".join(str(a) for a in authors)
        else:
            author_list = str(authors)
        parts.append(f"> **Authors:** {author_list}")
    if summary:
        parts.append(f"> **Summary:** {summary}")

    parts.append("")
    formatted = "\n".join(parts)
    return formatted if formatted.strip() else None


def strip_image_placeholders(markdown: str) -> str:
    """Remove image placeholder tags from page markdown."""
    return re.sub(r"!\[[^\]]*\]\([^)]+\)", "", markdown)


def write_markdown(
    pages: Iterable,
    output_path: Path,
    *,
    describe_images: bool,
    document_annotation: str | None,
) -> None:
    """Assemble and write the final Markdown file from OCR pages."""
    markdown_chunks: list[str] = []

    if document_annotation:
        doc_note = format_document_annotation(document_annotation)
        if doc_note:
            markdown_chunks.append(doc_note)

    for page in sorted(pages, key=lambda p: p.index):
        content = strip_image_placeholders(page.markdown).rstrip()
        markdown_chunks.append(f"<!-- Page {page.index + 1} -->\n{content}\n")

        if page.images and describe_images:
            for idx, image in enumerate(page.images, start=1):
                annotation_note = format_image_annotation(
                    image.image_annotation, page.index, idx
                )
                if annotation_note:
                    markdown_chunks.append(annotation_note)

    output_path.write_text("\n".join(markdown_chunks).strip() + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# OCR pipeline
# ---------------------------------------------------------------------------


_MAX_ANNOTATION_PAGES = 8


def process_pdf(
    pdf_path: Path,
    output_path: Path,
    *,
    model: str = DEFAULT_MODEL,
    describe_images: bool = True,
    document_annotations: bool = True,
) -> Path:
    """Upload *pdf_path* to Mistral OCR and write the result to *output_path*.

    Returns the resolved output path.
    """
    api_key = ensure_api_key()
    client = Mistral(api_key=api_key)

    file_bytes = pdf_path.read_bytes()
    upload = client.files.upload(
        file=File(
            file_name=pdf_path.name,
            content=file_bytes,
            content_type="application/pdf",
        ),
        purpose="ocr",
    )

    bbox_format = (
        response_format_from_pydantic_model(ImageAnnotation)
        if describe_images
        else None
    )

    ocr_response = client.ocr.process(
        model=model,
        document={
            "type": "file",
            "file_id": upload.id,
        },
        include_image_base64=False,
        bbox_annotation_format=bbox_format,
        document_annotation_format=None,
        pages=None,
    )

    document_annotation_payload: str | None = None
    if document_annotations:
        total_pages = len(ocr_response.pages)
        page_count = min(total_pages, _MAX_ANNOTATION_PAGES)
        document_format = response_format_from_pydantic_model(DocumentAnnotation)
        doc_response = client.ocr.process(
            model=model,
            document={
                "type": "file",
                "file_id": upload.id,
            },
            include_image_base64=False,
            bbox_annotation_format=None,
            document_annotation_format=document_format,
            pages=list(range(page_count)),
        )
        annotation = doc_response.document_annotation
        if isinstance(annotation, str):
            document_annotation_payload = annotation

    output_path.parent.mkdir(parents=True, exist_ok=True)
    write_markdown(
        ocr_response.pages,
        output_path,
        describe_images=describe_images,
        document_annotation=document_annotation_payload,
    )
    return output_path
