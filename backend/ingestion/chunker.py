import json
from typing import Optional
from pathlib import Path


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 100) -> list[str]:
    """Split text into overlapping chunks."""
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)
        i += chunk_size - overlap
    return [c for c in chunks if c.strip()]


def parse_file(content: bytes, filename: str) -> str:
    """Parse file content to plain text based on extension."""
    ext = Path(filename).suffix.lower()

    if ext in (".md", ".txt"):
        return content.decode("utf-8", errors="ignore")

    if ext == ".json":
        try:
            data = json.loads(content.decode("utf-8"))
            return _flatten_json(data)
        except Exception:
            return content.decode("utf-8", errors="ignore")

    if ext == ".pdf":
        try:
            import io
            from PyPDF2 import PdfReader
            reader = PdfReader(io.BytesIO(content))
            return "\n".join(p.extract_text() or "" for p in reader.pages)
        except Exception as e:
            raise ValueError(f"PDF parse error: {e}")

    raise ValueError(f"Unsupported file type: {ext}")


def _flatten_json(obj, prefix: str = "") -> str:
    """Recursively flatten JSON object to text."""
    lines = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            lines.append(_flatten_json(v, f"{prefix}{k}: " if prefix == "" else f"{prefix}.{k}: "))
    elif isinstance(obj, list):
        for item in obj:
            lines.append(_flatten_json(item, prefix))
    else:
        lines.append(f"{prefix}{obj}")
    return "\n".join(lines)
