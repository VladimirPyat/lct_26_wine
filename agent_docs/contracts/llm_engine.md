# LLM engine (Stage 2A)

**Status:** approved (Phase B instructions ready).  
**Scope:** OpenAI-compatible transport + named task configs. No provider registry.

## Layers

1. **Client (transport)** — OpenAI-compatible HTTP API (chat / vision; tools later).
2. **Task config** — one YAML per use-case under `src/llm/tasks/`. Provider settings are **inline** in that YAML (no central `providers.yaml` registry). Future multi-provider agent systems may add a registry later; not in this project now.

## Factory

```python
def create_llm_engine(task_name: str) -> LLMEngine:
    """Load src/llm/tasks/{task_name}.yaml + prompt file; resolve API key from env."""
```

Resolution order:

1. Load `src/llm/tasks/{task_name}.yaml` (missing file → error).
2. Read `provider` block: `name`, `base_url`, `api_key_env`, `model`.
3. `api_key = os.environ.get(api_key_env)` — if missing or empty → **`ValueError`** (fail fast; no silent fallback).
4. Load prompt markdown from `prompt_path` (relative to `src/llm/`).
5. Apply `retries` (default **3** if omitted).

Caller passes **only** `task_name`.

## Task YAML shape

```yaml
# src/llm/tasks/ocr_label.yaml
name: ocr_label
provider:
  name: qwen
  base_url: https://dashscope.aliyuncs.com/compatible-mode/v1
  api_key_env: QWEN_API_KEY
  model: qwen-vl-plus
retries: 3
modality: vision          # vision | text (text = no image)
prompt_path: prompts/ocr_label_v1.md
output:
  kind: text_lines        # parse model text → list[str] (PHOCR-compatible)
temperature: 0.0
```

| Field | Required | Notes |
|-------|----------|--------|
| `provider.*` | yes | Manually maintained per task; switch provider by editing this block + env key |
| `retries` | no | Default `3` |
| `modality` | yes | `vision` requires image input on invoke |
| `prompt_path` | yes | Markdown file; version by filename (`_v1`, `_v2`) |
| `output.kind` | yes | Task-specific; `text_lines` for OCR |

Reserved for later tasks (contract only, not implemented in 2A): e.g. `site_assistant` with tools / different `output.kind` — **separate** YAML, same factory.

## Prompts

- Directory: `src/llm/prompts/`.
- Content: instruction text for the model (Russian or English as needed by the task).
- Task YAML stores only the path; do not embed long prompts in YAML.

## Retries

- Default **3** attempts per LLM call.
- Retry on transient failures: connect/timeout, HTTP 408/429/5xx, and equivalent client transport errors.
- Do **not** retry on 4xx other than 408/429 (e.g. 401/403/422) — fail immediately.
- After all attempts fail: **log error** (task name, provider name, last status/message) and raise.

## Env (secrets only)

Documented in `.env.example`. **No** `BASE_URL` / `MODEL` in env.

```bash
OPENAI_API_KEY=sk-replace-me
QWEN_API_KEY=sk-ws-replace-me
```

`api_key_env` in YAML must match the variable name.

## Package layout

```
src/llm/
  client.py       # OpenAI-compatible + retries
  factory.py      # create_llm_engine
  engine.py       # LLMEngine protocol / impl
  tasks/          # *.yaml
  prompts/        # *.md
  adapters/       # e.g. OCR → IOCREngine
```

## Dependencies

Optional extra (approve at Phase B): `openai` **or** `httpx` for the compatible client. Prefer one library; declare in coder instruction. Unit tests mock HTTP — no live key in CI.

## Out of scope (2A)

- Provider registry.
- Eval HTTP / orchestrator (Stage 2B).
- Implementing `site_assistant` beyond documenting the pattern.
