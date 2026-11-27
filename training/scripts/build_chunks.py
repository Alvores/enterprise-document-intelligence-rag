"""Build deterministic, retrieval-realistic chunk pools for all Phase 8B splits.

Reads ``training/data/corpus_manifest.yaml``, extracts text page-by-page with
PyMuPDF within each document's ``keep_pages`` ranges (honouring ``stop_marker``),
filters chart/axis noise, splits cleaned text into sliding ``window_size``
sentence windows, embeds them with ``BAAI/bge-small-en-v1.5``, and mines hard
distractors per split.

Outputs ``chunks_{split}.jsonl`` and ``dataset_stats.json`` under
``training/data/``.
"""

import argparse
import json
import random
import re
import sys
import unicodedata
from datetime import UTC, datetime
from pathlib import Path

import fitz
import numpy as np
import yaml
from sentence_transformers import SentenceTransformer

TRAINING_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = TRAINING_ROOT / "data" / "corpus_manifest.yaml"
DEFAULT_OUTPUT_DIR = TRAINING_ROOT / "data"
RAW_PDFS_DIR = TRAINING_ROOT / "data" / "raw_pdfs"
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"

SPLITS = ("train", "val", "test_stress", "test_held_out")

_MIN_WORDS = 15
_MAX_NUMERIC_RATIO = 0.45
_STAGE_A_MIN_WORD_TOKENS = 2

_BLOCK_VGAP_MAX = 18.0
_BLOCK_LEFT_DELTA_MAX = 40.0
_BLOCK_RIGHT_DELTA_MAX = 180.0

_COMPOUND_PREFIXES = frozenset(
    {
        "e",
        "co",
        "non",
        "pre",
        "post",
        "sub",
        "semi",
        "inter",
        "intra",
        "multi",
        "cross",
        "self",
    }
)

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\u201c\u2018])")
_LIST_MARKER_RE = re.compile(r"(?<!\w)(\d{1,3})\.(?=\s)")
_LIST_ITEM_RE = re.compile(r"^\d{1,3}\.\s*\S")
_PLACEHOLDER = "\ue000"

_ABBREVIATION_RES = [
    re.compile(r"\bEq\."),
    re.compile(r"\bSec\."),
    re.compile(r"\bFig\."),
    re.compile(r"\bApp\."),
    re.compile(r"\bNo\."),
    re.compile(r"\bvs\."),
    re.compile(r"\bi\.e\."),
    re.compile(r"\be\.g\."),
    re.compile(r"\bet\s+al\."),
    re.compile(r"\bU\.S\."),
    re.compile(r"\bU\.K\."),
    re.compile(r"\bp\."),
    re.compile(r"\bpp\."),
]


def count_words(text: str) -> int:
    """Count whitespace-separated tokens that contain at least one alphabetic char."""
    return sum(1 for token in text.split() if any(ch.isalpha() for ch in token))


def numeric_ratio(text: str) -> float:
    """Fraction of whitespace-separated tokens with no alphabetic character."""
    tokens = text.split()
    if not tokens:
        return 0.0
    return 1.0 - (count_words(text) / len(tokens))


def is_noise_block(block: str) -> bool:
    """Drop prose-sparse or number-heavy blocks (chart axis labels, page furniture)."""
    if not block.split():
        return True
    return count_words(block) < _MIN_WORDS or numeric_ratio(block) > _MAX_NUMERIC_RATIO


def dehyphenate(text: str) -> str:
    """Join line-wrap hyphens while preserving genuine compound hyphens."""

    def _repl(match: re.Match[str]) -> str:
        prefix = match.group(1)
        if prefix in _COMPOUND_PREFIXES or (prefix and prefix[0].isupper()):
            return f"{prefix}-{match.group(2)}"
        return f"{prefix}{match.group(2)}"

    return re.sub(r"(\w+)-\n([a-z])", _repl, text)


