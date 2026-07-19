"""Local NuExtract inference engine — the torch/transformers-isolated layer.

NuExtract 3 (and the 2.0 family) are Qwen-VL vision-language models: they read a
photo plus a JSON *template* and emit filled JSON. This module owns the heavy work
of loading such a model and running greedy, deterministic inference on an image.

**All torch/transformers imports are lazy** (inside :func:`_import_backend`, called
from :meth:`NuExtractEngine.load`). Importing this module — or
:mod:`phaxtract.extract_ai`, which references it only for typing — never pulls torch
into memory, so the deterministic layer and CI stay dependency-free. The heavy path
lives behind the optional ``[ai]`` extra.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Protocol, runtime_checkable

_INSTALL_HINT = (
    "NuExtract inference needs the optional AI dependencies. "
    "Install them with:  pip install phaxtract[ai]"
)

# Instruction paired with the JSON template in the chat prompt. NuExtract keys its
# extraction off the template; the instruction just frames the task.
_EXTRACT_INSTRUCTION = "Extract the information according to the template."


class ExtractionDependencyError(RuntimeError):
    """Raised when the optional ``[ai]`` extra (torch/transformers) is missing."""


@runtime_checkable
class ExtractionEngine(Protocol):
    """A source of raw NuExtract JSON for an image + template.

    Implementations turn a document image and a JSON template string into the
    model's raw completion. Injecting a fake implementation lets the extraction
    orchestrator be tested without a GPU or a model download.
    """

    def extract(self, image: str | Path, template: str) -> str:
        """Return the raw JSON completion for ``image`` given ``template``."""
        ...


def _resolve_device(explicit: str | None, *, cuda_available: bool) -> str:
    """Pick a torch device: honour an explicit choice, else auto-select."""
    if explicit is not None:
        return explicit
    return "cuda" if cuda_available else "cpu"


def _build_messages(image: str | Path) -> list[dict[str, Any]]:
    """Build the chat message list for a single-image extraction turn."""
    return [
        {
            "role": "user",
            "content": [
                {"type": "image", "image": str(image)},
                {"type": "text", "text": _EXTRACT_INSTRUCTION},
            ],
        }
    ]


def _import_backend() -> SimpleNamespace:  # pragma: no cover - requires the [ai] extra
    """Import torch + transformers lazily; raise ``ImportError`` if unavailable."""
    import torch
    from transformers import AutoModelForImageTextToText, AutoProcessor

    return SimpleNamespace(
        torch=torch,
        model_cls=AutoModelForImageTextToText,
        processor_cls=AutoProcessor,
    )


@dataclass
class NuExtractEngine:
    """Load a NuExtract model once and extract raw JSON from document images.

    The model is loaded lazily on the first :meth:`extract` (or explicit
    :meth:`load`) call and cached for reuse. Decoding is greedy (temperature 0),
    the recommended setting for structured extraction.

    Args:
        model_id: HuggingFace model id (default ``numind/NuExtract3``).
        device: torch device (e.g. ``"cuda"``, ``"cpu"``); ``None`` auto-selects.
        max_new_tokens: generation cap for the JSON completion.
        thinking: enable NuExtract's reasoning mode; off for deterministic output.
    """

    model_id: str = "numind/NuExtract3"
    device: str | None = None
    max_new_tokens: int = 4096
    thinking: bool = False

    _loaded: bool = field(default=False, init=False, repr=False)
    _torch: Any = field(default=None, init=False, repr=False)
    _model: Any = field(default=None, init=False, repr=False)
    _processor: Any = field(default=None, init=False, repr=False)
    _device: str = field(default="cpu", init=False, repr=False)

    def load(self) -> None:
        """Load and cache the model + processor. Idempotent.

        Raises:
            ExtractionDependencyError: when the ``[ai]`` extra is not installed.
        """
        if self._loaded:
            return
        try:
            backend = _import_backend()
        except ImportError as exc:
            raise ExtractionDependencyError(_INSTALL_HINT) from exc
        self._init_from_backend(backend)  # pragma: no cover - requires the [ai] extra

    def _init_from_backend(  # pragma: no cover - requires the [ai] extra
        self, backend: SimpleNamespace
    ) -> None:
        torch = backend.torch
        device = _resolve_device(self.device, cuda_available=torch.cuda.is_available())
        dtype = torch.bfloat16 if device.startswith("cuda") else torch.float32
        self._model = backend.model_cls.from_pretrained(
            self.model_id,
            torch_dtype=dtype,
            device_map="auto" if device.startswith("cuda") else None,
            trust_remote_code=True,
        ).eval()
        self._processor = backend.processor_cls.from_pretrained(
            self.model_id, trust_remote_code=True
        )
        self._torch = torch
        self._device = device
        self._loaded = True

    def extract(  # pragma: no cover - requires the [ai] extra and a GPU
        self, image: str | Path, template: str
    ) -> str:
        """Run NuExtract on ``image`` with ``template``; return the raw JSON string."""
        from PIL import Image

        self.load()
        picture = Image.open(image).convert("RGB")
        messages = _build_messages(image)
        text = self._processor.tokenizer.apply_chat_template(
            messages,
            template=template,
            tokenize=False,
            add_generation_prompt=True,
        )
        inputs = self._processor(
            text=[text], images=[picture], padding=True, return_tensors="pt"
        ).to(self._device)
        with self._torch.no_grad():
            generated = self._model.generate(
                **inputs,
                do_sample=False,
                num_beams=1,
                max_new_tokens=self.max_new_tokens,
            )
        trimmed = [
            out[len(inp) :]
            for inp, out in zip(inputs.input_ids, generated, strict=True)
        ]
        decoded: list[str] = self._processor.batch_decode(
            trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
        )
        return decoded[0]
