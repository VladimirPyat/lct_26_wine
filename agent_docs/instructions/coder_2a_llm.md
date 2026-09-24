# @Coder — Stage 2A LLM foundation

**Contracts:** [`../contracts/llm_engine.md`](../contracts/llm_engine.md), [`../contracts/ocr_engine.md`](../contracts/ocr_engine.md)  
**Tester:** [`tester_2a_llm.md`](tester_2a_llm.md)  
**Parallel:** may run before/alongside 2B; 2B with `ocr.engine=phocr` does not require this slice.

## Goal

OpenAI-compatible LLM client + named task configs under `src/llm/`. First task: `ocr_label` (Qwen by default) exposing the same `IOCREngine` surface as PHOCR. **No** provider registry.

## Dependencies (approved)

```bash
uv add openai --optional ml
# or: add `openai` under [project.optional-dependencies] ml, then:
uv sync --extra ml --extra db --extra dev
```

Prefer the `openai` SDK against OpenAI-compatible base URLs. Do not add unrelated packages.

## Steps

1. **Package `src/llm/`**
   - `client.py` — OpenAI-compatible calls; **`retries` default 3**; retry connect/timeout, HTTP 408/429/5xx; after exhaustion log error (task + provider) and raise.
   - `engine.py` — thin engine API used by adapters.
   - `factory.py` — `create_llm_engine(task_name: str)` per contract: load `src/llm/tasks/{task_name}.yaml`, resolve `provider.api_key_env` from env → missing/empty **`ValueError`**, load prompt markdown.
   - Layout: `tasks/`, `prompts/`, `adapters/`.

2. **Task `ocr_label` (default provider = Qwen)**
   - Create `src/llm/tasks/ocr_label.yaml` with inline provider (Qwen DashScope-compatible URL, `api_key_env: QWEN_API_KEY`, vision model).
   - Prompt `src/llm/prompts/ocr_label_v1.md`: only visible label text, no invention; output parseable to lines.
   - `output.kind: text_lines` → `list[str]`.

3. **OCR adapter**
   - `src/llm/adapters/ocr.py` (or under `src/core/ocr/`): implements `IOCREngine.recognize` via `create_llm_engine("ocr_label")` (or `ocr.llm_task`).
   - Wire config: `ocr.engine: phocr | llm`, `ocr.llm_task: ocr_label`. Keep PHOCR path unchanged.
   - Do **not** put base_url/model in `.env` (keys only; see `.env.example`).

4. **Docs**
   - [`manuals/architecture.md`](../../manuals/architecture.md) — LLM layer vs OCR adapter vs future tasks.
   - [`manuals/configuration_guide.md`](../../manuals/configuration_guide.md) — task YAML, retries, `ocr.engine`, env key names (no secrets).

## Out of scope

- Eval endpoint / orchestrator (2B)
- Provider registry
- Live site_assistant task
- Reading or committing `.env`

## Acceptance

- [ ] `create_llm_engine("ocr_label")` works when `QWEN_API_KEY` set; **ValueError** if unset
- [ ] Retries: documented + implemented (default 3)
- [ ] `IOCREngine` adapter returns `list[str]`
- [ ] `ocr.engine` switches phocr ↔ llm without changing FuzzyReranker
- [ ] Manuals updated

## Handoff

Append `READY_FOR_TEST` (2A) to `agent_docs/progress/stage_2.md`. Lint gate before handoff (`ruff` / `bandit` on touched `src/`).