def _protect(text: str) -> str:
    """Hide list-marker and abbreviation periods so the sentence splitter skips them."""
    text = _LIST_MARKER_RE.sub(lambda match: match.group(0).replace(".", _PLACEHOLDER), text)
    for pattern in _ABBREVIATION_RES:
        text = pattern.sub(lambda match: match.group(0).replace(".", _PLACEHOLDER), text)
    return text


def _restore(text: str) -> str:
    return text.replace(_PLACEHOLDER, ".")


def _is_fragment(sentence: str) -> bool:
    """True for a sub-4-word fragment that is not a numbered list item."""
    if count_words(sentence) >= 4:
        return False
    return not _LIST_ITEM_RE.match(sentence)


def _merge_tiny_fragments(sentences: list[str]) -> list[str]:
    """Merge sub-4-word fragments (e.g. 'Left.', 'Right.', '4.') into a neighbour."""
    merged: list[str] = []
    for sentence in sentences:
        if _is_fragment(sentence) and merged:
            merged[-1] = f"{merged[-1]} {sentence}"
        else:
            merged.append(sentence)
    if len(merged) > 1 and _is_fragment(merged[0]):
        merged[1] = f"{merged[0]} {merged[1]}"
        merged = merged[1:]
    return merged


def split_sentences(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    protected = _protect(text)
    parts = [part.strip() for part in _SENTENCE_SPLIT.split(protected) if part.strip()]
    parts = [_restore(part) for part in parts]
    return _merge_tiny_fragments(parts)


def page_is_kept(page_index: int, keep_pages: list[list[int]]) -> bool:
    for start, end in keep_pages:
        if start - 1 <= page_index <= end - 1:
            return True
    return False


def pick_device() -> str:
    try:
        import torch
    except Exception:
        return "cpu"
    return "cuda" if torch.cuda.is_available() else "cpu"


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    try:
        import torch

        torch.manual_seed(seed)
    except Exception:
        pass


def resolve_pdf(manifest_dir: Path, entry: dict) -> Path:
    local_path = entry.get("local_path")
    if local_path:
        return (manifest_dir / local_path).resolve()
    return (RAW_PDFS_DIR / entry["filename"]).resolve()


def merge_blocks(
    blocks: list[tuple[float, float, float, float, str]],
) -> list[list[tuple[float, float, float, float, str]]]:
    """Stitch vertically adjacent single-line blocks into paragraphs."""
    paragraphs: list[list[tuple[float, float, float, float, str]]] = []
    if not blocks:
        return paragraphs
    current = [blocks[0]]
    prev = blocks[0]
    for block in blocks[1:]:
        x0, y0, x1, _y1, _text = block
        px0, _py0, px1, py1, _ptext = prev
        vertical_gap = y0 - py1
        left_close = abs(x0 - px0) <= _BLOCK_LEFT_DELTA_MAX
        same_column = abs(x1 - px1) <= _BLOCK_RIGHT_DELTA_MAX or x0 >= px0 - _BLOCK_LEFT_DELTA_MAX
        if vertical_gap <= _BLOCK_VGAP_MAX and left_close and same_column:
            current.append(block)
        else:
            paragraphs.append(current)
            current = [block]
        prev = block
    paragraphs.append(current)
    return paragraphs


def extract_sentences(
    doc: fitz.Document,
    entry: dict,
) -> tuple[list[str], list[int], dict]:
    keep_pages = entry["keep_pages"]
    stop_marker = entry.get("stop_marker")

    sentences: list[str] = []
    pages: list[int] = []
    pages_kept = 0
    raw_blocks = 0
    noise_blocks = 0
    stopped = False

    for page_index in range(doc.page_count):
        if not page_is_kept(page_index, keep_pages):
            continue
        page_num = page_index + 1

        # Stage A: keep prose-bearing text blocks, dropping obvious fragments.
        surviving: list[tuple[float, float, float, float, str]] = []
        for block in doc[page_index].get_text("blocks", sort=True):
            if block[6] != 0:
                continue
            block_text = block[4]
            if stop_marker and stop_marker in block_text:
                block_text = block_text.split(stop_marker, 1)[0]
                stopped = True
            block_text = block_text.strip()
            if not block_text:
                if stopped:
                    break
                continue
            raw_blocks += 1
            if (
                numeric_ratio(block_text) > _MAX_NUMERIC_RATIO
                or count_words(block_text) < _STAGE_A_MIN_WORD_TOKENS
            ):
                noise_blocks += 1
                if stopped:
                    break
                continue
            surviving.append((block[0], block[1], block[2], block[3], block_text))
            if stopped:
                break

        # Stage B: stitch blocks into paragraphs; Stage C: de-hyphenate, NFKC,
        # then apply the paragraph-level noise check.
        for group in merge_blocks(surviving):
            paragraph = "\n".join(block[4] for block in group)
            paragraph = dehyphenate(paragraph)
            paragraph = unicodedata.normalize("NFKC", paragraph).strip()
            if not paragraph:
                continue
            if is_noise_block(paragraph):
                noise_blocks += len(group)
                continue
            for sentence in split_sentences(paragraph):
                sentences.append(sentence)
                pages.append(page_num)

        pages_kept += 1
        if stopped:
            break

    audit = {
        "pages_kept": pages_kept,
        "raw_blocks": raw_blocks,
        "noise_blocks": noise_blocks,
    }
    return sentences, pages, audit


def build_windows(
    sentences: list[str],
    pages: list[int],
    doc_id: str,
    split: str,
    window_size: int,
) -> list[dict]:
    windows: list[dict] = []
    total = len(sentences)
    for index in range(total):
        start = max(0, index - window_size)
        end = min(total, index + window_size + 1)
        windows.append(
            {
                "chunk_id": f"{doc_id}:{index:06d}",
                "doc_id": doc_id,
                "split": split,
                "page": pages[index],
                "sentence_idx": index,
                "core_sentence": sentences[index],
                "window_text": " ".join(sentences[start:end]),
            }
        )
    return windows


def mine_distractors(
    records: list[dict],
    embeddings: np.ndarray,
    num_distractors: int,
    window_size: int,
) -> None:
    similarity = embeddings @ embeddings.T
    doc_ids = [record["doc_id"] for record in records]
    sentence_idx = [record["sentence_idx"] for record in records]

    for anchor in range(len(records)):
        same_doc: list[int] = []
        cross_doc: list[int] = []
        for candidate in range(len(records)):
            if candidate == anchor:
                continue
            if doc_ids[candidate] == doc_ids[anchor]:
                if abs(sentence_idx[candidate] - sentence_idx[anchor]) <= 2 * window_size:
                    continue
                same_doc.append(candidate)
            else:
                cross_doc.append(candidate)

        same_doc.sort(key=lambda j: -similarity[anchor, j])
        cross_doc.sort(key=lambda j: -similarity[anchor, j])

        picks = same_doc[:num_distractors]
        picks.extend(cross_doc[: max(0, num_distractors - len(picks))])

        records[anchor]["distractors"] = [
            {
                "chunk_id": records[j]["chunk_id"],
                "doc_id": records[j]["doc_id"],
                "page": records[j]["page"],
                "sentence_idx": records[j]["sentence_idx"],
                "score": float(similarity[anchor, j]),
                "same_doc": doc_ids[j] == doc_ids[anchor],
            }
            for j in picks
        ]


def percentile_stats(values: list[int]) -> dict:
    if not values:
        return {"median_words": 0.0, "p95_words": 0.0}
    arr = np.asarray(values, dtype=np.float64)
    return {
        "median_words": float(np.median(arr)),
        "p95_words": float(np.percentile(arr, 95)),
    }


def verify_no_leakage(split_records: dict[str, list[dict]]) -> bool:
    seen: dict[str, str] = {}
    overlap = False
    for split, records in split_records.items():
        for record in records:
            doc_id = record["doc_id"]
            if doc_id in seen and seen[doc_id] != split:
                overlap = True
            seen[doc_id] = split
    return not overlap


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build Phase 8B retrieval chunk pools.")
    parser.add_argument(
        "--manifest",
        default=str(DEFAULT_MANIFEST),
        help="Path to the corpus manifest.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory for the split JSONL files and stats.",
    )
    parser.add_argument("--window-size", type=int, default=3, help="Sentences per window.")
    parser.add_argument(
        "--num-distractors",
        type=int,
        default=4,
        help="Hard distractors mined per anchor window.",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility.")
    args = parser.parse_args(argv)

    set_seed(args.seed)

    manifest_path = Path(args.manifest)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    documents = manifest.get("documents", {})
    manifest_dir = manifest_path.resolve().parent

    device = pick_device()
    print(f"Embedding device: {device}")
    model = SentenceTransformer(EMBEDDING_MODEL, device=device)

    split_records: dict[str, list[dict]] = {split: [] for split in SPLITS}
    document_stats: dict[str, dict] = {}

    for doc_id, entry in documents.items():
        pdf_path = resolve_pdf(manifest_dir, entry)
        with fitz.open(pdf_path) as doc:
            sentences, pages, audit = extract_sentences(doc, entry)
        windows = build_windows(
            sentences,
            pages,
            doc_id,
            entry["split"],
            args.window_size,
        )
        split_records[entry["split"]].extend(windows)
        word_counts = [count_words(window["window_text"]) for window in windows]
        document_stats[doc_id] = {
            "split": entry["split"],
            "pages_kept": audit["pages_kept"],
            "raw_blocks": audit["raw_blocks"],
            "noise_blocks_dropped": audit["noise_blocks"],
            "windows": len(windows),
            **percentile_stats(word_counts),
        }

    split_stats: dict[str, dict] = {}
    for split in SPLITS:
        records = split_records[split]
        if not records:
            split_stats[split] = {
                "documents": [],
                "windows": 0,
                "median_words": 0.0,
                "p95_words": 0.0,
            }
            continue
        texts = [record["window_text"] for record in records]
        embeddings = np.asarray(
            model.encode(
                texts,
                batch_size=32,
                show_progress_bar=False,
                normalize_embeddings=True,
                convert_to_numpy=True,
            ),
            dtype=np.float32,
        )
        mine_distractors(records, embeddings, args.num_distractors, args.window_size)

        output_path = output_dir / f"chunks_{split}.jsonl"
        with output_path.open("w", encoding="utf-8") as handle:
            for record in records:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")

        word_counts = [count_words(record["window_text"]) for record in records]
        split_stats[split] = {
            "documents": sorted({record["doc_id"] for record in records}),
            "windows": len(records),
            **percentile_stats(word_counts),
        }

    no_leakage = verify_no_leakage(split_records)

    stats = {
        "generated": datetime.now(UTC).isoformat(),
        "embedding_model": EMBEDDING_MODEL,
        "window_size": args.window_size,
        "num_distractors": args.num_distractors,
        "seed": args.seed,
        "zero_doc_id_overlap": no_leakage,
        "documents": document_stats,
        "splits": split_stats,
    }
    stats_path = output_dir / "dataset_stats.json"
    stats_path.write_text(json.dumps(stats, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("\n=== Per-document audit ===")
    print(f"{'document':24s} {'split':13s} {'pages':>5s} {'raw':>6s} {'noise':>6s} {'wins':>7s}")
    for doc_id, entry in document_stats.items():
        print(
            f"{doc_id:24s} {entry['split']:13s} {entry['pages_kept']:5d} "
            f"{entry['raw_blocks']:6d} {entry['noise_blocks_dropped']:6d} "
            f"{entry['windows']:7d}"
        )

    print("\n=== Per-split audit ===")
    print(f"{'split':16s} {'docs':>4s} {'windows':>7s} {'median':>7s} {'p95':>7s}")
    for split in SPLITS:
        entry = split_stats[split]
        print(
            f"{split:16s} {len(entry['documents']):4d} {entry['windows']:7d} "
            f"{entry['median_words']:7.1f} {entry['p95_words']:7.1f}"
        )

    print(f"\nZero doc_id overlap across splits: {'OK' if no_leakage else 'FAILED'}")
    print(f"Wrote stats to {stats_path}")

    return 0 if no_leakage else 1


if __name__ == "__main__":
    sys.exit(main())
