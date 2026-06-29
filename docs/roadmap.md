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

## Phase 3: Retrieval (Week 3-4)
- [X] Query embedding generation
- [X] pgvector similarity search
- [X] Hybrid search (BM25 + dense)
- [X] POST /query endpoint with citations

## Phase 4: Production Readiness (Week 5-6)
- [ ] Golden dataset testing (pytest)
- [ ] Dockerfile + docker-compose
- [ ] GCP Cloud Run deployment
- [ ] Monitoring + health checks
- [ ] Implement Least Privilege Principal (DB User isolation / IAM Auth)

## Phase 5: Frontend (Week 7)
- [ ] React SPA
- [ ] PDF upload UI
- [ ] Chat interface
- [ ] Deployment