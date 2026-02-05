"""Command-line interface for mistral-ocr."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from mistral_ocr.core import DEFAULT_MODEL, process_pdf, resolve_output_path

app = typer.Typer(
    name="mistral-ocr",
    help=(
        "Extract text from PDFs as Markdown via the Mistral OCR API.\n\n"
        "Uploads a PDF to Mistral's Document AI service, runs OCR, and writes "
        "the result as a Markdown file. Preserves document structure including "
        "headings, tables, lists, and optionally describes detected figures.\n\n"
        "Requires the MISTRAL_API_KEY environment variable (or a .env file)."
    ),
    add_completion=False,
    rich_markup_mode=None,
    invoke_without_command=True,
)


@app.command()
def main(
    ctx: typer.Context,
    pdf_path: Annotated[
        Path | None,
        typer.Argument(help="Path to the PDF to process."),
    ] = None,
    output: Annotated[
        Path | None,
        typer.Option(
            "-o",
            "--output",
            help="Output Markdown path. Defaults to <input>.md.",
        ),
    ] = None,
    model: Annotated[
        str,
        typer.Option(
            "-m",
            "--model",
            help="Mistral OCR model to use.",
        ),
    ] = DEFAULT_MODEL,
    describe_images: Annotated[
        bool,
        typer.Option(
            help="Annotate detected figures with type, caption, and summary.",
        ),
    ] = True,
    document_annotations: Annotated[
        bool,
        typer.Option(
            help="Prepend document-level metadata (language, authors, summary).",
        ),
    ] = True,
) -> None:
    """Extract text from a PDF as Markdown via the Mistral OCR API."""
    if pdf_path is None:
        typer.echo(ctx.get_help(), err=True)
        raise typer.Exit(code=1)
    if not pdf_path.exists():
        typer.echo(f"Error: PDF not found at {pdf_path}", err=True)
        raise typer.Exit(code=1)
    if not pdf_path.is_file():
        typer.echo(f"Error: {pdf_path} is not a file", err=True)
        raise typer.Exit(code=1)

    out = resolve_output_path(pdf_path, output)

    try:
        result = process_pdf(
            pdf_path,
            out,
            model=model,
            describe_images=describe_images,
            document_annotations=document_annotations,
        )
        typer.echo(f"Wrote {result}")
    except RuntimeError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc


if __name__ == "__main__":
    app()
