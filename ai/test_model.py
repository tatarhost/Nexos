import os
from pathlib import Path

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

base_id = os.environ.get("MODEL_ID", "distilgpt2")
prompt = os.environ.get("TEST_PROMPT", "Hello!")
adapter = Path("dist/adapter")
tokenizer = AutoTokenizer.from_pretrained(adapter)
base = AutoModelForCausalLM.from_pretrained(base_id)
model = PeftModel.from_pretrained(base, adapter)
model.eval()
inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=128)
with torch.no_grad():
    output = model.generate(
        **inputs,
        max_new_tokens=80,
        do_sample=True,
        temperature=0.8,
        top_p=0.9,
        pad_token_id=tokenizer.eos_token_id,
    )
result = tokenizer.decode(output[0], skip_special_tokens=True)
Path("dist/test-report.txt").write_text(
    "Base model: " + base_id + "\nPrompt: " + prompt + "\n\nGenerated output:\n" + result + "\n",
    encoding="utf-8",
)
print(result)
