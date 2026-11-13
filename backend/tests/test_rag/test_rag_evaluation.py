import json
import os
from datetime import UTC, datetime
from importlib.util import find_spec
from pathlib import Path

import pandas as pd
import pytest
from datasets import Dataset
from ragas import RunConfig, evaluate
from ragas.embeddings import LlamaIndexEmbeddingsWrapper
from ragas.llms import LlamaIndexLLMWrapper
from ragas.metrics import (
    answer_relevancy,
    context_precision,
    context_recall,
    faithfulness,
)

from backend.app.core.config import settings
from backend.app.rag.retrieval import retrieval_service
from backend.app.services.llm_factory import llm_service

REPO_ROOT = Path(__file__).resolve().parents[3]
GOLDEN_DATASET_PATH = Path(__file__).resolve().parent / "golden_dataset.json"
BENCHMARKS_DIR = REPO_ROOT / "docs" / "benchmarks"


def load_golden_dataset(filepath: str) -> list[dict]:
    """Loads the static golden dataset artifact from disk."""
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(
            f"Golden dataset not found at {path}. Run "
            "`uv run python backend/scripts/generate_golden_dataset.py` first."
        )

    with path.open("r", encoding="utf-8") as f:
        dataset = json.load(f)

    if not isinstance(dataset, list):
        raise ValueError(f"Golden dataset at {path} must be a JSON array.")

    for index, item in enumerate(dataset):
        missing = {"question", "ground_truth"} - set(item)
        if missing:
            raise ValueError(f"Golden dataset item {index} is missing fields: {sorted(missing)}")

    return dataset


def _dataframe_to_markdown(df) -> str:
    """Renders a pandas DataFrame as a GitHub-flavored Markdown table."""
    headers = [str(column) for column in df.columns]
    separator = ["---"] * len(headers)
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(separator) + " |",
    ]

    for row in df.itertuples(index=False, name=None):
        cells = [str(value).replace("|", "\\|").replace("\n", " ") for value in row]
        lines.append("| " + " | ".join(cells) + " |")

    return "\n".join(lines)


def export_ablation_report(evaluation_results: dict, filename: str = "gate_0_baseline.md") -> Path:
    """Writes a Ragas result DataFrame to a dated Markdown ablation report."""

    if hasattr(evaluation_results, "to_pandas"):
        df = evaluation_results.to_pandas()
    elif isinstance(evaluation_results, dict):
        df = pd.DataFrame(evaluation_results)
    else:
        df = evaluation_results

    BENCHMARKS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = BENCHMARKS_DIR / filename

    lines = [
        "# RAG Evaluation Ablation Report",
        "",
        f"- Generated: {datetime.now(UTC).isoformat()}",
        f"- Rows: {len(df)}",
        "",
        _dataframe_to_markdown(df),
    ]

    numeric_columns = list(df.select_dtypes(include="number").columns)
    if numeric_columns:
        lines.extend(
            [
                "",
                "## Aggregate Scores",
                "",
                "| Metric | Mean | Valid Samples |",
                "| --- | --- | --- |",
            ]
        )
        lines.extend(
            f"| {column} | {df[column].mean():.4f} | {df[column].count()}/{len(df)} |"
            for column in numeric_columns
        )

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path


@pytest.mark.skipif(
    os.getenv("GITHUB_ACTIONS") == "true",
    reason=(
        "Ragas evaluation requires a live PostgreSQL instance and Ollama LLM, "
        "which are not available in CI."
    ),
)
@pytest.mark.skipif(
    not GOLDEN_DATASET_PATH.exists(),
    reason="golden_dataset.json is missing. Run generate_golden_dataset.py first.",
)
@pytest.mark.skipif(
    find_spec("ragas") is None,
    reason="Ragas eval dependencies are not installed.",
)
def test_ragas_triad_metrics(client):
    """Runs the golden dataset through /query and collects records for Ragas scoring."""
    golden_dataset = load_golden_dataset(str(GOLDEN_DATASET_PATH))
    headers = {"X-API-Key": settings.API_KEY}

    # Ensure the evaluation document is present before querying.
    pdf_path = REPO_ROOT / "data" / "attention_is_all_you_need.pdf"
    with open(pdf_path, "rb") as f:
        upload_response = client.post(
            "/documents/upload",
            files={"file": ("attention_is_all_you_need.pdf", f, "application/pdf")},
            headers=headers,
        )
    # 201 means created, 200 means ok, 400/409 means duplicate
    assert upload_response.status_code in (200, 201, 400, 409), "Failed to seed database"

    records = []
    for item in golden_dataset:
        response = client.post("/query", json={"query": item["question"]}, headers=headers)
        assert response.status_code == 200, f"API failed on question: {item['question']}"

        payload = response.json()
        sources_text = [source["text"] for source in payload.get("sources", [])]
        records.append(
            {
                # Modern Ragas keys
                "user_input": item["question"],
                "response": payload["answer"],
                "retrieved_contexts": sources_text,
                "reference": item["ground_truth"],
                # Legacy Ragas keys (for metrics expecting older aliases)
                "question": item["question"],
                "answer": payload["answer"],
                "contexts": sources_text,
                "ground_truth": item["ground_truth"],
            }
        )

    assert records, "Golden dataset produced no evaluation records."

    # Convert the list of dicts to a Hugging Face Dataset format
    dataset = Dataset.from_list(records)

    # Wrap LlamaIndex LLM and Embeddings for Ragas
    ragas_llm = LlamaIndexLLMWrapper(llm=llm_service.llm)
    ragas_embeddings = LlamaIndexEmbeddingsWrapper(embeddings=retrieval_service.embed_model)

    # Execute Ragas evaluation
    evaluation_result = evaluate(
        dataset=dataset,
        metrics=[
            context_precision,
            context_recall,
            faithfulness,
            answer_relevancy,
        ],
        llm=ragas_llm,
        embeddings=ragas_embeddings,
        run_config=RunConfig(max_workers=2, timeout=300, max_retries=3),
        raise_exceptions=False,
    )

    report_filename = os.getenv("EVAL_REPORT_FILENAME", "gate_0_baseline.md")
    export_ablation_report(evaluation_result, filename=report_filename)
