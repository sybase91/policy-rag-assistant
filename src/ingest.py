"""Load PDF documents from data/raw into LangChain Document objects."""

from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document

from src.config import RAW_DATA_DIR


def load_pdfs(raw_dir: Path | None = None) -> list[Document]:
    """Load every PDF in raw_dir and return page-level LangChain Documents.

    Each document preserves metadata:
      - source_file: PDF filename (e.g. nist-ai-100-1.pdf)
      - page: 0-based page index
    """
    directory = raw_dir or RAW_DATA_DIR
    pdf_paths = sorted(directory.glob("*.pdf"))

    documents: list[Document] = []
    for pdf_path in pdf_paths:
        loader = PyPDFLoader(str(pdf_path))
        pages = loader.load()
        for doc in pages:
            page_number = doc.metadata.get("page", 0)
            doc.metadata = {
                "source_file": pdf_path.name,
                "page": page_number,
            }
            documents.append(doc)

    return documents


if __name__ == "__main__":
    pdfs = sorted(RAW_DATA_DIR.glob("*.pdf"))
    documents = load_pdfs()

    print(f"PDFs found: {len(pdfs)}")
    print(f"Pages loaded: {len(documents)}")
    if documents:
        print(f"Sample metadata: {documents[0].metadata}")
    else:
        print("No documents loaded. Add PDFs to data/raw/ and try again.")
