# System Architecture: Enterprise Document Intelligence RAG

## Overview
A production-ready Retrieval-Augmented Generation (RAG) platform built with FastAPI, LlamaIndex, PostgreSQL/pgvector, and Ollama. Designed for local-first development with a direct deployment path to GCP Cloud Run.

## Technology Stack
| Layer | Technology | Justification |
|-------|------------|---------------|
| **API** | FastAPI 0.116 | Modern, async-capable, automatic OpenAPI docs |
| **Security** | FastAPI Security | Native dependency injection for X-API-Key header validation |
| **RAG Core** | LlamaIndex 0.14 | Best-in-class, native structures for document retrieval |
| **Vector DB** | PostgreSQL 16 + pgvector | Enterprise-grade, ACID-compliant, hybrid search ready |
| **Embeddings** | BAAI/bge-small-en-v1.5 | High-performance open-source embedding model with asymmetric query instructions |
| **LLM (Dev)** | Ollama (qwen3:8b) | Local development with zero API costs |
| **Telemetry** | Hugging Face Transformers | Native AutoTokenizers for 100% exact LLMOps token counting |
| **Logging** | python-json-logger | Structured JSON logs natively parsed by OpenShift/GCP |
| **Infra** | Docker & Compose | Containerized for parity, internal DNS routing, and serverless cloud deployment |

## Data Flow
PDF → PyMuPDF → Chunks → Embeddings → pgvector
Query → Embedding → Hybrid Search → LLM → Answer

## Status Tracker
- ✅ **Phase 1 (Foundation):** FastAPI, PostgreSQL, pgvector, Logging, Health endpoints
- ✅ **Phase 2 (Ingestion):** PDF upload, PyMuPDF parsing, LlamaIndex pipeline, pgvector persistence
- ✅ **Phase 3 (Retrieval):** Vector query, hybrid search (BM25), LLM synthesis
- ✅ **Phase 4 (Production Readiness):** Golden dataset testing, exact LLMOps telemetry, API Key security, Docker containerization 
- ⏳ **Phase 5 (Cloud Deployment):** Serverless architecture via GCP Cloud Run and Neon Postgres
- ⏳ **Phase 6 (Frontend):** React SPA UI

## See Also
- [Architecture Decision Records](./decisions.md)
- [Project Roadmap](./roadmap.md)