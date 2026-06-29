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