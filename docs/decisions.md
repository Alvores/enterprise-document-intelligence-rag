# Architecture Decision Records (ADRs)

## ADR-001: Monorepo Separation (`backend/` vs `frontend/`)
* **Date:** 2026-06-19
* **Status:** Accepted
* **Context:** Project will eventually include a React SPA alongside the Python API.
* **Decision:** Establish `backend/` and `frontend/` as top-level directories immediately, even though frontend is empty.
* **Consequences:** Prevents `.venv` and `node_modules` dependency clashing and signals full-stack system awareness from Day 1.

## ADR-002: LlamaIndex over LangChain
* **Date:** 2026-06-19
* **Status:** Accepted
* **Context:** Required an orchestration framework for document ingestion and retrieval.
* **Decision:** Use LlamaIndex.
* **Alternatives:** LangChain or LangGraph.
* **Consequences:** Avoided "framework soup." LlamaIndex provides superior native abstractions for a pure RAG data pipeline. Agentic state-machines (LangGraph) were deemed out of scope.

## ADR-003: PostgreSQL + pgvector
* **Date:** 2026-06-19
* **Status:** Accepted
* **Context:** Needed a vector database for embedding storage.
* **Decision:** PostgreSQL with the `pgvector` extension via local Docker.
* **Alternatives:** SaaS vector databases (Pinecone, Weaviate).
* **Consequences:** Single database architecture, guarantees ACID compliance, supports hybrid search (BM25 + dense), and keeps local development cost at $0.

## ADR-004: Package Management via `uv`
* **Date:** 2026-06-19
* **Status:** Accepted
* **Context:** Needed a deterministic, fast Python 3.12 environment manager.
* **Decision:** Use `uv` with `pyproject.toml` and `uv.lock`.
* **Alternatives:** `poetry` (slower, heavier) or standard `pip` (less reproducible).
* **Consequences:** Achieved sub-second dependency resolution and strict lockfile determinism, matching modern CI/CD standards.

## ADR-005: CPU-Only PyTorch for Local Development
* **Date:** 2026-06-19
* **Status:** Accepted
* **Context:** The local machine's RTX 5070 Ti (Blackwell sm_120 architecture) is not yet supported by stable PyTorch CUDA wheels, causing kernel execution errors.
* **Decision:** Fall back to CPU-only execution for `sentence-transformers` rather than debugging nightly PyTorch builds.
* **Consequences:** Embedding generation is slightly slower, but completely unblocks Project 1 development. The GPU is reserved for running Ollama LLMs, where VRAM acceleration is actually mission-critical.

## ADR-006: AI Boundary Mocking for Unit Tests
* **Date:** 2026-06-21
* **Status:** Accepted
* **Context:** Adding `pytest` coverage for the `/documents/upload` API endpoint.
* **Decision:** Use `unittest.mock` to intercept and mock the `IngestionService` during API route testing.
* **Consequences:** Prevents `pytest` from invoking CPU-heavy embedding models or establishing database connections during standard CI/CD runs. Ensures the test suite executes in milliseconds while still validating HTTP boundaries, Pydantic schemas, and error handling.

## ADR-007: Content-Based Deduplication (SHA-256)
* **Date:** 2026-06-21
* **Status:** Accepted
* **Context:** Preventing duplicate embeddings from polluting the vector database and degrading retrieval quality.
* **Decision:** Implemented a SHA-256 hashing mechanism on the raw incoming file bytes.
* **Consequences:** Eliminates redundant compute costs and prevents identical documents (even if renamed) from being embedded twice. Required adding a relational `documents` tracking table alongside the `pgvector` nodes.

## ADR-008: Overriding LLM Refine Prompts
* **Date:** 2026-06-28
* **Status:** Accepted
* **Context:** LlamaIndex automatically chunks large context retrievals and uses a "compact and refine" strategy if the retrieved nodes exceed the LLM's context window.
* **Decision:** Explicitly override both `text_qa_template` and `refine_template` with custom, strict enterprise prompts.
* **Consequences:** Prevents the framework from falling back to generic default prompts during multi-chunk refinement, guaranteeing the LLM strictly adheres to "only answer from context" rules across all pagination loops.

