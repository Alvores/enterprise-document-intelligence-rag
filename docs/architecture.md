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

## Current System State (Phase 1: Foundation)
- ✅ Infrastructure: FastAPI, PostgreSQL, pgvector
- ✅ Health endpoints: `/health`, `/health/db`
- ✅ Structured JSON logging
- ⏳ RAG ingestion: PDF upload + embedding (Week 2)
- ⏳ RAG retrieval: Query + answer (Week 3)
- ⏳ Hybrid search: BM25 + vector (Week 4)
- ⏳ Golden dataset testing (Week 5)
- ⏳ GCP Cloud Run deployment (Phase 3)

## See Also
- [Architecture Decision Records](./decisions.md)
- [Project Roadmap](./roadmap.md)