# Progress (migration snapshot)

## 2026-09-22 — Planner
- STATUS: MIGRATION_SNAPSHOT_READY
- Created `migration/` with OCR, text/fuzzy, cropper, YOLO ONNX, config_samples, eval_organizer, owner_eval, agent_docs plans
- Stack lock: DINO ONNX + pgvector; SigLIP out; SIFT/VLAD not carried
- Next: new repository bootstrap from MANIFEST; add DINO ONNX + PHOCR weights into `bin/` manually

## 2026-09-22 — Planner (transfer-ready)
- STATUS: READY_TO_COPY
- PHOCR weights: from new venv after install (not in migration)
- DINO ONNX: user adds in new repo only
- Added support/types_for_adapt.py + TRANSFER_CHECKLIST.md
- Post-transfer development plan: deferred to next user message

## 2026-09-22 — Planner (staged roadmap)
- STATUS: STAGES_DRAFT
- Added migration/agent_docs/plans/stages.md
- Stages: 0 scaffold → 1 catalog/data → 2.0 eval API → 2.1 product search+analogs → 3 frontend → 4 product extras
- Stage 1 detail deferred to stage kickoff (CSV, scrape join by slug, low-res audit, YOLO crops, DINO fill)

## 2026-09-23 — Stage 0 bootstrap
- STATUS: STAGE0_DONE
- Copied from `_migration` → `src/core/{ocr,text,cropper}`, `config/`, `bin/` (YOLO), `data/owner_eval/`, `docs/`, `agent_docs/`
- Added FastAPI `/health`, `pyproject.toml`, `docker-compose.yml` (pgvector), `.env.example`, README
- Updated `.cursor/rules/paths-access.mdc` + `tooling.mdc` (no frontend; eval at `data/owner_eval/`)
- `_migration/` kept gitignored as backup; agents RO / not in normal workflow
- Next: discuss Stage 1 (catalog data + DINO); owner supplies CSV/photos/DINO ONNX