## ADR-009: Asymmetric Embedding Query Instructions
* **Date:** 2026-07-05
* **Status:** Accepted
* **Context:** The `BAAI/bge-small-en-v1.5` model requires specific instruction prefixes for query embeddings to maintain high cosine similarity scores during retrieval.
* **Decision:** Hardcode the `query_instruction` parameter directly into the `HuggingFaceEmbedding` initialization.
* **Consequences:** Ensures accurate chunk retrieval without permanently appending the prompt to the stored document vectors.

## ADR-010: Native Transformers for Exact Token Telemetry
* **Date:** 2026-07-05
* **Status:** Accepted
* **Context:** Required accurate token counting for LLMOps telemetry. Proxy tokenizers like `tiktoken` can notably miscalculate open-source model chunk boundaries.
* **Decision:** Import `AutoTokenizer` directly from the Hugging Face `transformers` library, utilizing the exact vocabularies of the BGE and Qwen models.
* **Consequences:** Provides 100% precise token usage logging for both embeddings and generations without relying on inaccurate OpenAI approximations.

## ADR-011: LLM Environment Splitting (Factory Pattern)
* **Date:** 2026-07-26
* **Status:** Accepted
* **Context:** Ollama runs locally but cannot run inside a standard serverless Cloud Run container.
* **Decision:** Implement an LLMFactory that dynamically instantiates Ollama if running locally, or Gemini 3.6 Flash if a GEMINI_API_KEY (mapped from Secret Manager) is detected.
* **Consequences:** Achieved parity between a $0 local dev environment and a high-availability, high-speed cloud runtime without modifying core retrieval logic.

## ADR-012: Zero-Trust Database Networking
* **Date:** 2026-07-26
* **Status:** Accepted
* **Context:** The PostgreSQL database containing raw enterprise documents needed to be secured against public internet exposure.
* **Decision:** Provision Cloud SQL strictly with a private IP utilizing VPC Peering. Cloud Run traffic is routed via a Serverless Subnet using Direct VPC Egress (PRIVATE_RANGES_ONLY).
* **Consequences:** The database is invisible to the public internet. Required advanced Terraform orchestration to handle eventual consistency locks during teardown.

## ADR-013: Decoupled CI/CD Pipelines
* **Date:** 2026-07-26
* **Status:** Accepted
* **Context:** Needed automated deployment checks without losing manual control over infrastructure costs.
* **Decision:** Split GitHub Actions into three distinct workflows: PR Validation (automated lint/test/plan), Docker Publish (automated build/push on merge), and Ops Infrastructure Control (manual workflow_dispatch for Terraform apply/destroy).
* **Consequences:** Ensures code quality on every PR while preventing accidental automated scaling or unapproved cloud billing events.

## ADR-014: Quantitative RAG Triad Evaluation & OpenTelemetry Tracing
* **Date:** 2026-11-10
* **Status:** Accepted
* **Context:** The initial evaluation suite (`test_rag_evaluation.py`) relies on a 3-question `GOLDEN_DATASET` evaluated by a binary `PASS/FAIL` LLM judge, while telemetry (`ADR-010`) only captures coarse token counters. A binary pass/fail grade cannot isolate whether retrieval failed to surface relevant chunks or generation suffered from parametric hallucination, nor can it quantify marginal improvements from reranking or model fine-tuning.
* **Decision:** Replace binary judge evaluations with continuous **RAG Triad** scoring (**Context Precision**, **Context Recall**, **Faithfulness**, and **Answer Relevance**) using **Ragas** across an expanded 40+ synthetic golden evaluation set, and instrument full execution spans via **Arize Phoenix (OpenTelemetry)**.
* **Alternatives:** Custom binary LLM-as-a-judge heuristics (lacks multi-variable granularity) or proprietary SaaS platforms like LangSmith (introduces commercial vendor lock-in and external data egress).
* **Consequences:** Provides reproducible numerical baselines to validate each architectural transition (Baseline → Reranker → SFT → DPO) while maintaining an open-source, self-hostable telemetry stack.

