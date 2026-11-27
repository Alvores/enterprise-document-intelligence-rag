# Dataset Card — Phase 8B Multi-Document RAG Corpus

## Purpose & Design Goals

Phase 8A established the isolated CUDA training workspace. Phase 8B prepares the
**data** that Phase 8C (QLoRA SFT) and Phase 8D (DPO) will consume. We deliberately
train on a **multi-document synthetic RAG corpus with hard distractors** rather than
single chunks or the single `attention_is_all_you_need.pdf` used in earlier phases.

Why:

- **Retrieval realism.** Production queries (`backend/app/rag/retrieval.py`) retrieve
  `TOP_K_RETRIEVAL=25` windows, expand them, and rerank to Top-5. A model trained only
  on gold chunks never learns to ignore near-duplicate distractors that hybrid search
  surfaces from *other* documents.
- **Memorization suppression.** `attention_is_all_you_need.pdf` is a famous paper; a
  base LLM already knows it. We hold it out of train/val entirely so the SFT model must
  learn to answer from *context*, not parametric memory.
- **Grounded refusal.** Unanswerable queries (25% of the SFT mix) teach the exact
  production refusal string rather than hallucinated extrapolation.

## Corpus Provenance & Licensing

Raw PDFs are **gitignored** (`training/data/raw_pdfs/*.pdf`) and fetched reproducibly
via `scripts/fetch_corpus.py`; only the manifest, this card, and `dataset_stats.json`
are tracked. Publication dates are as of the source documents.

| doc_id | Document (date) | License / restrictions | Pages kept | Split |
|---|---|---|---|---|
| `nist_ai_600_1` | NIST AI 600-1: AI RMF Generative AI Profile | US Gov Public Domain (17 U.S.C. § 105) | 5–57 | train |
| `nist_csf_2_0` | NIST CSF 2.0 (CSWP 29) | US Gov Public Domain (17 U.S.C. § 105) | 5–31 | train |
| `fed_mpr_2026_07` | Federal Reserve Monetary Policy Report (July 2026) | US Gov Public Domain — narrative/Fed tables only. **Excludes third-party S&P/ICE/JPM charts (see p. ii); do not redistribute the PDF.** | 9–54, 68–70 | train |
| `dpo_paper_2024` | Direct Preference Optimization (arXiv:2305.18290v3) | CC BY 4.0 (Rafailov et al.) | 1–10, 15–21 | val |
| `fomc_minutes_2026_06` | FOMC Minutes (June 16–17, 2026) | US Gov Public Domain | 2–12 (`stop_marker: "Attendance"`) | test_stress |
| `attention_is_all_you_need` | Attention Is All You Need (arXiv:1706.03762v7) | arXiv non-exclusive license — **held-out benchmark only, never in train/val** | 1–10 | test_held_out |

`keep_pages` ranges are 1-indexed and inclusive. Trims remove covers, TOCs,
bibliographies, chart-only pages, and profanity-heavy appendices (e.g. DPO Appendix D
Reddit samples, pp. 22–27, are excluded). The Fed MPR page ranges skip front matter
(1–8), chart-only SEP Figures 1–5 (55–67), and Source Notes (71–77); the FOMC
`stop_marker` truncates the staff attendance roster that begins on PDF p. 12.

## Split Architecture & Zero-Leakage Guarantee

| Split | Documents | Count | Purpose |
|---|---|---|---|
| `train` | `nist_ai_600_1`, `nist_csf_2_0`, `fed_mpr_2026_07` | 3 | SFT + DPO training |
| `val` | `dpo_paper_2024` | 1 (unseen academic doc) | SFT + DPO validation |
| `test_stress` | `fomc_minutes_2026_06` | 1 (post-cutoff) | Citation & refusal stress test — post-cutoff extraction |
| `test_held_out` | `attention_is_all_you_need` | 1 (memorized) | Memorization-suppression benchmark |

Zero-leakage is enforced structurally: the manifest assigns each `doc_id` to exactly
one `split`, `build_chunks.py` writes split-separated files, and its audit verifies
`zero_doc_id_overlap` across all splits before exiting cleanly. The existing
20-question `backend/tests/test_rag/golden_dataset.json` (built on the Attention paper)
is left untouched and remains the held-out pipeline benchmark; the planned 25–30
question Citation & Refusal Stress Test is split between
`attention_is_all_you_need.pdf` (memorization suppression) and
`fomcminutes20260617.pdf` (post-cutoff extraction).

## Production-Parity Chunking & Hard-Distractor Pipeline

`build_chunks.py` mirrors the serving stack without importing `llama_index`:

1. **Page-level extraction.** PyMuPDF reads only `keep_pages` ranges; `stop_marker`
   truncation applies mid-page.
2. **Chart-noise filter.** Paragraph blocks are dropped if they have `< 20` words or
   `> 45%` standalone numeric/symbol tokens (axis ticks, page furniture), keeping
   narrative prose and structured tables.
3. **Sentence windows.** Text blocks are read with
   `page.get_text("blocks", sort=True)` (text blocks only, `block[6] == 0`) and
   de-hyphenated across PDF line breaks; cleaned text is sentence-split and rolled
   into sliding `±window_size` windows (`window_size=3` -> up to 7 sentences,
   matching LlamaIndex `SentenceWindowNodeParser(window_size=3)` and
   `SENTENCE_WINDOW_SIZE=3` in `backend/app/core/config.py`), recording
   `core_sentence` and `window_text`.
4. **Embedding.** Every window is embedded with `BAAI/bge-small-en-v1.5`
   (`cuda` if available, else `cpu`), normalized.
5. **Hard-distractor mining.** For each anchor, cosine similarity is computed within
   the same `split`. Same-document negatives are preferred, and overlapping windows
   (`|sentence_idx_a - sentence_idx_b| <= 2 * window_size`) are excluded so
   distractors cannot leak the exact gold answer. Up to `num_distractors=4` are stored
   per anchor with `score` and `same_doc` flags.
6. **Position randomization.** Downstream dataset builders shuffle `[Source 1..5]`
   positions so the model cannot key off source order.

## Planned Dataset Volumes & Task Mix

Round 2 (`validate_datasets.py`) will generate the final TRL JSONL records from these
chunk pools using `scripts/prompt_schema.py`. Targets:

**SFT** (~800–1,000 train / ~100–150 val)

| Task | Share |
|---|---|
| Single-hop factual QA | 45% |
| Multi-chunk synthesis | 30% |
| Unanswerable (verbatim refusal) | 25% |

**DPO** (~400–500 train / ~50–75 val)

| Contrast | Share |
|---|---|
| Entity/table conflation | 30% |
| Parametric leakage | 30% |
| Citation defects | 25% |
| False refusal | 15% |

Records use the TRL conversational schemas (`messages` for SFT; `prompt`/`chosen`/
`rejected` for DPO) produced by `build_sft_record` and `build_dpo_record`. Qwen3
`enable_thinking=False` token budgets: `<= 1536` prompt tokens, `<= 2048` total.

## Reproducibility Commands

```bash
cd training
uv sync --group data
uv run --group data python scripts/fetch_corpus.py --write-checksums
uv run --group data python scripts/build_chunks.py --window-size 3 --num-distractors 4 --seed 42
```

Outputs land in `training/data/`: `chunks_train.jsonl`, `chunks_val.jsonl`,
`chunks_test_stress.jsonl`, `chunks_test_held_out.jsonl`, and `dataset_stats.json`.

## Verified Statistics

Placeholder — Round 2's `validate_datasets.py` will populate this section with
post-hoc checks on record counts, task-mix ratios, token budgets, citation formatting,
and cross-split leakage.
