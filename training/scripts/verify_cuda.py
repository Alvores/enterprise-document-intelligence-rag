"""CUDA post-training workspace verification gate (Phase 8A).

Validates the isolated ``training/`` environment end-to-end before any QLoRA SFT
or DPO run: package imports, CUDA/Blackwell (sm_120) availability, a bfloat16
GEMM, a bitsandbytes 4-bit NF4 QLoRA forward/backward, and YAML config parsing.

Exits non-zero on any failure so it can gate CI or a local pre-training check.
"""

import sys
from pathlib import Path

TRAINING_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = TRAINING_ROOT / "configs"


def _section(title: str) -> None:
    print(f"\n=== {title} ===")


def _ok(message: str) -> None:
    print(f"[OK] {message}")


def _fail(message: str) -> None:
    print(f"[FAIL] {message}")


def check_imports() -> bool:
    _section("1. Package imports and versions")
    modules = [
        "torch",
        "transformers",
        "peft",
        "trl",
        "bitsandbytes",
        "accelerate",
        "datasets",
    ]
    all_ok = True
    for name in modules:
        try:
            module = __import__(name)
            version = getattr(module, "__version__", "unknown")
            _ok(f"{name}=={version}")
        except Exception as exc:
            _fail(f"{name} import failed: {exc}")
            all_ok = False
    return all_ok


def check_cuda() -> bool:
    _section("2. CUDA availability and architecture support")
    try:
        import torch
    except Exception as exc:
        _fail(f"torch import failed: {exc}")
        return False

    if not torch.cuda.is_available():
        _fail("torch.cuda.is_available() is False; no CUDA device detected.")
        return False

    device = torch.cuda.current_device()
    name = torch.cuda.get_device_name(device)
    major, minor = torch.cuda.get_device_capability(device)
    sm_arch = f"sm_{major}{minor}"
    free_bytes, total_bytes = torch.cuda.mem_get_info(device)

    print(f"  GPU name: {name}")
    print(f"  Compute capability: {major}.{minor} ({sm_arch})")
    print(f"  torch.version.cuda: {torch.version.cuda}")
    print(f"  VRAM total: {total_bytes / (1024**3):.2f} GiB")
    print(f"  VRAM free:  {free_bytes / (1024**3):.2f} GiB")

    arch_list = torch.cuda.get_arch_list()
    if sm_arch in arch_list:
        _ok(f"{sm_arch} is compiled into this torch build.")
    else:
        _fail(f"{sm_arch} not found in torch.cuda.get_arch_list(): {arch_list}")
        return False

    _ok("CUDA device detected and usable.")
    return True


def check_bf16_gemm() -> bool:
    _section("3. bfloat16 GEMM smoke test")
    try:
        import torch
    except Exception as exc:
        _fail(f"torch import failed: {exc}")
        return False

    try:
        torch.manual_seed(0)
        a = torch.randn(512, 512, dtype=torch.bfloat16, device="cuda")
        b = torch.randn(512, 512, dtype=torch.bfloat16, device="cuda")
        c = a @ b
        torch.cuda.synchronize()
        if c.shape != (512, 512) or not torch.isfinite(c.float()).all():
            raise RuntimeError("unexpected matmul result shape or non-finite values")
        _ok("bfloat16 matmul on CUDA succeeded (512x512 @ 512x512).")
        return True
    except Exception as exc:
        _fail(f"bfloat16 GEMM failed: {exc}")
        return False


def check_bnb_qlora() -> bool:
    _section("4. bitsandbytes 4-bit NF4 QLoRA smoke test")
    try:
        import bitsandbytes as bnb
        import torch
        import torch.nn as nn
    except Exception as exc:
        _fail(f"import failed: {exc}")
        return False

    try:
        torch.manual_seed(0)
        linear = bnb.nn.Linear4bit(
            256,
            256,
            bias=False,
            compute_dtype=torch.bfloat16,
            quant_type="nf4",
        ).cuda()

        x = torch.randn(8, 256, dtype=torch.bfloat16, device="cuda", requires_grad=True)
        delta = nn.Parameter(torch.zeros(256, 256, dtype=torch.bfloat16, device="cuda"))

        out = linear(x) + (x @ delta)
        loss = out.float().pow(2).mean()
        loss.backward()
        torch.cuda.synchronize()

        if x.grad is None or not torch.isfinite(x.grad.float()).all():
            raise RuntimeError("no finite input gradient flowed through Linear4bit")
        if delta.grad is None or not torch.isfinite(delta.grad.float()).all():
            raise RuntimeError("no finite adapter gradient; bf16 LoRA delta did not train")

        _ok("Linear4bit forward + backward succeeded; gradient flowed into bf16 adapter.")
        return True
    except Exception as exc:
        _fail(f"bitsandbytes 4-bit NF4 QLoRA smoke test failed: {exc}")
        return False


def check_yaml_configs() -> bool:
    _section("5. Training config validation")
    try:
        import yaml
    except Exception as exc:
        _fail(f"pyyaml import failed: {exc}")
        return False

    filenames = ["sft_qwen3_8b.yaml", "dpo_qwen3_8b.yaml"]
    all_ok = True
    for filename in filenames:
        path = CONFIG_DIR / filename
        if not path.exists():
            _fail(f"{path} does not exist.")
            all_ok = False
            continue
        try:
            with path.open("r", encoding="utf-8") as handle:
                data = yaml.safe_load(handle)
            if not isinstance(data, dict):
                raise ValueError("top-level YAML value is not a mapping")
            _ok(f"{filename} parsed cleanly ({len(data)} top-level keys).")
        except Exception as exc:
            _fail(f"{filename} failed to parse: {exc}")
            all_ok = False
    return all_ok


def main() -> int:
    print("CUDA post-training workspace verification")
    print(f"Training root: {TRAINING_ROOT}")

    checks = [
        ("imports", check_imports),
        ("cuda", check_cuda),
        ("bf16 gemm", check_bf16_gemm),
        ("bnb qlora", check_bnb_qlora),
        ("yaml configs", check_yaml_configs),
    ]

    passed = 0
    failed = 0
    for label, check in checks:
        try:
            ok = check()
        except Exception as exc:
            _fail(f"{label} raised an unexpected error: {exc}")
            ok = False
        if ok:
            passed += 1
        else:
            failed += 1

    print(f"\n=== Summary: {passed} passed, {failed} failed ===")
    if failed:
        print("Verification FAILED. Resolve the issues above before training.")
        return 1
    print("All checks passed. The workspace is ready for QLoRA SFT/DPO.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