## ADR-015: Asynchronous Event-Driven Ingestion via GCS & Cloud Pub/Sub Push
* **Date:** 2026-11-10
* **Status:** Accepted
* **Context:** The synchronous `POST /documents/upload` endpoint performs PyMuPDF text parsing, chunking, and CPU-bound embedding generation within the client HTTP request lifecycle. Processing large multi-page enterprise documents blocks API worker threads, risks Cloud Run HTTP 504 gateway timeouts, and drops jobs if transient database connection drops occur.
* **Decision:** Decouple document upload from document ingestion using **Google Cloud Storage (GCS)** staging and **Cloud Pub/Sub Push Subscriptions** with a Dead-Letter Queue (DLQ). The upload endpoint computes the SHA-256 digest (`ADR-007`), stages the binary to GCS, writes a `PENDING` record to PostgreSQL, publishes a message to Pub/Sub, and immediately returns `202 Accepted`. A dedicated push endpoint (`POST /documents/worker`) consumes the event, executes the ingestion pipeline, and updates document state to `READY` or `FAILED`.
* **Alternatives:** FastAPI `BackgroundTasks` (unreliable under serverless scale-down because Cloud Run throttles CPU after request termination) or Celery + Redis (requires provisioning always-on infrastructure, violating serverless scale-to-zero objectives).
* **Consequences:** Ensures sub-second client response times, offloads CPU-heavy extraction to managed background execution, enables automated exponential backoff retries with DLQ isolation, and guarantees idempotency through content-addressable SHA-256 digests.

## ADR-016: Two-Stage Retrieval with Sentence-Window Parsing & Cross-Encoder Reranking
* **Date:** 2026-11-10
* **Status:** Accepted
* **Context:** The baseline retrieval strategy uses flat 512-token chunks (`SentenceSplitter`) and retrieves `TOP_K_RETRIEVAL = 5` via hybrid dense + BM25 search (`alpha = 0.7`). Large fixed chunks dilute specific facts across bi-encoder vector projections (`bge-small-en-v1.5`), while small fixed chunks sever essential surrounding context. Furthermore, bi-encoders evaluate query-document similarity via decoupled dot products, which miss token-level interactions.
* **Decision:** Transition to a two-stage retrieval pipeline in LlamaIndex (`ADR-002`):
  1. Parse documents using `SentenceWindowNodeParser`, embedding granular single sentences for high-precision semantic matching while preserving a ±3 sentence window in metadata.
  2. Broaden initial hybrid retrieval to `similarity_top_k = 25`, expand surrounding context using `MetadataReplacementPostProcessor`, and execute a second-stage **Cross-Encoder Reranker** (`SentenceTransformerRerank` using `BAAI/bge-reranker-base`) to score joint query-document representations and prune candidates down to the Top-5 nodes.
* **Alternatives:** Increasing top-k retrieval without reranking (pollutes the prompt with low-similarity distractors and induces token bloat).
* **Consequences:** Substantially elevates Context Recall and Precision without overflowing the downstream generator's context window. Increases second-stage compute latency, which is compensated for by higher synthesis quality.

## ADR-017: Isolated CUDA Training Workspace vs. CPU-Only API Runtime
* **Date:** 2026-11-10
* **Status:** Accepted
* **Context:** `ADR-005` pins PyTorch to the `pytorch-cpu` wheel index in `pyproject.toml` to maintain a lightweight Cloud Run deployment and sidestep local driver/kernel constraints. However, fine-tuning and alignment (QLoRA, SFT, DPO) require GPU-accelerated libraries including `torch` (CUDA), `trl`, `peft`, `bitsandbytes`, and `accelerate`.
* **Decision:** Isolate all model post-training and dataset generation scripts into a distinct top-level `training/` workspace with an independent `pyproject.toml` and lockfile, completely separate from the production `backend/` runtime.
* **Alternatives:** Incorporating training packages into the root environment (bloats the production container image by >8GB and breaks CPU-only CI pipelines in GitHub Actions).
* **Consequences:** Preserves minimal, sub-second deployable container artifacts for the serving runtime while providing an unconstrained CUDA environment for distributed or spot-instance training runs.

