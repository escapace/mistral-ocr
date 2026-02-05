"""Pydantic models for Mistral OCR annotation schemas."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class ImageType(StrEnum):
    GRAPH = "graph"
    TEXT = "text"
    TABLE = "table"
    IMAGE = "image"


class ImageAnnotation(BaseModel):
    """Structured description for OCR-detected images."""

    image_type: ImageType = Field(
        ...,
        description=(
            "The type of the image. Must be one of 'graph', 'text', 'table' or 'image'."
        ),
    )
    description: str = Field(
        ..., description="A concise description suitable for captions."
    )
    summary: str | None = Field(
        None, description="Optional extended description highlighting key details."
    )


class DocumentAnnotation(BaseModel):
    """Structured metadata summarizing the full document."""

    language: str = Field(
        ..., description="Language code for the document (ISO 639-1)."
    )
    summary: str = Field(..., description="Overall summary of the document.")
    authors: list[str] | None = Field(
        None,
        description="List of authors or organizations credited in the document.",
    )
