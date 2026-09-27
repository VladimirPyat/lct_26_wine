
## 2026-09-24 — Planner (Stage 2 Phase A)

- STATUS: CONTRACTS_DRAFT (await user ✅ before Phase B instructions)
- Contracts: `llm_engine.md`, `ocr_engine.md`, `eval_predict.md`; updated `retrieval.md`, `contracts/index.md`
- Drafts: `decision_policy.md` (eval always slug; top_k=5, margin_min=0.1, abs_min=0.2, enable_rerank)
- Plans: `stages.md` § Stage 2 split into 2A LLM / 2B Eval
- `.env.example`: OPENAI_API_KEY, QWEN_API_KEY only (no base_url/model in env)
- paths-access: `src/llm/` note (5a)
- Next: user ✅ on contracts → Phase B `coder_2a_*`/`tester_2a_*` + `coder_2b_*`/`tester_2b_*` + stub `manual_testing.md`

## 2026-09-24 — Planner (Stage 2 Phase B)

- STATUS: INSTRUCTIONS_READY
- Instructions:
  - `coder_2a_llm.md` → `tester_2a_llm.md`
  - `coder_2b_eval.md` → `tester_2b_eval.md`
- Stub: `manuals/manual_testing.md` linked from README + `manuals/index.md`
- Contracts marked approved; tooling: collect_eval_report + openai note for 2A
- Default LLM task provider: Qwen (`QWEN_API_KEY`); other providers later as reserve
- Next: @Coder starts `coder_2a_llm.md` and/or `coder_2b_eval.md` (phocr path). Dispatch order: 2A ∥ 2B(phocr); llm OCR needs 2A first.

## 2026-09-24 — Coder (Stage 2A LLM)

- STATUS: READY_FOR_TEST (2A)
- Delivered:
  - `src/llm/` — client (retries=3), engine, factory; task `ocr_label` (Qwen); prompt `ocr_label_v1.md`
  - `src/llm/adapters/ocr.py` — `LLMOCREngine` (`IOCREngine`)
  - `src/core/ocr/factory.py` — `create_ocr_engine(phocr|llm|mock)`; `ocr.llm_task` in YAML
  - `OcrSettings` / `load_ocr_settings` (integrated with 2B `OcrRerankSettings`)
  - Dep: `openai` under optional `ml`; manuals architecture + configuration_guide
- Lint (touched): `ruff check src/llm src/core/ocr src/core/config.py` OK; `bandit -ll` OK (no med/high)
- Next: @Tester `tester_2a_llm.md`

## 2026-09-24 — Tester (Stage 2A LLM)

- STATUS: TEST_PASS (2A)
- Report: `agent_docs/reports/test_stage_2a_llm.md`
- Commands: `pytest -k "llm or ocr"` → 8 passed, 1 skipped (exit 0); `ruff check src/ tests/` → exit 0
- Covered: missing key, retries ok/exhausted, no retry 401/403, OCR adapter list[str], factory phocr|llm|mock swap
- Next: Stage 2A done; 2B not started by this tester pass

## 2026-09-24 — Coder (Stage 2B Eval)

- STATUS: READY_FOR_TEST (2B)
- Delivered:
  - `WineRetriever` (`retrieve` / `retrieve_bundle`): YOLO → DINO → `search_by_embedding`
  - `core.policy.decide` + JSONL `emit_decision_log`; knobs in `config/ocr_rerank.yaml`
  - `POST /v1/eval/predict` (multipart `image` → `{"slug":...}`); empty catalog → 503
  - `scripts/collect_eval_report.py` (rerank/garbage rates, latency p50/p95, optional hit@1)
  - Manuals: architecture / configuration_guide / quickstart (uvicorn + owner_eval set1)
- Policy defaults: top_k=5, margin_min=0.1, abs_min=0.2, enable_rerank=true; ocr.engine=phocr
- Smoke: with `enable_rerank=false` → HTTP 200 slug + decision log + report script OK (~834ms)
- Soft block: `phocr` not in ml extras → see `agent_docs/reports/BLOCKED.md` (rerank path needs `uv add phocr` or llm)
- Lint: `ruff check src/` OK; `bandit -r src/ -ll` OK; mypy blocked by env numpy stubs (pre-existing)
- Next: @Tester `tester_2b_eval.md`

## 2026-09-24 — Unblock (phocr)

- STATUS: UNBLOCKED
- User approved `phocr`; added to `ml` extra + `tool.uv.override-dependencies` for numpy 2.x (PHOCR metadata still pins <=1.26)
- `uv sync --extra ml --extra db --extra dev` OK; `from phocr import PHOCR` OK
- Next: @Tester `tester_2b_eval.md`

