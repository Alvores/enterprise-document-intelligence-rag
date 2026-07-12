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

## Phase 5: Cloud Deployment (Week 5)
- [ ] Provision PostgreSQL Cloud SQL
- [ ] Push Docker container to Google Artifact Registry
- [ ] Deploy API to Google Cloud Run (Serverless)
- [ ] Configure GCP Secret Manager for API Keys

## Phase 6: Frontend (Week 6)
- [ ] React SPA
- [ ] PDF upload UI
- [ ] Chat interface
- [ ] Deployment