## ADR-018: Parameter-Efficient Post-Training via QLoRA (SFT) & Direct Preference Optimization (DPO)
* **Date:** 2026-11-10
* **Status:** Accepted
* **Context:** The system currently relies on prompt engineering (`RAG_SYSTEM_TEMPLATE`, `ADR-008`) to constrain the LLM to context-only synthesis and strict citations. In production testing, general-purpose instruction models frequently fail to output standardized citation keys, struggle to filter irrelevant distractor chunks, and hallucinate answers to unanswerable queries rather than executing structured refusals.
* **Decision:** Implement a two-stage parameter-efficient post-training workflow targeting the base Qwen 8B model:
  1. **Supervised Fine-Tuning (`SFTTrainer` + QLoRA, $r=16, \alpha=32$):** Train on RAG triplets containing target context alongside distractor nodes to enforce inline `[doc_id]` citation syntax and context filtering.
  2. **Direct Preference Optimization (`DPOTrainer`, $\beta=0.1$):** Align the adapter using pairwise preference data—rewarding answers strictly grounded in retrieved evidence and penalizing parametric knowledge leakage and over-extrapolation.
* **Alternatives:** Full-parameter fine-tuning (prohibitive compute cost and adapter portability overhead) or Reinforcement Learning from Human Feedback via PPO (requires unstable dual-model actor-critic loops and reward model hosting).
* **Consequences:** Produces a portable (~60MB) adapter exhibiting high Faithfulness and reliable citation compliance, eliminating reliance on brittle system prompt instructions.

## ADR-019: High-Throughput Inference via vLLM with Automatic Prefix Caching & Dynamic LoRA
* **Date:** 2026-11-10
* **Status:** Accepted
* **Context:** Serving the fine-tuned adapter under concurrent enterprise load requires high GPU throughput. Standard Hugging Face inference loops suffer from KV-cache memory fragmentation and lack continuous batching. Furthermore, multi-turn RAG queries repeatedly transmit invariant system instructions (`RAG_SYSTEM_TEMPLATE`) and shared document chunks, incurring redundant prefill computations.
* **Decision:** Deploy **vLLM** as an OpenAI-compatible inference service with `--enable-lora` and `--enable-prefix-caching`, updating `LLMService` (`ADR-011`) to route requests to this endpoint. Prompts are formatted such that static system directives and retrieved chunks precede dynamic user queries, ensuring shared token sequences match the prefix cache.
* **Alternatives:** Hugging Face text-generation-inference (TGI) or merging weights for Ollama (GGUF formats lack flexible runtime switching between departmental LoRA adapters on a single base model).
* **Consequences:** PagedAttention prevents KV-cache fragmentation during high concurrency, while Automatic Prefix Caching reduces Time-To-First-Token (TTFT) by reusing precomputed KV blocks for overlapping context windows.

## ADR-020: Server-Sent Events (SSE) over WebSockets for Token Streaming & Citations
* **Date:** 2026-11-10
* **Status:** Accepted
* **Context:** The API returns a monolithic `QueryResponse` JSON object only after full sequence generation completes, creating 2–5 seconds of perceived user latency. The React single-page application (`frontend/`) requires immediate visual confirmation of retrieval and incremental text generation.
* **Decision:** Expose a `POST /query/stream` endpoint using FastAPI's `StreamingResponse` configured for **Server-Sent Events (`text/event-stream`)**. The stream transmits an initial `citations` event containing reranked source nodes immediately following retrieval, followed by incremental `token` text deltas, concluding with a `telemetry` event.
* **Alternatives:** WebSockets (introduces stateful connection management, complicates horizontal autoscaling on serverless infrastructure, and introduces unnecessary bi-directional protocol overhead for what is strictly a server-to-client stream).
* **Consequences:** Reduces perceived end-user latency to the initial Time-To-First-Token (<500ms) while keeping API endpoints stateless and fully compatible with Cloud Run load balancers and reverse proxies.