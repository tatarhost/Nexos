import json
import os
from pathlib import Path

import torch
from datasets import Dataset
from peft import LoraConfig, TaskType, get_peft_model
from transformers import AutoModelForCausalLM, AutoTokenizer, DataCollatorForLanguageModeling, Trainer, TrainingArguments

model_id = os.environ.get("MODEL_ID", "distilgpt2")
dataset_path = Path(os.environ.get("DATASET_PATH", "data/train.jsonl"))
epochs = int(os.environ.get("EPOCHS", "1"))
if epochs not in (1, 2, 3):
    raise SystemExit("EPOCHS must be 1, 2 or 3.")

rows = []
with dataset_path.open("r", encoding="utf-8") as f:
    for line_number, line in enumerate(f, 1):
        if not line.strip():
            continue
        item = json.loads(line)
        value = item.get("text") if isinstance(item, dict) else None
        if not isinstance(value, str) or not value.strip():
            raise SystemExit(f"Line {line_number} must contain a non-empty string field named 'text'.")
        rows.append({"text": value.strip()})
if len(rows) < 2:
    raise SystemExit("At least two non-empty training examples are required.")

tokenizer = AutoTokenizer.from_pretrained(model_id)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token
model = AutoModelForCausalLM.from_pretrained(model_id)
model.config.pad_token_id = tokenizer.pad_token_id

# GPT-2 style attention layers use Conv1D projections; fan_in_fan_out handles that layout.
lora = LoraConfig(
    task_type=TaskType.CAUSAL_LM,
    r=8,
    lora_alpha=16,
    lora_dropout=0.05,
    target_modules=["c_attn", "c_proj"],
    fan_in_fan_out=True,
)
model = get_peft_model(model, lora)
model.print_trainable_parameters()

dataset = Dataset.from_list(rows)
def tokenize(batch):
    return tokenizer(batch["text"], truncation=True, max_length=128)
tokenized = dataset.map(tokenize, batched=True, remove_columns=["text"])
if len(tokenized) < 2:
    raise SystemExit("Dataset did not produce enough tokenized examples.")

args = TrainingArguments(
    output_dir="ai/training-output",
    num_train_epochs=epochs,
    per_device_train_batch_size=1,
    gradient_accumulation_steps=1,
    learning_rate=2e-4,
    logging_steps=1,
    save_strategy="no",
    report_to="none",
    use_cpu=not torch.cuda.is_available(),
    dataloader_pin_memory=torch.cuda.is_available(),
)
trainer = Trainer(
    model=model,
    args=args,
    train_dataset=tokenized,
    data_collator=DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False),
    tokenizer=tokenizer,
)
trainer.train()

out = Path("dist/adapter")
out.mkdir(parents=True, exist_ok=True)
model.save_pretrained(out)
tokenizer.save_pretrained(out)
merged = model.merge_and_unload()
merged_dir = Path("dist/model")
merged_dir.mkdir(parents=True, exist_ok=True)
merged.save_pretrained(merged_dir, safe_serialization=True)
tokenizer.save_pretrained(merged_dir)
Path("dist/model-info.json").write_text(json.dumps({
    "base_model": model_id,
    "method": "LoRA",
    "epochs": epochs,
    "training_examples": len(rows),
    "adapter_directory": "adapter",
}, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Saved LoRA adapter to {out}")
