from llama_index.llms.ollama import Ollama

from backend.app.core.config import settings

# 1. Define the Golden Dataset
# These are fact-based questions where we know the exact metric or definition expected.
GOLDEN_DATASET = [
    {"question": "How many identical layers is the encoder composed of?", "expected_fact": "6"},
    {
        "question": "What is the dimensionality of the output embeddings (d_model)?",
        "expected_fact": "512",
    },
    {
        "question": "What optimizer was used to train the Transformer?",
        "expected_fact": "Adam optimizer",
    },
]

# 2. Define the strict LLM Judge
# We use a separate LLM instance to grade the output objectively.
judge_llm = Ollama(model=settings.LLM_MODEL, base_url=settings.OLLAMA_HOST, request_timeout=120.0)

EVALUATION_PROMPT = """
You are a strict, objective grader evaluating a Retrieval-Augmented Generation (RAG) system.
You will be provided with a QUESTION, an EXPECTED FACT, and the RAG SYSTEM'S ANSWER.

Your only job is to determine if the RAG SYSTEM'S ANSWER accurately contains the EXPECTED FACT.
Ignore extra context as long as it does not contradict the expected fact.

QUESTION: {question}
EXPECTED FACT: {expected_fact}
RAG SYSTEM'S ANSWER: {actual_answer}

If the answer is factually correct and contains the expected fact, output exactly: PASS
If the answer is incorrect, hallucinated, or missing the expected fact, output exactly: FAIL

GRADE:
"""


def test_golden_dataset_accuracy(client):
    """
    Evaluation test that seeds the database with the PDF, runs queries through
    the in-memory FastAPI client, and uses an LLM to grade factual accuracy.
    """
    headers = {"X-API-Key": settings.API_KEY}

    # 1. SETUP: Ensure the document is in the database before querying
    # Using the TestClient allows this to work locally or in Docker seamlessly.
    pdf_path = "data/attention_is_all_you_need.pdf"
    with open(pdf_path, "rb") as f:
        upload_response = client.post(
            "/documents/upload",
            files={"file": ("attention_is_all_you_need.pdf", f, "application/pdf")},
            headers=headers,
        )
    # 201 means created, 200 means ok, 400/409 means duplicate
    assert upload_response.status_code in (200, 201, 400, 409), "Failed to seed database"

    # 2. EVALUATION: Run the golden dataset
    for item in GOLDEN_DATASET:
        payload = {"query": item["question"]}
        response = client.post("/query", json=payload, headers=headers)

        assert response.status_code == 200, f"API failed on question: {item['question']}"
        actual_answer = response.json()["answer"]

        prompt = EVALUATION_PROMPT.format(
            question=item["question"],
            expected_fact=item["expected_fact"],
            actual_answer=actual_answer,
        )

        grade_response = judge_llm.complete(prompt)
        grade = grade_response.text.strip().upper()

        assert "PASS" in grade, (
            f"Failed Question: '{item['question']}'.\nExpected: {item['expected_fact']}\n \
            Got: {actual_answer}"
        )
