---
name: transformers
description: "Hugging Face transformers — load, inspect, and run open-weight models in the HF layout (config.json + safetensors/.bin + tokenizer): AutoModel/AutoTokenizer/AutoConfig, safetensors-first loading, generation, save/convert. Use for HF-format checkpoints rather than raw .pt tensors, and for the trust_remote_code / pickle load-time RCE surface."
license: Apache-2.0
compatibility: "Python 3.9+; transformers 4.x; torch. Optional: safetensors, accelerate (device_map), bitsandbytes (quantized load). GPU optional."
metadata:
  author: AeonDave
  version: "1.0"
---

# transformers

The dominant loader for open-weight LLMs. When an artifact is a HF repo/folder (`config.json`, `*.safetensors` or `pytorch_model*.bin`, tokenizer files) rather than a bare `.pt`, go through `transformers` — it resolves architecture, tokenizer, and generation config for you. For raw `state_dict`/`.pt` tensors use [`pytorch`](../pytorch/SKILL.md); for malicious-artifact triage use [`model-scanning`](../model-scanning/SKILL.md).

## Load safely

```python
from transformers import AutoModelForCausalLM, AutoTokenizer, AutoConfig

cfg = AutoConfig.from_pretrained("org/model")          # metadata only, no weights
tok = AutoTokenizer.from_pretrained("org/model")
model = AutoModelForCausalLM.from_pretrained(
    "org/model",
    dtype="auto",            # older transformers: torch_dtype="auto"
    device_map="auto",       # needs `accelerate`; else .to("cuda")
    use_safetensors=True,    # refuse pickle weights when a safetensors copy exists
)
```

- **`trust_remote_code=True` is load-time RCE.** It imports and runs the repo's own `modeling_*.py`/`configuration_*.py` from the Hub inside your process. Many new architectures require it — read that Python (and pin a commit with `revision=`) before enabling; never set it on an unvetted repo.
- **Prefer safetensors over `.bin`.** `pytorch_model.bin` is pickle (arbitrary code on load); `*.safetensors` is header JSON + raw tensors with no code path. `use_safetensors=True` forces the safe copy.
- `local_files_only=True` pins to already-downloaded files (no silent Hub fetch); `revision="<sha>"` pins the exact commit.

## Inspect

```python
print(model.config)                      # architecture, hidden size, layers, vocab
print(model.num_parameters() / 1e9, "B")
print(model.get_memory_footprint() / 1e9, "GB")
print(model.generation_config)           # defaults the model ships for .generate()
for name, p in model.named_parameters():
    print(name, tuple(p.shape))
```

`AutoModel.from_pretrained` gives the bare backbone (no task head); use the task class (`AutoModelForCausalLM`, `...ForSequenceClassification`, etc.) that matches `config.architectures`.

## Generate and save

```python
ids = tok("Hello", return_tensors="pt").to(model.device)
out = model.generate(**ids, max_new_tokens=64, do_sample=False)
print(tok.decode(out[0], skip_special_tokens=True))

model.save_pretrained("out/", safe_serialization=True)   # writes safetensors
tok.save_pretrained("out/")
```

`safe_serialization=True` is the clean way to convert a pickle checkpoint you already trust into safetensors.

## Gotchas

- Tokenizer/model mismatch (wrong `pad_token`, chat template) silently degrades output — set `tok.pad_token` and apply `tok.apply_chat_template(...)` for instruct models.
- `device_map="auto"` shards across GPUs/CPU/disk; a model that "loads" may be partly on CPU and crawl. Check `model.hf_device_map`.
- 4-bit/8-bit load (`BitsAndBytesConfig`, `load_in_4bit=True`) needs `bitsandbytes` + CUDA; it is for inference/QLoRA, not a safety boundary.
- Version drift changes defaults (e.g. `torch_dtype` → `dtype`); pin `transformers` and check the installed version, not blog snippets.

## References

- Upstream: [huggingface/transformers](https://github.com/huggingface/transformers) ([from_pretrained / safetensors docs](https://huggingface.co/docs/transformers/main/en/main_classes/model))
- Companions in repo: [`pytorch`](../pytorch/SKILL.md) (raw checkpoints), [`model-scanning`](../model-scanning/SKILL.md) (untrusted artifacts), [`model-finetuning`](../model-finetuning/SKILL.md), [`abliteration`](../abliteration/SKILL.md); deep artifact forensics: [model-file-forensics](../../offensive-ctf/ai-ml-ctf/references/model-file-forensics-and-deserialization.md)
