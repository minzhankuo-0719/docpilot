import re
import unicodedata


def clean_text(text: str) -> str:
    """Normalise raw extracted text from PDF or PPTX."""
    # Normalise unicode (e.g. ligatures, full-width chars)
    text = unicodedata.normalize("NFKC", text)
    # Fix PDF soft-hyphen line breaks: "atten-\ntion" → "attention"
    text = re.sub(r"-\n(\w)", r"\1", text)
    # Collapse remaining newlines to spaces
    text = re.sub(r"\n+", " ", text)
    # Remove control characters (keep tab/space)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    # Collapse multiple spaces
    text = re.sub(r" {2,}", " ", text)
    return text.strip()
