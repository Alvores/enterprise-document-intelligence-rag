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