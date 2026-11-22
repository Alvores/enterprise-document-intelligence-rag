# Training Workspace (Phase 8A)

Isolated CUDA post-training workspace for the Enterprise Document Intelligence RAG
platform. This directory fine-tunes and aligns Qwen3-8B for citation-accurate,
distraction-resilient RAG synthesis (ADR-017, ADR-018).

## Why this is isolated

`training/` is a standalone `uv` project with its own `pyproject.toml` and lockfile
(ADR-017). The production `backend/` runtime is pinned to CPU-only PyTorch to keep the
Cloud Run image lightweight (ADR-005); the CUDA toolchain plus `trl`, `peft`, and
`bitsandbytes` required here would bloat that image by >8 GB and break the CPU-only CI
pipeline. Never import `training/` from `backend/` or add its dependencies to the root
`pyproject.toml`.

## Prerequisites (WSL2)

- NVIDIA driver with CUDA 13.x support (Blackwell `sm_120`).
- Confirm the GPU is visible inside WSL2:

```bash
nvidia-smi
```

If `nvidia-smi` fails, reinstall the Windows NVIDIA driver (WSL2 uses the host driver).
No container runtime is needed for plain WSL2 CUDA.

## Install

```bash
cd training
uv sync          # creates training/.venv with CUDA 13.2 PyTorch
```

The PyTorch wheels are pulled from the explicit `pytorch-cu132` index configured in
`pyproject.toml`.

## Verify the environment

```bash
uv run python scripts/verify_cuda.py
```

This gate checks package versions, CUDA availability and `sm_120` support, a bfloat16
GEMM, and a bitsandbytes 4-bit NF4 QLoRA forward/backward. Exit code 0 means the
workspace is ready.

## VRAM budget (16 GB GPUs, e.g. RTX 5070 Ti)

| Component | Approx. |
|-----------|---------|
| Qwen3-8B in 4-bit NF4 | ~5 GB |
| LoRA adapters + activations (seq len 2048) | ~4-6 GB |
| Optimizer states (paged_adamw_8bit) | ~1-2 GB |
| Headroom | remaining |

`batch_size=1` plus `gradient_accumulation_steps=8` keeps activation memory within a
16 GB budget; paged 8-bit Adam offloads optimizer state to CPU. If OOM occurs, reduce
`max_length` (2048 -> 1536) before touching batch size.

## Workflow

1. Curate `data/sft_train.jsonl` / `data/sft_val.jsonl` (RAG triplets: question,
   relevant chunks, distractor chunks, cited answer).
2. Run SFT (`configs/sft_qwen3_8b.yaml`) -> `artifacts/qwen3-8b-rag-sft`.
3. Curate `data/dpo_train.jsonl` / `data/dpo_val.jsonl` (chosen vs rejected pairs).
4. Run DPO (`configs/dpo_qwen3_8b.yaml`) -> `artifacts/qwen3-8b-rag-dpo`.
