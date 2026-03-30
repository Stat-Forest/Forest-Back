from dataclasses import dataclass
from typing import List


@dataclass(slots=True)
class Chunk:
    text: str
    index: int
    token_count: int


def estimate_tokens(text: str) -> int:
    """
    Rough token estimator.
    For Uzbek/Russian/English mixed text, 1 token ~= 4 chars is acceptable for approximation.
    """
    cleaned = (text or "").strip()
    if not cleaned:
        return 0
    return max(1, len(cleaned) // 4)


def chunk_text(text: str, chunk_size: int = 1200, overlap: int = 200) -> List[Chunk]:
    """
    Split text into overlapping chunks.

    Rules:
    - chunk_size must be > 0
    - overlap must be >= 0
    - overlap must be smaller than chunk_size
    """
    normalized = " ".join((text or "").split())
    if not normalized:
        return []

    if chunk_size <= 0:
        raise ValueError("chunk_size must be > 0")

    if overlap < 0:
        raise ValueError("overlap must be >= 0")

    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    chunks: List[Chunk] = []
    start = 0
    idx = 0
    step = chunk_size - overlap

    while start < len(normalized):
        end = min(len(normalized), start + chunk_size)
        piece = normalized[start:end].strip()

        if piece:
            chunks.append(
                Chunk(
                    text=piece,
                    index=idx,
                    token_count=estimate_tokens(piece),
                )
            )
            idx += 1

        if end >= len(normalized):
            break

        start += step

    return chunks