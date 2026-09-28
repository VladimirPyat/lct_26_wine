# Contracts index

| File | Scope |
|------|-------|
| [wines_schema.md](wines_schema.md) | Postgres tables, lookups, embedding, storage paths |
| [wines_repository.md](wines_repository.md) | CRUD, slug, vector top-K, attribute filters |
| [catalog_prepare.md](catalog_prepare.md) | ready / additional / rejected CSV rules |
| [retrieval.md](retrieval.md) | RankedHit, IRetriever, policy I/O |
| [llm_engine.md](llm_engine.md) | Stage 2A: OpenAI-compatible client, task YAML, retries, no provider registry |
| [ocr_engine.md](ocr_engine.md) | Stage 2: IOCREngine backends phocr \| llm |
| [eval_predict.md](eval_predict.md) | Stage 2B: `/v1/eval/predict`, orchestrator, logs, owner_eval |
| [compute_opt.md](compute_opt.md) | OPT-001/002: DINO `encode_batch_size`, YOLO `cropper.device` |
| [product_api.md](product_api.md) | Stage 3: `ProductService` DTOs/Protocol, `/api/v1/*`, analogs, dictionaries, feedback, query storage |
| [web_ui.md](web_ui.md) | Stage 4: Jinja2 pages, result states, responsive, browser cabinet |

Plans: [`../plans/stages.md`](../plans/stages.md), [`../plans/opt_001_002.md`](../plans/opt_001_002.md). Drafts: `../drafts/` (decision_policy, infra_postgres, models_onnx, streams, greenfield).
