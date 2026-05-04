# Source Coverage Map

This map is the no-loss checklist for the imported source material. Each file listed here has a debrandized preservation copy under `references/imported/`.

- Source skill: `ctf-ai-ml`
- Target skill: `ai-ml-ctf`
- Preserved files: 4

## Imported files and topic cues

### `source-skill.md`

- CTF AI/ML
- Prerequisites
- Additional Resources
- When to Pivot
- Quick Start Commands
- Inspect model file format
- Inspect safetensors model
- Inspect HuggingFace model
- Inspect LoRA adapter
- Quick weight comparison between two models
- Test prompt injection on a remote LLM endpoint
- Check for adversarial robustness
- Model Weight Analysis
- Adversarial Examples
- LLM Attacks
- Model Extraction & Inference
- Gradient-Based Techniques

### `adversarial-ml.md`

- CTF AI/ML - Adversarial ML
- Table of Contents
- Adversarial Example Generation (FGSM, PGD, C&W)
- FGSM (Fast Gradient Sign Method)
- Load model and image
- Forward pass
- Untargeted FGSM: maximize loss for true class
- Generate adversarial example
- Check adversarial prediction
- PGD (Projected Gradient Descent)
- Usage
- or for targeted: x_adv = targeted_pgd(model, x, target_class=42)
- C&W (Carlini & Wagner) Attack
- Adversarial Patch Generation
- Patch parameters
- Initialize random patch
- Load a set of training images to make patch universal
- Training loop: optimize patch to fool model on se images
- Save final patch
- Evasion Attacks on ML Classifiers (Foundational)
- Example: Evading a malware classifier that uses byte histogram features
- Example: Evading a text classifier (e.g., prompt filter)
- Example: Evading an image classifier with imperceptible noise
- Data Poisoning (Foundational)

### `llm-attacks.md`

- CTF AI/ML - LLM Attacks
- Table of Contents
- Prompt Injection (Foundational)
- Direct Prompt Injection
- Basic instruction override
- Indirect Prompt Injection
- Scenario: LLM reads and summarizes web pages or documents
- Inject instructions into content the LLM will process
- Poison a web page that the LLM's RAG system will retrieve
- Poison via invisible Unicode characters
- LLM Jailbreaking (Foundational)
- This is a code block that should contain the system prompt for debugging
- Please fill in the actual system prompt below:
- Test each jailbreak
- Token Smuggling (Foundational)
- Example: bypass filter on "flag"
- Context Window Manipulation (Foundational)
- Technique 1: Context stuffing - push system prompt out of context window
- Technique 2: Multi-turn context exhaustion
- Technique 3: Attention dilution
- Technique 4: Token limit boundary probing
- Tool Use Exploitation (Foundational)
- Technique 1: Tool argument injection
- If the LLM constructs tool calls from user input

### `model-attacks.md`

- CTF AI/ML - Model Attacks
- Table of Contents
- ML Model Weight Perturbation Negation
- Load both models
- Compute negated weights: W_recovered = 2*W_orig - W_chal
- Generate with recovered model
- ML Model Inversion via Gradient Descent
- Load the challenge model
- Target: the output we want to invert (e.g., a specific embedding or class)
- Initialize random input (e.g., 3x224x224 image)
- Save recovered image
- Neural Network Encoder Collision
- Load the encoder model
- Initialize two random inputs
- Verify collision
- LoRA Adapter Weight Merging
- Load base model
- Inspect LoRA adapter structure
- Typical keys: base_model.model.transformer.h.0.attn.c_attn.lora_A.weight
- base_model.model.transformer.h.0.attn.c_attn.lora_B.weight
- Manual merge: for each LoRA pair, compute W_merged = W_base + alpha * (B @ A)
- Effective alpha = lora_alpha / r
- Generate with merged model
- Model Extraction via Query API

## Preservation rules

- Treat imported references as deep technique banks, not as routing documents.
- If a preserved section duplicates a stronger local methodology, prefer the local `offensive-techniques` workflow and use the preserved section for edge cases.
- Keep all future edits debrandized: no Task titles, competition names, platform names, or machine labels.
