# NEXUS OS

A responsive GitHub Pages workspace with GitHub Actions build workflows.

## NEXUS AI Lab

NEXUS AI is a small experimental GPT-style causal language model trained **from random initialization**. It does not load or fine-tune a pretrained Hugging Face model.

- **NEXUS-10M:** approximately 10.8 million parameters.
- **NEXUS-100M:** approximately 100 million parameters; CPU training may exceed hosted-runner time or memory limits.
- Byte-level UTF-8 tokenizer with 260 token IDs.
- Training data: JSONL, one object per line, for example `{"text":"Example training text."}`.
- GitHub Actions trains the model, runs a generation test, and uploads `nexus-ai-model.zip` for 14 days.
- The ZIP contains standalone weights (`model.pt`), model configuration, tokenizer description, and `test-report.txt`.

### Train and test
1. Add a sufficiently large and varied corpus to `data/train.jsonl`.
2. Open the AI Lab on the NEXUS OS website and choose 10M or 100M.
3. Click **Запустить обучение** and then **Run workflow** on GitHub.
4. Set the dataset path, training steps, and test prompt.
5. When the run completes, download `nexus-ai-model` from the workflow's Artifacts section.

A tiny sample dataset is only enough to validate the pipeline; it cannot produce a useful general-purpose assistant. More training text, compute, and evaluation are required. The GitHub-hosted runner is temporary CPU infrastructure, not a persistent GPU server. The static GitHub Pages site cannot host an always-on inference server; testing is performed by the workflow and the generated report is included in the downloadable ZIP.

## Build workspace
- Android APK, Java JAR, Windows EXE and Minecraft mod workflows.
- GitHub Actions runners are temporary machines. Outputs are downloadable artifacts, not persistent desktop sessions.

## Security
Do not commit passwords, access tokens, signing keys, or private credentials. Keep secrets in GitHub Actions Secrets.
