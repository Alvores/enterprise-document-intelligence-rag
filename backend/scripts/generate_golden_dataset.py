import json
import os
import time
from pathlib import Path
from typing import Literal

from llama_index.core import PromptTemplate
from pydantic import BaseModel, Field

from backend.app.core.logging import logger
from backend.app.db.connection import db_manager
from backend.app.services.llm_factory import llm_service

GOLDEN_DATASET_PATH = (
    Path(__file__).resolve().parent.parent / "tests" / "test_rag" / "golden_dataset.json"
)
VECTOR_STORE_TABLE = "data_enterprise_documents"
RATE_LIMIT_SECONDS = float(os.getenv("GOLDEN_DATASET_RATE_LIMIT_SECONDS", "1.0"))
MAX_RETRIES = 3


class GoldenQAPair(BaseModel):
    question_type: Literal["factual", "synthesis", "unanswerable"] = Field(
        ..., description="The type of question being asked."
    )
    question: str = Field(description="The question generated from the text.")
    ground_truth: str = Field(
        description=(
            "The exact, concise answer to the question based ONLY on the text. If \n"
            "unanswerable, output exactly: 'I do not have enough information in the provided \n"
            "documents to answer this query.'"
        )
    )


TEACHER_PROMPT_TEMPLATE = PromptTemplate(
    """You are an expert AI evaluator creating a rigorous test exam for an Enterprise RAG system.
    I will provide you with a CHUNK of text retrieved from an enterprise document.
    Your task is to generate ONE single structured Question and Answer pair based on this CHUNK.

    CHUNK:
    {chunk_text}

    INSTRUCTIONS:
    1. Select one of the following question types at random:
    - "factual": A direct question requiring a specific entity, metric, date, or definition from
    the text.
    - "synthesis": A question that requires connecting two distinct ideas or clauses within the
    text.
    - "unanswerable": A question that sounds related to the text's topic, but the answer is
    deliberately missing from the provided CHUNK.

    2. If "factual" or "synthesis", provide the exact, concise answer based ONLY on the CHUNK.
    3. If "unanswerable", the ground truth answer MUST be exactly:
    "I do not have enough information in the provided documents to answer this query."
    """
)


def fetch_random_chunks(limit: int = 20) -> list[str]:
    """Randomly samples raw chunk text from the pgvector data table."""
    query = f"SELECT text FROM {VECTOR_STORE_TABLE} ORDER BY RANDOM() LIMIT %s;"

    try:
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (limit,))
                rows = cur.fetchall()
    except Exception as e:
        logger.error("Failed to fetch random chunks", extra={"error": str(e)})
        raise

    chunks = [row[0].strip() for row in rows if row[0] and row[0].strip()]
    logger.info(
        "Fetched random chunks from vector store",
        extra={"requested": limit, "returned": len(chunks), "table": VECTOR_STORE_TABLE},
    )
    return chunks


def generate_qa_pairs_for_chunks(chunks: list[str]) -> list[dict]:
    """Generates structured Q&A pairs for each chunk, pacing calls to avoid rate limits."""
    qa_pairs: list[dict] = []
    total = len(chunks)

    for index, raw_chunk in enumerate(chunks, start=1):
        chunk = raw_chunk.strip()
        if not chunk:
            continue

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                qa_pair = llm_service.llm.structured_predict(
                    GoldenQAPair,
                    TEACHER_PROMPT_TEMPLATE,
                    chunk_text=chunk,
                )
                qa_pairs.append(
                    qa_pair.model_dump() if isinstance(qa_pair, BaseModel) else dict(qa_pair)
                )
                logger.info(
                    "Generated golden Q&A pair",
                    extra={
                        "chunk_index": index,
                        "total_chunks": total,
                        "question_type": qa_pair.question_type,
                    },
                )
                break
            except Exception as e:
                logger.warning(
                    "QA generation attempt failed",
                    extra={"chunk_index": index, "attempt": attempt, "error": str(e)},
                )
                if attempt == MAX_RETRIES:
                    logger.error(
                        "Exhausted retries for chunk; skipping.",
                        extra={"chunk_index": index},
                    )
                else:
                    time.sleep(RATE_LIMIT_SECONDS * attempt)

        if index < total:
            time.sleep(RATE_LIMIT_SECONDS)

    return qa_pairs


def main() -> None:
    """Generates the golden dataset artifact consumed by the Ragas evaluation harness."""
    logger.info("Starting synthetic golden dataset generation...")

    chunks = fetch_random_chunks(limit=20)
    if not chunks:
        logger.error(
            "No chunks available in the vector store. Ingest documents before generating a dataset."
        )
        raise SystemExit(1)

    qa_pairs = generate_qa_pairs_for_chunks(chunks)
    if not qa_pairs:
        logger.error("LLM produced no usable Q&A pairs; refusing to overwrite the dataset.")
        raise SystemExit(1)

    GOLDEN_DATASET_PATH.parent.mkdir(parents=True, exist_ok=True)
    GOLDEN_DATASET_PATH.write_text(
        json.dumps(qa_pairs, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    logger.info(
        "Golden dataset saved",
        extra={"path": str(GOLDEN_DATASET_PATH), "qa_pairs": len(qa_pairs)},
    )


if __name__ == "__main__":
    main()
