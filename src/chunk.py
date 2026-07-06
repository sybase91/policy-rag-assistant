"""Split ingested documents into smaller chunks for retrieval."""

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.config import CHUNK_OVERLAP, CHUNK_SIZE
from src.ingest import load_pdfs


def chunk_documents(
    documents: list[Document] | None = None,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
) -> list[Document]:
    """Split page documents into chunks while preserving metadata.

    Adds chunk_id to each chunk, e.g. nist-ai-100-1.pdf_p12_c003.
    """
    if documents is None:
        documents = load_pdfs()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

    chunks: list[Document] = []
    for doc in documents:
        source_file = doc.metadata.get("source_file", "unknown")
        page = doc.metadata.get("page", 0)
        split_docs = splitter.split_documents([doc])

        for chunk_index, chunk in enumerate(split_docs):
            chunk.metadata["source_file"] = source_file
            chunk.metadata["page"] = page
            chunk.metadata["chunk_id"] = f"{source_file}_p{page}_c{chunk_index:03d}"
            chunks.append(chunk)

    return chunks


if __name__ == "__main__":
    documents = load_pdfs()
    chunks = chunk_documents(documents)

    print(f"Pages loaded: {len(documents)}")
    print(f"Chunks created: {len(chunks)}")
    if chunks:
        sample = chunks[0]
        preview = sample.page_content[:200].replace("\n", " ")
        print(f"Sample chunk text: {preview}...")
        print(f"Sample metadata: {sample.metadata}")
    else:
        print("No chunks created. Add PDFs to data/raw/ and try again.")
