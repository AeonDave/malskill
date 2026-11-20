---
name: model-finetuning
description: "Fine-tune open-weight LLMs with TRL, PEFT LoRA/QLoRA, Unsloth, or Axolotl; prepare datasets, optimize preferences, merge adapters, and export models. Use also to implement or audit targeted machine unlearning, including removal claims for deployed models."
license: MIT
compatibility: "Python 3.10+; transformers, trl, peft, datasets, accelerate. QLoRA needs bitsandbytes + CUDA. A single 24-48 GB GPU covers most 7-13B QLoRA runs; full fine-tune needs far more."
metadata:
  author: AeonDave
  version: "1.0"
---

# model-finetuning

Adapt an open model to a task or domain. Default to **parameter-efficient** fine-tuning (LoRA/QLoRA): you freeze the base and train small low-rank adapters, which fits large models on one GPU and keeps the base reusable. Reach for full fine-tuning only when PEFT measurably underperforms. For the inference-only side use [`transformers`](../transformers/SKILL.md); for a training-free behavior change (uncensoring, style) use [`abliteration`](../abliteration/SKILL.md).

## Stack

For authoring weights or compiling a bounded fact memory without an optimizer, load [weight-space-programming](../weight-space-programming/SKILL.md).

- **TRL `SFTTrainer`** — supervised fine-tuning on top of transformers `Trainer`; handles chat/instruction formatting, completion-only masking, packing, and native PEFT. Configure via `SFTConfig`.
- **PEFT `LoraConfig`** — the adapter definition (`r`, `lora_alpha`, `target_modules`, `task_type`).
- **`BitsAndBytesConfig`** — 4-bit NF4 base load = QLoRA.
- **Unsloth** / **Axolotl** — faster kernels / YAML-driven pipelines over the same primitives.

## QLoRA recipe

```python
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import LoraConfig
from trl import SFTTrainer, SFTConfig
from datasets import load_dataset

bnb = BitsAndBytesConfig(
    load_in_4bit=True, bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True,
)
model = AutoModelForCausalLM.from_pretrained("org/base", quantization_config=bnb, device_map="auto")
tok = AutoTokenizer.from_pretrained("org/base")

peft_cfg = LoraConfig(
    r=16, lora_alpha=32, lora_dropout=0.05, bias="none",
    target_modules="all-linear",   # attention + MLP; beats attention-only
    task_type="CAUSAL_LM",
)

trainer = SFTTrainer(
    model=model,
    args=SFTConfig(output_dir="out", num_train_epochs=2, learning_rate=2e-4,
                   per_device_train_batch_size=2, gradient_accumulation_steps=8,
                   bf16=True, packing=True),
    train_dataset=load_dataset("json", data_files="train.jsonl")["train"],
    peft_config=peft_cfg,
    processing_class=tok,          # older TRL: tokenizer=tok
)
trainer.train()
trainer.save_model("out")          # saves the adapter, not the full model
```

Sane starting defaults: `r=16`, `alpha=32`, `target_modules="all-linear"`, `lr=2e-4`, 2-3 epochs. Train on completions only (mask the prompt) for a small quality gain. Spend effort on data quality before hyperparameters.

## Dataset format

SFT expects either a `text` column or a chat `messages` list; `SFTTrainer` applies the tokenizer's chat template. A few thousand clean, task-representative examples usually beat a noisy large set.

## Preference and alignment tuning

SFT teaches a format; preference optimization aligns *which* answer the model prefers. All are TRL trainers that compose with PEFT/QLoRA the same way as `SFTTrainer`:

| Method | Signal | When |
|---|---|---|
| **DPO** (`DPOTrainer`/`DPOConfig`) | paired chosen/rejected | default preference alignment (style, safety); no reward model or RL loop — tune `beta`, `loss_type` |
| **KTO** (`KTOTrainer`) | unpaired binary good/bad | feedback is easier to collect as thumbs up/down than as pairs |
| **ORPO** (`ORPOTrainer`) | paired, folded into SFT | single stage, no separate reference model |
| **GRPO** (`GRPOTrainer`) | programmatic reward function | verifiable-reward RL (math/code); the DeepSeek-R1 method, lighter than PPO |
| **PPO** (`PPOTrainer`) + `RewardTrainer` | learned reward model | classic RLHF; highest cost (rollouts + critic) |

```python
from trl import DPOConfig, DPOTrainer
trainer = DPOTrainer(
    model=policy_model, ref_model=None,   # ref_model=None reuses the base under PEFT
    args=DPOConfig(output_dir="out-dpo", beta=0.1, learning_rate=5e-7, bf16=True),
    train_dataset=dataset,                # columns: prompt, chosen, rejected
    processing_class=tok,
)
trainer.train()
```

Offensive note: a harmful preference dataset (e.g. toxic-DPO) is a **training-based uncensoring** route — the alternative to training-free [`abliteration`](../abliteration/SKILL.md). The same authorization and poisoning caveats apply.

## Unlearning (post-training removal)

Implement targeted removal or audit a claimed removal of training-data influence. Distinguish weight-level unlearning from inference-time suppression: neither low output accuracy nor refusal alone establishes erasure.

Core rules:

- Measure forgetting and retained utility; add relearning and representation-level tests when model access permits. State which checks were unavailable and limit the claim accordingly.
- Evaluate the exact artifact and serving configuration, including quantization or inference-time interventions; full-precision results do not establish quantized behavior.
- For agents, identify whether the target is knowledge, a behavior/trajectory, or runtime state; evaluate the corresponding layer.

Load [references/unlearning.md](references/unlearning.md) when selecting an unlearning method, testing removal claims, assessing quantized deployment, or removing agent trajectories/runtime state. It owns the method comparisons and access requirements for verification.

## Merge and export

```python
from peft import AutoPeftModelForCausalLM
merged = AutoPeftModelForCausalLM.from_pretrained("out").merge_and_unload()
merged.save_pretrained("merged", safe_serialization=True)   # safetensors full model
```

Merge adapters into the base for zero-overhead inference, then convert to GGUF to serve locally via [`ollama`](../ollama/SKILL.md).

## Gotchas and security

- QLoRA trains on a 4-bit base: slightly lower ceiling than 16-bit LoRA — acceptable for most adaptation, not for squeezing maximum accuracy.
- `target_modules="all-linear"` resolves per architecture; if PEFT can't infer it, name the projections (`q_proj,k_proj,v_proj,o_proj,gate_proj,up_proj,down_proj`).
- TRL/PEFT APIs churn (`tokenizer=` → `processing_class=`, `TrainingArguments` → `SFTConfig`) — check installed versions, not old notebooks.
- Fine-tuning is a poisoning/backdoor vector: a crafted dataset can install trigger-conditioned behavior while benchmarks look normal. Control dataset provenance; evaluate on held-out and adversarial prompts. Attack-side modeling: [`adversarial-robustness-toolbox`](../adversarial-robustness-toolbox/SKILL.md), [model-attacks](../../offensive-ctf/ai-ml-ctf/references/model-attacks.md).

## References

- [TRL SFTTrainer](https://huggingface.co/docs/trl/sft_trainer) · [PEFT LoRA](https://huggingface.co/docs/peft/package_reference/lora) · [Unsloth](https://github.com/unslothai/unsloth) · [Axolotl](https://github.com/axolotl-ai-cloud/axolotl)
