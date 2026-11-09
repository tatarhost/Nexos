import io
import json
import os
import re
import secrets
import shutil
import tempfile
import uuid
import zipfile
from pathlib import Path, PurePosixPath

import torch
from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from model import NexusGPT, decode, encode

DATA_DIR = Path(os.environ.get("NEXUS_DATA_DIR", "/data"))
MODELS_DIR = DATA_DIR / "models"
MAX_UPLOAD = int(os.environ.get("MAX_UPLOAD_MB", "500")) * 1024 * 1024
MAX_UNPACKED = 1024 * 1024 * 1024
API_TOKEN = os.environ.get("NEXUS_API_TOKEN", "")
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
loaded_models = {}

if not API_TOKEN or len(API_TOKEN) < 24:
    raise RuntimeError("Set NEXUS_API_TOKEN to a random secret of at least 24 characters.")

app = FastAPI(title="NEXUS Inference API", version="1.0.0")
origins = [x.strip() for x in os.environ.get(
    "CORS_ORIGINS", "https://tatarhost.github.io"
).split(",") if x.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)


def authorize(authorization: str = Header(default="")):
    supplied = authorization.removeprefix("Bearer ").strip()
    if not secrets.compare_digest(supplied, API_TOKEN):
        raise HTTPException(status_code=401, detail="Invalid API token")


def safe_extract_model(upload: bytes, destination: Path):
    if len(upload) > MAX_UPLOAD:
        raise HTTPException(status_code=413, detail="ZIP exceeds upload limit")
    try:
        archive = zipfile.ZipFile(io.BytesIO(upload))
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="Invalid ZIP archive")
    total = 0
    selected = {}
    with archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            name = PurePosixPath(info.filename)
            if name.is_absolute() or ".." in name.parts or len(name.parts) > 4:
                raise HTTPException(status_code=400, detail="Unsafe ZIP path")
            mode = info.external_attr >> 16
            if mode & 0o170000 == 0o120000:
                raise HTTPException(status_code=400, detail="ZIP symlinks are not allowed")
            total += info.file_size
            if total > MAX_UNPACKED:
                raise HTTPException(status_code=413, detail="Unpacked ZIP exceeds limit")
            base = name.name
            if base in ("model.pt", "config.json", "tokenizer.json"):
                if base in selected:
                    raise HTTPException(status_code=400, detail="Duplicate model files")
                selected[base] = archive.read(info)
    if "model.pt" not in selected or "config.json" not in selected:
        raise HTTPException(status_code=400, detail="ZIP must contain model/model.pt and model/config.json")
    try:
        config = json.loads(selected["config.json"].decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid config.json")
    required = ("width", "layers", "heads", "block_size")
    if any(k not in config for k in required):
        raise HTTPException(status_code=400, detail="Model config is incomplete")
    width, layers, heads, block = (int(config[k]) for k in required)
    if not (32 <= width <= 1024 and 1 <= layers <= 24 and 1 <= heads <= 16
            and width % heads == 0 and 16 <= block <= 512):
        raise HTTPException(status_code=400, detail="Model architecture is outside supported limits")
    try:
        payload = torch.load(io.BytesIO(selected["model.pt"]), map_location="cpu", weights_only=True)
        if not isinstance(payload, dict) or not isinstance(payload.get("state_dict"), dict):
            raise ValueError("Missing state_dict")
        model_config = payload.get("config", config)
        model = NexusGPT(model_config)
        model.load_state_dict(payload["state_dict"], strict=True)
        parameter_count = sum(p.numel() for p in model.parameters())
        if parameter_count > 120_000_000:
            raise ValueError("Model exceeds 120 million parameters")
        model.to(DEVICE).eval()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Model weights could not be loaded: {str(exc)[:180]}")
    destination.mkdir(parents=True, exist_ok=False)
    (destination / "model.pt").write_bytes(selected["model.pt"])
    (destination / "config.json").write_bytes(selected["config.json"])
    if "tokenizer.json" in selected:
        (destination / "tokenizer.json").write_bytes(selected["tokenizer.json"])
    return model, config, parameter_count


class ChatRequest(BaseModel):
    model_id: str = Field(min_length=1, max_length=64)
    prompt: str = Field(min_length=1, max_length=4000)
    max_new_tokens: int = Field(default=160, ge=1, le=256)


@app.on_event("startup")
def load_saved_models():
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    for folder in MODELS_DIR.iterdir():
        if not folder.is_dir():
            continue
        try:
            payload = torch.load(folder / "model.pt", map_location="cpu", weights_only=True)
            model = NexusGPT(payload["config"])
            model.load_state_dict(payload["state_dict"], strict=True)
            model.to(DEVICE).eval()
            config = json.loads((folder / "config.json").read_text(encoding="utf-8"))
            loaded_models[folder.name] = {"model": model, "config": config}
        except Exception as exc:
            print(f"Skipping invalid saved model {folder.name}: {exc}")


@app.get("/health")
def health():
    return {"ok": True, "service": "NEXUS Inference", "device": str(DEVICE)}


@app.get("/api/models", dependencies=[Depends(authorize)])
def list_models():
    return {"models": [
        {"id": model_id, "name": item["config"].get("name", model_id),
         "parameters": item["config"].get("parameters")}
        for model_id, item in loaded_models.items()
    ]}


@app.post("/api/models/upload", dependencies=[Depends(authorize)])
async def upload_model(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Choose a .zip model archive")
    content = await file.read(MAX_UPLOAD + 1)
    await file.close()
    model_id = uuid.uuid4().hex[:16]
    destination = MODELS_DIR / model_id
    try:
        model, config, count = safe_extract_model(content, destination)
    except Exception:
        shutil.rmtree(destination, ignore_errors=True)
        raise
    loaded_models[model_id] = {"model": model, "config": {**config, "parameters": count}}
    return {"id": model_id, "name": config.get("name", "NEXUS model"), "parameters": count}


@app.post("/api/chat", dependencies=[Depends(authorize)])
def chat(request: ChatRequest):
    item = loaded_models.get(request.model_id)
    if not item:
        raise HTTPException(status_code=404, detail="Model not found. Upload its ZIP first.")
    model = item["model"]
    tokens = encode(request.prompt)
    torch.seed()
    generated = list(tokens)
    with torch.inference_mode():
        for _ in range(request.max_new_tokens):
            context = torch.tensor([generated[-model.block_size:]], dtype=torch.long, device=DEVICE)
            logits = model(context)[0, -1].float() / 0.9
            logits[:4] = -float("inf")
            next_token = int(torch.multinomial(torch.softmax(logits, dim=-1), 1).item())
            if next_token == 2:
                break
            generated.append(next_token)
    answer = decode(generated[len(tokens):]).strip()
    return {"model": item["config"].get("name", request.model_id), "answer": answer}


@app.delete("/api/models/{model_id}", dependencies=[Depends(authorize)])
def delete_model(model_id: str):
    if not re.fullmatch(r"[a-f0-9]{16}", model_id) or model_id not in loaded_models:
        raise HTTPException(status_code=404, detail="Model not found")
    del loaded_models[model_id]
    shutil.rmtree(MODELS_DIR / model_id, ignore_errors=True)
    return {"deleted": model_id}
