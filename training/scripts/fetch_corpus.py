"""Download and verify the Phase 8B training corpus.

Reads ``training/data/corpus_manifest.yaml`` and, for every document without a
``local_path`` override, downloads the PDF into ``training/data/raw_pdfs/`` if it is
not already present. It then computes the SHA-256 digest, verifies it against the
manifest when a digest is recorded, and confirms each PDF opens with PyMuPDF.

Examples:
    uv run --group data python scripts/fetch_corpus.py
    uv run --group data python scripts/fetch_corpus.py --write-checksums
"""

import argparse
import hashlib
import sys
from pathlib import Path

import fitz
import httpx
import yaml

TRAINING_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = TRAINING_ROOT / "data" / "corpus_manifest.yaml"
DEFAULT_OUTPUT_DIR = TRAINING_ROOT / "data" / "raw_pdfs"
USER_AGENT = "enterprise-rag-training/0.1 (Phase 8B corpus fetcher)"
_CHUNK_SIZE = 65536


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(_CHUNK_SIZE), b""):
            digest.update(block)
    return digest.hexdigest()


def download(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with httpx.Client(
        follow_redirects=True,
        headers={"User-Agent": USER_AGENT},
        timeout=60.0,
    ) as client:
        with client.stream("GET", url) as response:
            response.raise_for_status()
            with destination.open("wb") as handle:
                for chunk in response.iter_bytes():
                    handle.write(chunk)


def resolve_source_path(manifest_dir: Path, entry: dict, output_dir: Path) -> Path:
    local_path = entry.get("local_path")
    if local_path:
        return (manifest_dir / local_path).resolve()
    return (output_dir / entry["filename"]).resolve()


def write_checksums(manifest_path: Path, checksums: dict[str, str]) -> None:
    """Update ``sha256`` fields in-place, preserving the manifest's structure."""
    current_doc: str | None = None
    updated: list[str] = []
    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("  ") and not line.startswith("    ") and line.rstrip().endswith(":"):
            current_doc = line.strip()[:-1]
        if current_doc and current_doc in checksums and line.strip().startswith("sha256:"):
            indent = line[: len(line) - len(line.lstrip())]
            line = f"{indent}sha256: {checksums[current_doc]}"
        updated.append(line)
    manifest_path.write_text("\n".join(updated) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Download and verify the Phase 8B corpus.")
    parser.add_argument(
        "--manifest",
        default=str(DEFAULT_MANIFEST),
        help="Path to the corpus manifest.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory for downloaded PDFs.",
    )
    parser.add_argument(
        "--write-checksums",
        action="store_true",
        help="Record verified SHA-256 digests back into the manifest.",
    )
    args = parser.parse_args(argv)

    manifest_path = Path(args.manifest)
    output_dir = Path(args.output_dir)
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    documents = manifest.get("documents", {})
    manifest_dir = manifest_path.resolve().parent

    checksums: dict[str, str] = {}
    failures: list[str] = []

    for doc_id, entry in documents.items():
        source = resolve_source_path(manifest_dir, entry, output_dir)
        try:
            if entry.get("local_path") is None and not source.exists():
                print(f"[download] {doc_id} -> {source.name}")
                download(entry["url"], source)
            if not source.exists():
                raise FileNotFoundError(f"local file not found: {source}")

            digest = sha256_of(source)
            checksums[doc_id] = digest

            expected = entry.get("sha256")
            if expected and digest != expected:
                raise ValueError(f"SHA-256 mismatch: expected {expected}, got {digest}")

            with fitz.open(source) as doc:
                page_count = doc.page_count

            split = entry.get("split", "?")
            short = digest[:12]
            print(f"[ok] {doc_id:24s} split={split:13s} pages={page_count:3d} sha256={short}...")
        except Exception as exc:
            failures.append(f"{doc_id}: {exc}")
            print(f"[fail] {doc_id}: {exc}")

    if args.write_checksums:
        for doc_id, digest in checksums.items():
            documents[doc_id]["sha256"] = digest
        manifest["documents"] = documents
        write_checksums(manifest_path, checksums)
        print(f"\nWrote {len(checksums)} checksum(s) back to {manifest_path}")

    if failures:
        print(f"\n{len(failures)} document(s) failed:")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    print(f"\nAll {len(checksums)} document(s) verified.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
