---
name: model-finetuning
description: "Fine-tune and adapt open-weight LLMs with Hugging Face TRL + PEFT LoRA/QLoRA (bitsandbytes), or Unsloth/Axolotl: supervised fine-tuning (SFTTrainer) and preference optimization (DPO/ORPO/KTO/GRPO), dataset formatting, adapter merge and GGUF export. Use for training-based adaptation of local models, not inference-only inspection."
license: MIT
compatibility: "Python 3.10+; transformers, trl, peft, datasets, accelerate. QLoRA needs bitsandbytes + CUDA. A single 24-48 GB GPU covers most 7-13B QLoRA runs; full fine-tune needs far more."
metadata:
  author: AeonDave
  version: "1.0"
  category: ai
---

# model-finetuning

Adapt an open model to a task or domain. Default to **parameter-efficient** fine-tuning (LoRA/QLoRA): you freeze the base and train small low-rank adapters, which fits large models on one GPU and keeps the base reusable. Reach for full fine-tuning only when PEFT measurably underperforms. For the inference-only side use [`transformers`](../transformers/SKILL.md); for a training-free behavior change (uncensoring, style) use [`abliteration`](../abliteration/SKILL.md).

## Stack

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

Remove a capability/knowledge from a trained model — the inverse direction of fine-tuning, and the training-based counterpart to ablation editing ([`abliteration`](../abliteration/SKILL.md)). Dual use: strip unwanted capability from your own model, or **verify a vendor's claimed unlearning actually removed data** (most methods only obfuscate — recovery attacks "jog the memory" of models that were merely perturbed; see *"Unlearning or Obfuscating?"*, 2025).

Method families ([SoK: LLM unlearning, arXiv:2506.09227](https://arxiv.org/html/2506.09227v1); catalog: [awesome-llm-unlearning](https://github.com/chrisliu298/awesome-llm-unlearning)):

| Family | Method | Notes |
|---|---|---|
| Gradient ascent | plain GA on forget-set | simplest; destabilizes the model beyond the forget target |
| **NPO** (`NPOTrainer`, TRL) | negative preference optimization | unlearning framed as preference optimization — more stable than GA, the current default |
| **WHP** | fine-tune on augmented/related corpora ("Who's Harry Potter") | teach the model the *opposite* of the target knowledge |
| **RMU** | steering forget-sample activations toward random directions (WMDP paper) | representation-level; strong for capability removal |
| Task arithmetic | subtract a "forget task vector" | training-free — lives in [`model-merging`](../model-merging/SKILL.md) |
| Ablation | knowledge-neuron / direction ablation | training-free — lives in [`abliteration`](../abliteration/SKILL.md) |

Evaluation rule: unlearning claims require **both** a forget-set test (knowledge truly gone — not just refuses to answer) and a retain-set test (no collateral damage). Verbatim-answer suppression is the weakest claim; adversarial retrieval probes (fine-tune recovery, prompt reconstruction) are how you distinguish removal from obfuscation.

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
