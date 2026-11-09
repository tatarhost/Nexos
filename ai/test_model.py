import os
from pathlib import Path

import torch

from model import NexusGPT, decode, encode

folder = Path("dist/model")
payload = torch.load(folder / "model.pt", map_location="cpu", weights_only=True)
model = NexusGPT(payload["config"])
model.load_state_dict(payload["state_dict"])
model.eval()

prompt = os.environ.get("TEST_PROMPT", "Привет! Расскажи о себе.")
tokens = encode(prompt)
generated = tokens[:]
torch.manual_seed(7)
with torch.no_grad():
    for _ in range(120):
        context = torch.tensor([generated[-model.block_size:]], dtype=torch.long)
        logits = model(context)[0, -1]
        logits = logits / 0.9
        probabilities = torch.softmax(logits, dim=-1)
        next_token = int(torch.multinomial(probabilities, 1).item())
        if next_token == 2:
            break
        generated.append(next_token)

result = decode(generated[1:])
config = payload["config"]
report = (
    f"Model: {config['name']}\n"
    f"Parameters: {sum(p.numel() for p in model.parameters()):,}\n"
    f"Prompt: {prompt}\n\nGenerated output:\n{result}\n"
)
Path("dist/test-report.txt").write_text(report, encoding="utf-8")
print(report)
