from dataclasses import dataclass
from pathlib import Path

from pptx import Presentation


@dataclass
class ParsedSlide:
    slide_num: int  # 1-indexed
    text: str
    source: str     # filename


def parse_pptx(path: str | Path) -> list[ParsedSlide]:
    """Extract text from every slide of a PPTX file."""
    path = Path(path)
    source = path.name
    prs = Presentation(str(path))
    slides: list[ParsedSlide] = []

    for i, slide in enumerate(prs.slides, 1):
        lines: list[str] = []
        for shape in slide.shapes:
            if not shape.has_text_frame:
                continue
            for para in shape.text_frame.paragraphs:
                line = para.text.strip()
                if line:
                    lines.append(line)
        slides.append(ParsedSlide(
            slide_num=i,
            text="\n".join(lines),
            source=source,
        ))

    return slides
