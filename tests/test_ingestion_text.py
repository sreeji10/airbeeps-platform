from services.ingestion.text import chunk_text


def test_chunk_text_creates_overlapping_chunks() -> None:
    text = " ".join(["word"] * 1000)
    chunks = chunk_text(text, chunk_size=200, overlap=50)

    assert len(chunks) > 1
    assert all(chunk for chunk in chunks)