## 2026-09-24 — Tester (Stage 2B Eval)

- STATUS: TEST_PASS (2B)
- Report: `agent_docs/reports/test_stage_2b_eval.md`
- Unit/API: policy margin/rerank/abs_min + HTTP smoke + canary — 10 pytest passed (`-k "eval or policy or predict"`)
- Owner eval (phocr, enable_rerank=true):
  - set1 hit@1=0.5556 (15/27); latency p50/p95 ≈ 5033/8889 ms; harness exit 0
  - set2 hit@1=0.7200 (18/25); latency p50/p95 ≈ 6016/8405 ms; harness exit 0
- Canary swapped golden: hit@1 near 0 (PASS)
- HITL: filled `manuals/manual_testing.md`
- Defects (non-blocking): `collect_eval_report.load_mapping` ignores `cases[]`; soft latency ~3s missed on CPU+phocr
- Next: stage sign-off; optional @Coder fix mapping loader

## 2026-09-24 — BugFixer (query crop fallback logging)

- Catalog vectors now YOLO crops (see stage_1 note); query no-box → full frame + ERROR log; decision JSONL includes `used_fallback` / `crop_path`
- Report: `agent_docs/reports/bug_catalog_yolo_encode.md`

## 2026-09-25 — Planner (OPT-001 / OPT-002)

- STATUS: INSTRUCTIONS_READY (OPT-001 / OPT-002)
- Contract: `agent_docs/contracts/compute_opt.md` (index updated)
- Plan: `agent_docs/plans/opt_001_002.md`; backlog tickets marked INSTRUCTIONS_READY (OPT-001 > OPT-002; no YOLO batch)
- Instructions:
  - @Coder `agent_docs/instructions/coder_opt_001_002.md` (A batch DINO, then B cropper.device, then manuals)
  - @Tester `agent_docs/instructions/tester_opt_001_002.md`
- Locked: `dino.encode_batch_size` in `database.yaml`; `cropper.device` default cpu; online YOLO stays CPU unless overridden; no new packages
- Next: @Coder `coder_opt_001_002.md`

## 2026-09-25 — Coder (OPT-001 / OPT-002)

- STATUS: READY_FOR_TEST (OPT-001 / OPT-002)
- OPT-001: `dino.encode_batch_size` (default 16); `DinoOnnxEncoder.encode_images` + import buffer; CLI `--encode-batch-size`
- OPT-002: `cropper.device` cpu|cuda|auto (default cpu); YOLO EP via `select_yolo_onnx_providers`; CLI `--cropper-device`
- Manuals: architecture / configuration_guide / quickstart (removed “YOLO always CPU”)
- Lint: `uv run ruff check src/` OK; `uv run bandit -r src/ -ll` OK
- Next: @Tester `tester_opt_001_002.md`

## 2026-09-25 — Tester (OPT-001 / OPT-002)

- STATUS: TEST_PASS (OPT-001 / OPT-002)
- Report: `agent_docs/reports/test_opt_001_002.md`
- Commands: pytest `-k "compute_opt or dino_batch or yolo_provider or encode_batch or cropper_device"` → 15 passed (exit 0); `ruff check src/ tests/` → exit 0
- Covered: encode_batch_size YAML/validator; encode_images length/None siblings/serial fallback/batch=1; encode_image raises; select_yolo_onnx_providers cpu|cuda|auto; default cropper.device=cpu; cropper≠compute device
- Manuals: architecture / configuration_guide / quickstart checked (no “YOLO всегда CPU”)
- Next: OPT-001/002 sign-off

## 2026-09-27 — Planner (SIG: SigLIP2 prod switch)

- STATUS: INSTRUCTIONS_READY (SIG) — branch `feat/siglip-prod`; @Coder starts after user ✅; rollout (DB reset + reimport) needs separate ✅
- Plan: `agent_docs/plans/siglip_prod.md`; audit: `agent_docs/reports/siglip_prod_migration_audit.md`
- Contracts updated: `retrieval.md` (encoder preprocess, `grape_variety`), `wines_schema.md` (dim 1152), `eval_predict.md` (confident rerank, log fields)
- Already on master `5c34275`: OCR `margin_min 0.08`, `rerank_mode: confident` (offline: SigLIP 49/51, 0 broken; `always` 45/51)
- Next: @Coder `coder_siglip_prod.md` → @Tester `tester_siglip_prod.md`
