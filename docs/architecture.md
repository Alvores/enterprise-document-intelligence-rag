# System Architecture: Enterprise Document Intelligence RAG

## Overview
A production-ready Retrieval-Augmented Generation (RAG) platform built with FastAPI, LlamaIndex, PostgreSQL/pgvector, and Ollama. Designed for local-first development with a direct deployment path to GCP Cloud Run.

## Technology Stack
| Layer | Technology | Justification |
|-------|------------|---------------|
| **API** | FastAPI 0.116 | Modern, async-capable, automatic OpenAPI docs |
| **Security** | FastAPI Security | Native dependency injection for X-API-Key header validation; secrets vaulted in GCP |
| **RAG Core** | LlamaIndex 0.14 | Native structures for document retrieval |
| **Vector DB** | PostgreSQL 16 + pgvector | Enterprise-grade, ACID-compliant, private VPC IP, hybrid search ready via pgvector |
| **Embeddings** | BAAI/bge-small-en-v1.5 | High-performance open-source embedding model with asymmetric query instructions |
| **LLM (Dev/Cloud)** | Ollama (qwen3:8b) / Gemini 3.6 Flash | Local zero-cost dev (qwen3:8b) seamlessly transitioning to high-speed cloud generation |
| **Telemetry** | Hugging Face Transformers | Native AutoTokenizers for 100% exact LLMOps token counting |
| **Evaluation / Observability** | Ragas + Arize Phoenix (OpenTelemetry) | Continuous RAG Triad scoring and self-hosted span tracing instead of binary LLM-judge pass/fail |
| **Async Queue** | GCP Pub/Sub + Cloud Storage | Decouples PDF upload from ingestion with retries, DLQ, and scale-to-zero workers |
| **Reranker** | BAAI/bge-reranker-base | Cross-encoder second stage prunes Top-25 hybrid hits to the highest-signal Top-5 |
| **Post-Training** | HF PEFT QLoRA + TRL (SFT/DPO) | Fine-tunes Qwen 8B for inline citations, distractor filtering, and grounded refusals |
| **Inference Server** | vLLM (PagedAttention + prefix caching) | High-throughput serving of the DPO-aligned LoRA adapter with KV-cache reuse |
| **CI/CD** | GitHub Actions | Automated uv linting, testing, and Artifact Registry publishing |
| **Logging** | python-json-logger | Structured JSON logs natively parsed by OpenShift/GCP |
| **Infra Local** | Docker & Compose | Containerized for parity, internal DNS routingt |
| **Infra Cloud** | Terraform & Cloud Run | Infrastructure as code, serverless auto-scaling, and Direct VPC egress routing |

## Data Flow
PDF → GCS + Pub/Sub Push → PyMuPDF → Sentence-Window Nodes → BGE Embeddings → pgvector
Query → Hybrid Search (Top-25) → Window Expansion + Cross-Encoder Rerank (Top-5) → vLLM (DPO Qwen-8B + Prefix Cache) → SSE Stream

## Status Tracker
- ✅ **Phase 1 (Foundation):** FastAPI, PostgreSQL, pgvector, Logging, Health endpoints
- ✅ **Phase 2 (Ingestion):** PDF upload, PyMuPDF parsing, LlamaIndex pipeline, pgvector persistence
- ✅ **Phase 3 (Retrieval):** Vector query, hybrid search (BM25), LLM synthesis
- ✅ **Phase 4 (Production Readiness):** Golden dataset testing, exact LLMOps telemetry, API Key security, Docker containerization 
- ✅ **Phase 5 (Cloud Deployment):** Serverless architecture via GCP Cloud Run, Private Cloud SQL, and Terraform IaC
- ⏳ **v0.2.0 Phase 6 (Evaluation & Tracing):** Ragas RAG Triad metrics, expanded golden dataset, Arize Phoenix spans
- ⏳ **v0.2.0 Phase 7 (Async Ingestion & Reranking):** GCS + Pub/Sub ingestion, sentence-window parsing, cross-encoder reranking
- ⏳ **v0.2.0 Phase 8 (Post-Training):** Isolated CUDA workspace, QLoRA SFT, DPO alignment
- ⏳ **v0.2.0 Phase 9 (Serving):** vLLM with PagedAttention and automatic prefix caching
- ⏳ **v0.2.0 Phase 10 (Frontend):** React SPA with SSE token streaming and citations

## See Also
- [Architecture Decision Records](./decisions.md)
- [Project Roadmap](./roadmap.md)