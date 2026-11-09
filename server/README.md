# NEXUS Inference Server

A persistent API for uploading, validating, storing and running NEXUS GPT ZIP model archives.

## Deploy on a Linux VPS

1. Install Docker Engine and the Docker Compose plugin.
2. Clone this repository onto the server.
3. Copy `server/.env.example` to `.env` and replace `NEXUS_API_TOKEN` with a long random secret (at least 24 characters). Add your website's origin to `CORS_ORIGINS` (origin only, no path).
4. Run `docker compose -f server/compose.yml up -d --build`.
5. Put HTTPS in front of port 8000 using a reverse proxy such as Caddy or nginx. Do not expose the API over plain HTTP on the public internet.
6. In NEXUS OS → AI Lab, enter the HTTPS API URL and token, connect, then upload a model ZIP.

The service stores models in a persistent Docker volume, reloads them after restart, and runs generation on CUDA when a compatible PyTorch CUDA build and GPU are available; otherwise it uses CPU. The included Dockerfile installs CPU PyTorch by default. For NVIDIA GPU deployment, use a CUDA-compatible PyTorch image/build and NVIDIA Container Toolkit.

## ZIP format

The ZIP must contain `model/model.pt` and `model/config.json`; `model/tokenizer.json` is optional. The server uses PyTorch `weights_only=True`, validates architecture bounds, rejects unsafe ZIP paths and symlinks, and limits uploads/unpacked size. Only upload model archives you trust.

## API

All endpoints except `GET /health` require `Authorization: Bearer <NEXUS_API_TOKEN>`.

- `GET /api/models` — list loaded models.
- `POST /api/models/upload` — multipart field `file`, ZIP archive.
- `POST /api/chat` — JSON `{"model_id":"...","prompt":"...","max_new_tokens":160}`.
- `DELETE /api/models/{model_id}` — remove a model.

The browser stores the API token only in the current page's memory. Use a private deployment and keep the token secret. For a public multi-user service, add user accounts, per-user quotas and server-side rate limiting before opening it to everyone.

## Important

GitHub Pages is static hosting: it cannot run model inference or permanently store uploaded model files. The separate VPS runs inference and keeps model files on its persistent volume. GitHub Actions remains useful for training jobs and downloadable artifacts, not as an always-on inference host.
