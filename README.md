# mistral-ocr

Command-line tool that extracts text from PDFs as Markdown using the
Mistral OCR API. Uploads a PDF to Mistral's Document AI service, runs OCR,
and writes the result as a Markdown file. Document structure (headings,
tables, lists) is preserved, and detected figures can be annotated with
captions and summaries.

## Requirements

- Python 3.13+
- A [Mistral API key](https://console.mistral.ai/api-keys)

## Installation

```
uv tool install "git+https://github.com/escapace/mistral-ocr"
```

## Usage

```
export MISTRAL_API_KEY=<key>
mistral-ocr document.pdf
```

The API key can also be set in a `.env` file in the working directory.

Output defaults to `document.md`. To specify a different path:

```
mistral-ocr document.pdf -o output.md
```

### Options

```
-o, --output PATH                Output Markdown path. Defaults to <input>.md.
-m, --model TEXT                 Mistral OCR model to use. [default: mistral-ocr-latest]
--no-describe-images             Skip figure annotations.
--no-document-annotations        Skip document-level metadata.
```
