# Plan — SIG: production switch DINO → SigLIP2 (+ OCR confident rerank sync)

**Branch:** `feat/siglip-prod`  
**Status:** Phase B instructions written 2026-09-27; @Coder starts after user ✅ (rollout steps with DB reset need a separate ✅).  
**Evidence:** [`../reports/siglip2_embedding_results.md`](../reports/siglip2_embedding_results.md),
[`../reports/siglip_prod_migration_audit.md`](../reports/siglip_prod_migration_audit.md),
[`../reports/ocr_rerank_proposals_siglip.md`](../reports/ocr_rerank_proposals_siglip.md).

## Why

Offline on YOLO crops (same as API): SigLIP2 `siglip2_wine_p1_epoch_3` — R@1 49/51, R@5 51/51 (Dev-A + Dev-B);
DINOv2-L phase1 — R@1 ≈ 0.75, R@5 0.96 / 0.92. Prod config still points to a DINO file that is not in `bin/`.

## Locked decisions

| Topic | Decision |
|---|---|
| Model artifact | `bin/siglip2_wine_p1_epoch_3.onnx` (+ `_preprocess.json`), output `pooler_output [B,1152]`, fp32 |
| Preprocess | letterbox longest side → 256, pad RGB `(123,116,103)`, `/255`, mean/std `0.5`, L2 — must equal training |
| Code identifiers | keep `DinoOnnxEncoder`, `dino_model_path`, `dino:` block (rename = separate refactor, out of scope) |
| Backward compat | new preprocess keys have defaults (`resize_mode: stretch`) so a DINO config still works |
| Embedding dim | from `database.yaml` (`1152`); encoder fails fast if ONNX static output dim ≠ config |
| DB | alembic `0002`: change `wines.embedding` to `vector(<config dim>)`; refuses non-empty table unless `VINE_RESET_EMBEDDINGS=1` |
| Catalog vectors | full reimport from YOLO crops (`--crop-first --recreate-wines`) — **HITL / explicit user ✅** |
| OCR policy | already on master (`5c34275`): `margin_min 0.08`, `rerank_mode: confident`, `strong_combos` manufacturer+grape / manufacturer+brand. This stage: docs + tests only |
| Rollback | revert branch + restore DINO block (kept as comment in `database.yaml`) + `alembic upgrade` + reimport |

## Work items

| ID | Owner | Item |
|---|---|---|
| SIG-001 | Coder | Encoder: `resize_mode: stretch\|letterbox`, `pad_fill_rgb`; letterbox identical to `scripts/compare_dino_onnx.py::_letterbox`; ONNX output-dim fail-fast |
| SIG-002 | Coder | `config/database.yaml` → SigLIP values; DINO values kept as rollback comment |
| SIG-003 | Coder | Alembic `0002_embedding_dim` (guarded) |
| SIG-004 | Coder | Decision log: `encoder_model`, `embedding_dim` |
| SIG-005 | Coder | Manuals / README / `config/README.md` (SigLIP + OCR confident; fix inverted «Чаще OCR» hint) |
| SIG-006 | Tester | Unit: preprocess, settings, dim fail-fast, `label_evidence`, confident policy; fix hardcoded 768 / missing-model tests |
| SIG-007 | Human ✅ → Coder/Tester | Rollout: migrate, reimport, owner_eval 1/2 via API, latency |

## Out of scope (backlog)

- Renaming `dino_*` → `encoder_*`; fp16 / quantized export; HNSW index (2k rows — seq scan OK).
- Catalog SKU dedupe (e.g. `alma-valley-shardone-rezerv-beloe-suhoe-14` / `-135`) — data ticket.
- `abs_min` recalibration for SigLIP (only matters for Stage 3 not-found gate).
- Color as a rerank signal (Endemy red vs rosé).
