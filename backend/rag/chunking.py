"""LangChain text-splitting compatibility helper."""

from langchain_text_splitters import RecursiveCharacterTextSplitter


def split_text(text: str, chunk_size: int = 900, overlap: int = 150) -> list[str]:
    """Split text with LangChain's recursive character splitter."""
    if chunk_size <= overlap:
        raise ValueError("chunk_size must be larger than overlap")
    if not text or not text.strip():
        return []

    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=overlap,
    ).split_text(text.strip())
