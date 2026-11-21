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
| **LLM (Dev/Cloud)** | Ollama (qwen3:8b) / Gemini 3.5 Flash-Lite (configurable via LLM_MODEL) | Local zero-cost dev (qwen3:8b) seamlessly transitioning to high-speed cloud generation |
| **Telemetry** | Hugging Face Transformers | Native AutoTokenizers for 100% exact LLMOps token counting; tokenizers baked offline (`/app/models/bge-small-en-v1.5`, `/app/models/qwen3-8b-tokenizer`) with `HF_HUB_OFFLINE=1` on Cloud Run |
| **Evaluation / Observability** | Ragas + Arize Phoenix (OpenTelemetry) | Continuous RAG Triad scoring and self-hosted span tracing instead of binary LLM-judge pass/fail |
| **Async Queue** | GCP Pub/Sub + Cloud Storage | Decouples PDF upload from ingestion; OIDC-authenticated Pub/Sub push (`POST /documents/worker`), 180s ack deadline, 5-attempt DLQ, and `GET /documents/{document_id}` polling |
| **Reranker** | BAAI/bge-reranker-base | Cross-encoder second stage prunes Top-25 hybrid hits to the highest-signal Top-5 |
| **Post-Training** | HF PEFT QLoRA + TRL (SFT/DPO) | Fine-tunes Qwen 8B for inline citations, distractor filtering, and grounded refusals |
| **Inference Server** | vLLM (PagedAttention + prefix caching) | High-throughput serving of the DPO-aligned LoRA adapter with KV-cache reuse |
| **CI/CD** | GitHub Actions | Automated uv linting, testing, and Artifact Registry publishing; manual `Ops: Manual Infra Control` (`apply`) runs Terraform + `gcloud run deploy :latest`, while PR merges (`docker_publish.yml`) build and push only |
| **Logging** | python-json-logger | Structured JSON logs natively parsed by OpenShift/GCP |
| **Infra Local** | Docker & Compose | Containerized for parity, internal DNS routing |
| **Infra Cloud** | Terraform & Cloud Run | Infrastructure as code, serverless auto-scaling, Direct VPC egress; `4096Mi` RAM, `startup_cpu_boost`, and `ENABLE_TELEMETRY=false` on Cloud Run |

## Data Flow

### Current (Phase 7)
PDF → GCS + Pub/Sub Push → PyMuPDF → Sentence-Window Nodes → BGE Embeddings → pgvector
Query → Hybrid Search (Top-25) → Window Expansion + Cross-Encoder Rerank (Top-5) → Ollama qwen3:8b / Gemini 3.5 Flash-Lite → JSON Response + Citations

### Target (Phases 8–10)
PDF → GCS + Pub/Sub Push → PyMuPDF → Sentence-Window Nodes → BGE Embeddings → pgvector
Query → Hybrid Search (Top-25) → Window Expansion + Cross-Encoder Rerank (Top-5) → vLLM (DPO Qwen-8B + Prefix Cache) → SSE Stream

## Status Tracker
- ✅ **Phase 1 (Foundation):** FastAPI, PostgreSQL, pgvector, Logging, Health endpoints
- ✅ **Phase 2 (Ingestion):** PDF upload, PyMuPDF parsing, LlamaIndex pipeline, pgvector persistence
- ✅ **Phase 3 (Retrieval):** Vector query, hybrid search (BM25), LLM synthesis
- ✅ **Phase 4 (Production Readiness):** Golden dataset testing, exact LLMOps telemetry, API Key security, Docker containerization 
- ✅ **Phase 5 (Cloud Deployment):** Serverless architecture via GCP Cloud Run, Private Cloud SQL, and Terraform IaC
- ✅ **v0.2.0 Phase 6 (Evaluation & Tracing):** Ragas RAG Triad metrics, expanded golden dataset, Arize Phoenix spans
- ✅ **v0.2.0 Phase 7 (Async Ingestion & Reranking):** GCS + Pub/Sub ingestion, sentence-window parsing, cross-encoder reranking
- ⏳ **v0.2.0 Phase 8 (Post-Training):** Isolated CUDA workspace, QLoRA SFT, DPO alignment
- ⏳ **v0.2.0 Phase 9 (Serving):** vLLM with PagedAttention and automatic prefix caching
- ⏳ **v0.2.0 Phase 10 (Frontend):** React SPA with SSE token streaming and citations

## Evaluation Benchmarks (Ablation Gates)
| Metric | Gate 0 (Baseline) | Gate 1 (Reranker) |
|--------|-------------------|-------------------|
| Context Precision | 0.7593 | 0.8235 |
| Context Recall | 0.9000 | 0.9500 |
| Faithfulness | 0.9079 | 0.9815 |
| Answer Relevancy | 0.8518 | 0.9182 |

Sources: [`docs/benchmarks/gate_0_baseline.md`](./benchmarks/gate_0_baseline.md), [`docs/benchmarks/gate_1_reranker.md`](./benchmarks/gate_1_reranker.md)

## See Also
- [Architecture Decision Records](./decisions.md)
- [Project Roadmap](./roadmap.md)
