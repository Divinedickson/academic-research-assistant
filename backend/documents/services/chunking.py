import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Chunk:
    page_number: int
    chunk_index: int
    content: str
    character_count: int


def _find_split_point(text, start, hard_end, target_size):
    preferred_window_start = start + max(target_size // 2, 1)
    window = text[preferred_window_start:hard_end]

    for pattern in ['\n\n', '. ', '? ', '! ', '\n', ' ']:
        index = window.rfind(pattern)

        if index != -1:
            return preferred_window_start + index + len(pattern)

    return hard_end


def _next_start(text, start, end, overlap):
    if end >= len(text):
        return len(text)

    next_start = max(end - overlap, start + 1)

    while next_start < len(text) and text[next_start].isspace():
        next_start += 1

    return next_start


def chunk_pages(pages, chunk_size=1000, overlap=200):
    if chunk_size <= 0:
        raise ValueError('chunk_size must be greater than zero.')

    if overlap < 0:
        raise ValueError('overlap cannot be negative.')

    if overlap >= chunk_size:
        raise ValueError('overlap must be smaller than chunk_size.')

    chunks = []
    chunk_index = 0

    # Chunks never cross page boundaries, so future citations can point to one
    # reliable page. For each page, we take a target-sized window, prefer a
    # paragraph/sentence/word break near the end, then move back by the overlap.
    # `_next_start` always advances at least one character to avoid infinite
    # loops when long text has no useful split boundary.
    for page in pages:
        text = re.sub(r'\s+\n', '\n', page.content).strip()

        if not text:
            continue

        start = 0
        text_length = len(text)

        while start < text_length:
            hard_end = min(start + chunk_size, text_length)
            end = hard_end

            if hard_end < text_length:
                end = _find_split_point(text, start, hard_end, chunk_size)

            content = text[start:end].strip()

            if content:
                chunks.append(
                    Chunk(
                        page_number=page.page_number,
                        chunk_index=chunk_index,
                        content=content,
                        character_count=len(content),
                    ),
                )
                chunk_index += 1

            start = _next_start(text, start, end, overlap)

    return chunks
