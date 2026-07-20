"""QLoRA fine-tune of NuExtract on the photo gold (brick B).

Trains a LoRA adapter on ``gold/finetune/{train,val}.jsonl`` (built by
``build_finetune_data.py``) so NuExtract aligns per-product monthly quantities on the
dense ``etat_des_ventes`` layout. Uses QLoRA (4-bit base + LoRA) so a 4B model trains on
a ~12 GB GPU.

Requires the optional ``[ai]`` extra and a CUDA GPU:

    pip install -e ".[ai]"
    python scripts/build_finetune_data.py --converted ... --images ... --out gold/finetune
    python scripts/finetune_nuextract.py --data gold/finetune --out gold/adapter

Then evaluate the adapter with the benchmark:

    python scripts/benchmark_nuextract.py --model numind/NuExtract-2.0-4B \\
        --adapter gold/adapter --converted ... --images ...
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "gold" / "finetune"
OUT_DIR = ROOT / "gold" / "adapter"

# LoRA target projections. Attention-only is lighter (fewer stored activations at
# backward); the full set (with the MLP projections) adapts more but costs more VRAM.
_ATTN_MODULES = ["q_proj", "k_proj", "v_proj", "o_proj"]
_MLP_MODULES = ["gate_proj", "up_proj", "down_proj"]


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def _messages(example: dict[str, Any]) -> list[dict[str, Any]]:
    """User turn = image + inline template; assistant turn = the target JSON output.

    Must match the inference-time prompt exactly (see build_extraction_text).
    """
    from phaxtract.nuextract_engine import build_extraction_text

    return [
        {"role": "user", "content": build_extraction_text(example["template"])},
        {"role": "assistant", "content": example["output"]},
    ]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="QLoRA fine-tune NuExtract on gold.")
    parser.add_argument("--data", type=Path, default=DATA_DIR, help="Dir with train/val JSONL")
    parser.add_argument("--out", type=Path, default=OUT_DIR, help="Adapter output dir")
    parser.add_argument("--model", default="numind/NuExtract-2.0-2B", help="Base model id")
    parser.add_argument("--epochs", type=float, default=3.0, help="Training epochs")
    parser.add_argument("--lr", type=float, default=2e-4, help="Learning rate")
    parser.add_argument("--lora-r", type=int, default=16, help="LoRA rank")
    parser.add_argument("--lora-alpha", type=int, default=32, help="LoRA alpha")
    parser.add_argument("--grad-accum", type=int, default=8, help="Gradient accumulation steps")
    parser.add_argument("--max-pixels", type=int, default=500_000, help="Cap image resolution")
    parser.add_argument(
        "--max-output-chars",
        type=int,
        default=None,
        help="Skip training examples whose target JSON is longer (product-heavy = long "
        "sequence = VRAM); the layout lesson still comes from the shorter statements",
    )
    parser.add_argument(
        "--attn-only", action="store_true", help="LoRA on attention only (lower VRAM)"
    )
    return parser.parse_args()


def main() -> None:  # pragma: no cover - requires the [ai] extra and a GPU
    args = _parse_args()

    # Reduce allocator fragmentation before torch initializes (helps fit a 12 GB GPU).
    import os

    os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

    import torch
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from PIL import Image
    from transformers import (
        AutoModelForImageTextToText,
        AutoProcessor,
        BitsAndBytesConfig,
        Trainer,
        TrainingArguments,
    )

    from phaxtract.nuextract_engine import _target_size

    train = _read_jsonl(args.data / "train.jsonl")
    val_path = args.data / "val.jsonl"
    val = _read_jsonl(val_path) if val_path.exists() else []
    if args.max_output_chars is not None:
        kept = [ex for ex in train if len(ex["output"]) <= args.max_output_chars]
        print(f"Skipped {len(train) - len(kept)} long examples (> {args.max_output_chars} chars)")
        train = kept
    if not train:
        raise SystemExit(f"No training examples in {args.data / 'train.jsonl'}")
    print(f"Train: {len(train)}  Val: {len(val)}  Base: {args.model}")

    # Fused cross-entropy (Liger) computes the LM loss without materializing the full
    # [seq x vocab] logits — the allocation that OOMs long, product-heavy statements on
    # a 12 GB GPU. Must be applied before the model is built. Best-effort.
    try:
        import liger_kernel.transformers as lk

        if "2.0-4B" in args.model and hasattr(lk, "apply_liger_kernel_to_qwen2_5_vl"):
            lk.apply_liger_kernel_to_qwen2_5_vl()
        else:
            lk.apply_liger_kernel_to_qwen2_vl()
        print("Liger kernel applied (fused cross-entropy, lower VRAM).")
    except Exception as exc:  # optional accelerator; never fatal
        print(f"Liger kernel not applied ({exc}); long sequences may OOM.")

    # Route the (partially untyped) transformers factories through Any, as the engine
    # does, so strict mypy does not trip on their untyped `from_pretrained`.
    processor_cls: Any = AutoProcessor
    bnb_config_cls: Any = BitsAndBytesConfig
    model_cls: Any = AutoModelForImageTextToText

    processor = processor_cls.from_pretrained(args.model, trust_remote_code=True)
    bnb = bnb_config_cls(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )
    model = model_cls.from_pretrained(
        args.model, quantization_config=bnb, device_map="auto", trust_remote_code=True
    )
    model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True)
    model.enable_input_require_grads()  # keep gradients flowing with checkpointing + PEFT
    target_modules = _ATTN_MODULES if args.attn_only else _ATTN_MODULES + _MLP_MODULES
    model = get_peft_model(
        model,
        LoraConfig(
            r=args.lora_r,
            lora_alpha=args.lora_alpha,
            lora_dropout=0.05,
            bias="none",
            target_modules=target_modules,
            task_type="CAUSAL_LM",
        ),
    )
    model.print_trainable_parameters()

    image_token_id = getattr(model.config, "image_token_id", None)

    def collate(batch: list[dict[str, Any]]) -> Any:
        texts: list[str] = []
        images: list[list[Any]] = []
        for example in batch:
            text = processor.apply_chat_template(_messages(example), tokenize=False)
            texts.append(text)
            picture = Image.open(example["image"]).convert("RGB")
            resized = _target_size(picture.width, picture.height, args.max_pixels)
            if resized is not None:
                picture = picture.resize(resized)
            images.append([picture])
        inputs = processor(text=texts, images=images, padding=True, return_tensors="pt")
        labels = inputs["input_ids"].clone()
        labels[labels == processor.tokenizer.pad_token_id] = -100
        if image_token_id is not None:
            labels[labels == image_token_id] = -100  # don't train on image placeholders
        inputs["labels"] = labels
        return inputs

    args.out.mkdir(parents=True, exist_ok=True)
    trainer = Trainer(
        model=model,
        args=TrainingArguments(
            output_dir=str(args.out),
            num_train_epochs=args.epochs,
            per_device_train_batch_size=1,
            gradient_accumulation_steps=args.grad_accum,
            learning_rate=args.lr,
            bf16=True,
            gradient_checkpointing=True,
            logging_steps=5,
            save_strategy="epoch",
            optim="paged_adamw_8bit",
            remove_unused_columns=False,
            report_to="none",
        ),
        train_dataset=train,
        data_collator=collate,
    )
    trainer.train()
    model.save_pretrained(args.out)
    processor.save_pretrained(args.out)
    print(f"Saved LoRA adapter to {args.out}")


if __name__ == "__main__":
    main()
