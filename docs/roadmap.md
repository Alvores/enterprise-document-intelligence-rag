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
- [x] Implement LLM Factory for environment switching (Gemini 3.6 Flash for cloud)
- [x] Implement GitHub Actions CI/CD (PR validation, auto-publish, manual infra control)

## Phase 6: Frontend (Week 6)
- [ ] React SPA
- [ ] PDF upload UI
- [ ] Chat interface
- [ ] Deployment