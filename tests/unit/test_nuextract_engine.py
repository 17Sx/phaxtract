"""Tests for the NuExtract engine — the torch/transformers-isolated inference layer.

The heavy model is never loaded here: we test the config surface, the lazy-import
error path, the device-resolution logic, and (in a fresh subprocess) that importing
the module never pulls torch into memory.
"""

from __future__ import annotations

import subprocess
import sys

import pytest

from phaxtract.nuextract_engine import (
    ExtractionDependencyError,
    NuExtractEngine,
    _resolve_device,
    _target_size,
    build_messages,
)


def test_default_config() -> None:
    engine = NuExtractEngine()
    assert engine.model_id == "numind/NuExtract3"
    assert engine.thinking is False
    assert engine.max_new_tokens == 4096
    assert engine.device is None  # resolved lazily at load time
    assert engine.load_in_4bit is False
    assert engine.max_pixels is None
    assert engine.adapter_path is None


def test_target_size_within_budget_is_none() -> None:
    assert _target_size(800, 600, None) is None
    assert _target_size(800, 600, 1_000_000) is None  # 480k <= 1M


def test_target_size_downscales_and_preserves_aspect() -> None:
    size = _target_size(4000, 3000, 1_000_000)
    assert size is not None
    width, height = size
    assert width * height <= 1_000_000
    # aspect ratio preserved (4:3)
    assert abs(width / height - 4 / 3) < 0.01


def test_resolve_device_prefers_explicit() -> None:
    assert _resolve_device("cpu", cuda_available=True) == "cpu"
    assert _resolve_device("cuda:1", cuda_available=False) == "cuda:1"


def test_resolve_device_auto() -> None:
    assert _resolve_device(None, cuda_available=True) == "cuda"
    assert _resolve_device(None, cuda_available=False) == "cpu"


def test_build_messages_user_turn_carries_image() -> None:
    messages = build_messages("photo.png")
    assert len(messages) == 1
    assert messages[0]["role"] == "user"
    assert {"type": "image", "image": "photo.png"} in messages[0]["content"]


def test_build_messages_with_output_adds_assistant_turn() -> None:
    messages = build_messages("photo.png", output='{"products": []}')
    assert [m["role"] for m in messages] == ["user", "assistant"]
    assert messages[1]["content"][0]["text"] == '{"products": []}'


def test_load_without_backend_raises_dependency_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom() -> object:
        raise ImportError("No module named 'torch'")

    monkeypatch.setattr("phaxtract.nuextract_engine._import_backend", _boom)
    engine = NuExtractEngine()
    with pytest.raises(ExtractionDependencyError, match=r"phaxtract\[ai\]"):
        engine.load()


def test_importing_engine_does_not_import_torch() -> None:
    code = (
        "import sys; import phaxtract.nuextract_engine, phaxtract.extract_ai; "
        "assert 'torch' not in sys.modules, 'torch was imported at module load'; "
        "assert 'transformers' not in sys.modules, 'transformers was imported at module load'"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
