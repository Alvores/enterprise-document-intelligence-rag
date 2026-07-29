# Architecture Decision Records (ADRs)

## ADR-001: Monorepo Separation (`backend/` vs `frontend/`)
* **Date:** 2026-06-19
* **Status:** Accepted
* **Context:** Project will eventually include a React SPA alongside the Python API.
* **Decision:** Establish `backend/` and `frontend/` as top-level directories immediately, even though frontend is empty.
* **Consequences:** Prevents `.venv` and `node_modules` dependency clashing and signals full-stack system awareness from Day 1.

## ADR-002: LlamaIndex over LangChain
* **Date:** 2026-06-19
* **Status:** Accepted
* **Context:** Required an orchestration framework for document ingestion and retrieval.
* **Decision:** Use LlamaIndex.
* **Alternatives:** LangChain or LangGraph.
* **Consequences:** Avoided "framework soup." LlamaIndex provides superior native abstractions for a pure RAG data pipeline. Agentic state-machines (LangGraph) were deemed out of scope.

## ADR-003: PostgreSQL + pgvector
* **Date:** 2026-06-19
* **Status:** Accepted
* **Context:** Needed a vector database for embedding storage.
* **Decision:** PostgreSQL with the `pgvector` extension via local Docker.
* **Alternatives:** SaaS vector databases (Pinecone, Weaviate).
* **Consequences:** Single database architecture, guarantees ACID compliance, supports hybrid search (BM25 + dense), and keeps local development cost at $0.

## ADR-004: Package Management via `uv`
* **Date:** 2026-06-19
* **Status:** Accepted
* **Context:** Needed a deterministic, fast Python 3.12 environment manager.
* **Decision:** Use `uv` with `pyproject.toml` and `uv.lock`.
* **Alternatives:** `poetry` (slower, heavier) or standard `pip` (less reproducible).
* **Consequences:** Achieved sub-second dependency resolution and strict lockfile determinism, matching modern CI/CD standards.

## ADR-005: CPU-Only PyTorch for Local Development
* **Date:** 2026-06-19
* **Status:** Accepted
* **Context:** The local machine's RTX 5070 Ti (Blackwell sm_120 architecture) is not yet supported by stable PyTorch CUDA wheels, causing kernel execution errors.
* **Decision:** Fall back to CPU-only execution for `sentence-transformers` rather than debugging nightly PyTorch builds.
* **Consequences:** Embedding generation is slightly slower, but completely unblocks Project 1 development. The GPU is reserved for running Ollama LLMs, where VRAM acceleration is actually mission-critical.

## ADR-006: AI Boundary Mocking for Unit Tests
* **Date:** 2026-06-21
* **Status:** Accepted
* **Context:** Adding `pytest` coverage for the `/documents/upload` API endpoint.
* **Decision:** Use `unittest.mock` to intercept and mock the `IngestionService` during API route testing.
* **Consequences:** Prevents `pytest` from invoking CPU-heavy embedding models or establishing database connections during standard CI/CD runs. Ensures the test suite executes in milliseconds while still validating HTTP boundaries, Pydantic schemas, and error handling.

## ADR-007: Content-Based Deduplication (SHA-256)
* **Date:** 2026-06-21
* **Status:** Accepted
* **Context:** Preventing duplicate embeddings from polluting the vector database and degrading retrieval quality.
* **Decision:** Implemented a SHA-256 hashing mechanism on the raw incoming file bytes.
* **Consequences:** Eliminates redundant compute costs and prevents identical documents (even if renamed) from being embedded twice. Required adding a relational `documents` tracking table alongside the `pgvector` nodes.

## ADR-008: Overriding LLM Refine Prompts
* **Date:** 2026-06-28
* **Status:** Accepted
* **Context:** LlamaIndex automatically chunks large context retrievals and uses a "compact and refine" strategy if the retrieved nodes exceed the LLM's context window.
* **Decision:** Explicitly override both `text_qa_template` and `refine_template` with custom, strict enterprise prompts.
* **Consequences:** Prevents the framework from falling back to generic default prompts during multi-chunk refinement, guaranteeing the LLM strictly adheres to "only answer from context" rules across all pagination loops.

## ADR-009: Asymmetric Embedding Query Instructions
* **Date:** 2026-07-05
* **Status:** Accepted
* **Context:** The `BAAI/bge-small-en-v1.5` model requires specific instruction prefixes for query embeddings to maintain high cosine similarity scores during retrieval.
* **Decision:** Hardcode the `query_instruction` parameter directly into the `HuggingFaceEmbedding` initialization.
* **Consequences:** Ensures accurate chunk retrieval without permanently appending the prompt to the stored document vectors.

## ADR-010: Native Transformers for Exact Token Telemetry
* **Date:** 2026-07-05
* **Status:** Accepted
* **Context:** Required accurate token counting for LLMOps telemetry. Proxy tokenizers like `tiktoken` can notably miscalculate open-source model chunk boundaries.
* **Decision:** Import `AutoTokenizer` directly from the Hugging Face `transformers` library, utilizing the exact vocabularies of the BGE and Qwen models.
* **Consequences:** Provides 100% precise token usage logging for both embeddings and generations without relying on inaccurate OpenAI approximations.

## ADR-011: LLM Environment Splitting (Factory Pattern)
* **Date:** 2026-07-26
* **Status:** Accepted
* **Context:** Ollama runs locally but cannot run inside a standard serverless Cloud Run container.
* **Decision:** Implement an LLMFactory that dynamically instantiates Ollama if running locally, or Gemini 3.6 Flash if a GEMINI_API_KEY (mapped from Secret Manager) is detected.
* **Consequences:** Achieved parity between a $0 local dev environment and a high-availability, high-speed cloud runtime without modifying core retrieval logic.

## ADR-012: Zero-Trust Database Networking
* **Date:** 2026-07-26
* **Status:** Accepted
* **Context:** The PostgreSQL database containing raw enterprise documents needed to be secured against public internet exposure.
* **Decision:** Provision Cloud SQL strictly with a private IP utilizing VPC Peering. Cloud Run traffic is routed via a Serverless Subnet using Direct VPC Egress (PRIVATE_RANGES_ONLY).
* **Consequences:** The database is invisible to the public internet. Required advanced Terraform orchestration to handle eventual consistency locks during teardown.

## ADR-013: Decoupled CI/CD Pipelines
* **Date:** 2026-07-26
* **Status:** Accepted
* **Context:** Needed automated deployment checks without losing manual control over infrastructure costs.
* **Decision:** Split GitHub Actions into three distinct workflows: PR Validation (automated lint/test/plan), Docker Publish (automated build/push on merge), and Ops Infrastructure Control (manual workflow_dispatch for Terraform apply/destroy).
* **Consequences:** Ensures code quality on every PR while preventing accidental automated scaling or unapproved cloud billing events.
