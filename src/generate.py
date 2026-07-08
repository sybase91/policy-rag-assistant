"""Generate grounded RAG answers with source citations.

Generation is the "G" in RAG: the LLM writes a natural-language answer.
Grounded generation means the answer must come only from retrieved chunks,
not the model's general training knowledge. We pass chunks to the LLM because
it has not read your PDFs directly. Citations let users verify claims in the
original documents. Unsupported questions should be refused rather than invented.
"""

from __future__ import annotations

from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from src.config import CHAT_MODEL, CHAT_TEMPERATURE
from src.embed import validate_api_key
from src.retrieve import retrieve_context

REFUSAL_MESSAGE = "I don't know based on the provided documents."

SYSTEM_PROMPT = """You are an Enterprise AI Governance Assistant.

Answer the user's question using only the provided context.

Rules:
- Use only the provided context.
- Do not use outside knowledge.
- If the answer is not supported by the context, say:
  "I don't know based on the provided documents."
- Be concise and practical.
- Use bullet points when helpful.
- Cite sources using this format:
  [source_file, page X]
- Do not invent laws, policies, controls, citations, page numbers, or recommendations.
- If multiple sources are relevant, cite multiple sources.
- If the retrieved context is weak or unrelated, say that the documents do not provide enough information."""

DEMO_QUESTIONS = [
    "What is prompt injection?",
    "What are the core functions of the NIST AI Risk Management Framework?",
    "What risks are specific to generative AI systems?",
    "How does cybersecurity governance connect to AI governance?",
    "What is my company's refund policy?",
]


def format_context(chunks: list[Document]) -> str:
    """Convert retrieved LangChain Document chunks into a clean context string.

    Each chunk includes source_file, page, chunk_id, and text.
    """
    blocks: list[str] = []
    for index, chunk in enumerate(chunks, start=1):
        metadata = chunk.metadata
        block = (
            f"--- Chunk {index} ---\n"
            f"source_file: {metadata.get('source_file', 'unknown')}\n"
            f"page: {metadata.get('page', 'unknown')}\n"
            f"chunk_id: {metadata.get('chunk_id', 'unknown')}\n"
            f"text:\n{chunk.page_content}"
        )
        blocks.append(block)
    return "\n\n".join(blocks)


def extract_sources(chunks: list[Document]) -> list[dict]:
    """Return a clean list of unique sources with source_file, page, chunk_id."""
    seen_chunk_ids: set[str] = set()
    sources: list[dict] = []

    for chunk in chunks:
        metadata = chunk.metadata
        chunk_id = metadata.get("chunk_id", "unknown")
        if chunk_id in seen_chunk_ids:
            continue
        seen_chunk_ids.add(chunk_id)
        sources.append(
            {
                "source_file": metadata.get("source_file", "unknown"),
                "page": metadata.get("page", "unknown"),
                "chunk_id": chunk_id,
            }
        )
    return sources


def answer_question(question: str, k: int = 5) -> dict:
    """Retrieve relevant chunks and generate a grounded answer.

    Return a dictionary with question, answer, sources, and retrieved_context_count.
    """
    # Step 1: Validate API key (needed for retrieval embeddings and chat).
    validate_api_key()

    # Step 2: Retrieve relevant chunks from Chroma (Phase 3).
    chunks = retrieve_context(question, k=k)

    # Step 3: Refuse early if nothing was retrieved.
    if not chunks:
        return {
            "question": question,
            "answer": REFUSAL_MESSAGE,
            "sources": [],
            "retrieved_context_count": 0,
        }

    # Step 4: Format retrieved chunks into a context block for the LLM.
    context = format_context(chunks)

    # Step 5: Call ChatOpenAI with a strict grounded system prompt.
    llm = ChatOpenAI(model=CHAT_MODEL, temperature=CHAT_TEMPERATURE)
    response = llm.invoke(
        [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(
                content=f"Context:\n{context}\n\nQuestion:\n{question}"
            ),
        ]
    )

    # Step 6: Return structured result with citation metadata.
    answer_text = response.content
    if isinstance(answer_text, list):
        answer_text = " ".join(str(part) for part in answer_text)

    return {
        "question": question,
        "answer": str(answer_text),
        "sources": extract_sources(chunks),
        "retrieved_context_count": len(chunks),
    }


def print_answer_result(result: dict) -> None:
    """Print question, answer, and sources in a beginner-friendly format."""
    print(f"\nQuestion: {result['question']}")
    print("\nAnswer:")
    print(result["answer"])

    print("\nSources:")
    sources = result.get("sources", [])
    if not sources:
        print("(none)")
        return

    for index, source in enumerate(sources, start=1):
        print(
            f"{index}. {source['source_file']}, page {source['page']}, "
            f"chunk_id={source['chunk_id']}"
        )


if __name__ == "__main__":
    print("Phase 4 Grounded Generation Demo")
    print(f"Chat model: {CHAT_MODEL} (temperature={CHAT_TEMPERATURE})")
    print("=" * 60)

    for question in DEMO_QUESTIONS:
        result = answer_question(question, k=5)
        print_answer_result(result)
        print("\n" + "=" * 60)
