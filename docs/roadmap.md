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
- [ ] Ollama installation + qwen3:4b
- [ ] PyMuPDF PDF text extraction
- [ ] LlamaIndex IngestionPipeline (chunking + embeddings)
- [ ] pgvector storage
- [ ] POST /documents/upload endpoint
- [ ] Error handling + logging

## Phase 3: Retrieval (Week 3-4)
- [ ] Query embedding generation
- [ ] pgvector similarity search
- [ ] Hybrid search (BM25 + dense)
- [ ] POST /query endpoint with citations

## Phase 4: Production Readiness (Week 5-6)
- [ ] Golden dataset testing (pytest)
- [ ] Dockerfile + docker-compose
- [ ] GCP Cloud Run deployment
- [ ] Monitoring + health checks

## Phase 5: Frontend (Week 7)
- [ ] React SPA
- [ ] PDF upload UI
- [ ] Chat interface
- [ ] Deployment