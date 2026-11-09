import json
import os
import random
from pathlib import Path

import torch
from torch.nn import functional as F

from model import NexusGPT, encode

DATASET_PATH = Path(os.environ.get("DATASET_PATH", "data/train.jsonl"))
MODEL_SIZE = os.environ.get("MODEL_SIZE", "10m").lower()
MAX_STEPS = int(os.environ.get("MAX_STEPS", "100"))
BLOCK_SIZE = 128

if MODEL_SIZE == "10m":
    config = {"name": "NEXUS-10M", "width": 384, "layers": 6, "heads": 6, "block_size": BLOCK_SIZE}
elif MODEL_SIZE == "100m":
    config = {"name": "NEXUS-100M", "width": 768, "layers": 14, "heads": 12, "block_size": BLOCK_SIZE}
else:
    raise SystemExit("MODEL_SIZE must be 10m or 100m.")
if not 10 <= MAX_STEPS <= 2000:
    raise SystemExit("MAX_STEPS must be between 10 and 2000.")

rows = []
with DATASET_PATH.open("r", encoding="utf-8") as stream:
    for line_number, line in enumerate(stream, 1):
        if not line.strip():
            continue
        item = json.loads(line)
        value = item.get("text") if isinstance(item, dict) else None
        if not isinstance(value, str) or len(value.strip()) < 2:
            raise SystemExit(f"Line {line_number} must contain a non-empty 'text' field.")
        rows.append(value.strip())
if len(rows) < 2:
    raise SystemExit("At least two training examples are required.")

# Train a byte-level language model from random initialization. No pretrained weights.
tokens = []
for row in rows:
    tokens.extend(encode(row))
tokens = torch.tensor(tokens, dtype=torch.long)
if len(tokens) < 8:
    raise SystemExit("Training corpus is too small.")

torch.manual_seed(42)
random.seed(42)
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = NexusGPT(config).to(device)
parameter_count = sum(p.numel() for p in model.parameters())
print(f"Training {config['name']} from scratch: {parameter_count:,} parameters on {device}")
optimizer = torch.optim.AdamW(model.parameters(), lr=3e-4, weight_decay=0.1)
model.train()

for step in range(1, MAX_STEPS + 1):
    starts = torch.randint(0, len(tokens) - 1, (1,)).item()
    end = min(starts + BLOCK_SIZE + 1, len(tokens))
    sample = tokens[starts:end]
    if len(sample) < 3:
        sample = tokens[:min(len(tokens), BLOCK_SIZE + 1)]
    if len(sample) < 3:
        raise SystemExit("Not enough tokens to create a training batch.")
    x = sample[:-1].unsqueeze(0).to(device)
    y = sample[1:].unsqueeze(0).to(device)
    logits = model(x)
    loss = F.cross_entropy(logits.reshape(-1, logits.size(-1)), y.reshape(-1))
    optimizer.zero_grad(set_to_none=True)
    loss.backward()
    torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
    optimizer.step()
    if step == 1 or step % 10 == 0 or step == MAX_STEPS:
        print(f"step {step}/{MAX_STEPS} - loss: {loss.item():.4f}")

out = Path("dist/model")
out.mkdir(parents=True, exist_ok=True)
torch.save({"state_dict": model.cpu().state_dict(), "config": config}, out / "model.pt")
(out / "config.json").write_text(json.dumps({
    **config,
    "parameters": parameter_count,
    "training_steps": MAX_STEPS,
    "training_examples": len(rows),
    "initialization": "random",
    "tokenizer": "UTF-8 byte-level",
}, ensure_ascii=False, indent=2), encoding="utf-8")
(out / "tokenizer.json").write_text(json.dumps({
    "type": "utf8-byte",
    "vocab_size": 260,
    "special_tokens": {"pad": 0, "bos": 1, "eos": 2, "unk": 3},
}, indent=2), encoding="utf-8")
print(f"Saved standalone NEXUS model to {out} ({parameter_count:,} parameters)")
