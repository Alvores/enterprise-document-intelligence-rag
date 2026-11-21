# Project Roadmap

## Phase 1: Foundation (Week 1)
- [x] Repository setup with monorepo structure
- [x] uv environment with pyproject.toml
- [x] PostgreSQL + pgvector (Docker container)
- [x] FastAPI application with health endpoints
- [x] Structured JSON logging
- [x] Database connection pool
- [x] Git workflow (feature branches → PR → merge)

## Phase 2: Document Ingestion (Week 2)
- [X] Ollama installation + qwen3:4b
- [X] PyMuPDF PDF text extraction
- [X] LlamaIndex IngestionPipeline (chunking + embeddings)
- [X] pgvector storage
- [X] POST /documents/upload endpoint
- [X] Error handling + logging

## Phase 3: Retrieval (Week 3)
- [X] Query embedding generation
- [X] pgvector similarity search
- [X] Hybrid search (BM25 + dense)
- [X] POST /query endpoint with citations

## Phase 4: Production Readiness (Week 4)
- [x] API Key Security Header Validation
- [x] Exact LLMOps Telemetry Logging (Hugging Face Native)
- [x] Golden dataset testing (pytest + LLM Judge)
- [x] Automated Database Init Script
- [x] Dockerfile + docker-compose containerization

## Phase 5: Cloud Deployment (Weeks 5-7)
- [x] Infrastructure as Code (Terraform) setup with remote GCS state
- [x] Provision private Cloud SQL (PostgreSQL 16) with VPC Peering
- [x] Push Docker container to Google Artifact Registry
- [x] Deploy API to Google Cloud Run (Serverless) with Direct VPC Egress
- [x] Configure GCP Secret Manager for Database URLs and API Keys
- [x] Implement LLM Factory for environment switching (env-configured Gemini model (default: gemini-3.5-flash-lite))
- [x] Implement GitHub Actions CI/CD (PR validation, auto-publish, manual infra control)

## v0.2.0 Expansion

### Phase 6: Evaluation & Tracing (ADR-014)
- [X] Replace binary LLM judge with continuous Ragas RAG Triad scoring
- [X] Expand golden dataset to 40+ synthetic questions
- [X] Instrument pipeline spans with Arize Phoenix (OpenTelemetry)
- [X] Establish retrieval/generation baseline for ablation gates

### Phase 7: Async Ingestion & Two-Stage Retrieval (ADR-015, ADR-016)
- [x] Stage uploads in GCS and return `202 Accepted`
- [x] Add Pub/Sub push worker with DLQ and `PENDING → READY/FAILED` state tracking
- [x] Replace flat chunking with `SentenceWindowNodeParser`
- [x] Add cross-encoder reranking (Top-25 → Top-5)
- [x] Cloud hardening: OIDC-authenticated worker endpoint, `GET /documents/{document_id}` polling, `4096Mi` Cloud Run memory + `startup_cpu_boost`, offline-baked models/tokenizers (`HF_HUB_OFFLINE=1`), Gate 1 Ragas benchmarking

### Phase 8: Post-Training (ADR-017, ADR-018)
- [ ] Create isolated `training/` CUDA workspace
- [ ] Curate RAG SFT dataset with relevant + distractor chunks
- [ ] Run QLoRA SFT for citation formatting and distractor filtering
- [ ] Run DPO alignment for grounded refusals and hallucination reduction

### Phase 9: High-Throughput Serving (ADR-019)
- [ ] Deploy vLLM with PagedAttention and automatic prefix caching
- [ ] Extend `LLMService` to route to the vLLM endpoint
- [ ] Load the DPO LoRA adapter dynamically

### Phase 10: React SPA & SSE Frontend (ADR-020)
- [ ] React SPA
- [ ] PDF upload UI
- [ ] Chat interface with SSE token streaming and citation delivery
- [ ] Deployment

## Post-v0.2.0 Polish & Performance Backlog
- [ ] Optimize CPU reranker latency on Cloud Run (`cpu = "4"`, tune `TOP_K_RETRIEVAL`, evaluate ONNX/MiniLM, deduplicate overlapping sentence windows)
- [ ] Share a single `HuggingFaceEmbedding` singleton across `IngestionService` and `RetrievalService`
- [ ] Migrate deprecated `llama-index-llms-gemini` to `llama-index-llms-google-genai`