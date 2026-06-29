# System Architecture: Enterprise Document Intelligence RAG

## Overview
A production-ready Retrieval-Augmented Generation (RAG) platform built with FastAPI, LlamaIndex, PostgreSQL/pgvector, and Ollama. Designed for local-first development with a direct deployment path to GCP Cloud Run.

## Technology Stack
| Layer | Technology | Justification |
|-------|------------|---------------|
| **API** | FastAPI 0.116 | Modern, async-capable, automatic OpenAPI docs |
| **RAG Core** | LlamaIndex 0.14 | Best-in-class, native structures for document retrieval |
| **Vector DB** | PostgreSQL 16 + pgvector | Enterprise-grade, ACID-compliant, hybrid search ready |
| **Embeddings** | sentence-transformers | Lightweight, local 384-dim embeddings |
| **LLM (Dev)** | Ollama | Local development with zero API costs |
| **Logging** | python-json-logger | Structured JSON logs natively parsed by OpenShift/GCP |
| **Infra** | Docker | Containerized for parity and serverless cloud deployment |

## Data Flow
PDF → PyMuPDF → Chunks → Embeddings → pgvector
Query → Embedding → Hybrid Search → LLM → Answer

## Status Tracker
- ✅ **Phase 1 (Foundation):** FastAPI, PostgreSQL, pgvector, Logging, Health endpoints
- ✅ **Phase 2 (Ingestion):** PDF upload, PyMuPDF parsing, LlamaIndex pipeline, pgvector persistence
- ✅ **Phase 3 (Retrieval):** Vector query, hybrid search (BM25), LLM synthesis
- ⏳ **Phase 4 (Production):** Golden dataset testing, Dockerfile, GCP Cloud Run
- ⏳ **Phase 5 (Frontend):** React SPA UI

## See Also
- [Architecture Decision Records](./decisions.md)
- [Project Roadmap](./roadmap.md)