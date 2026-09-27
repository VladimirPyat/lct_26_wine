# Test report — SIG: SigLIP2 encoder + OCR confident rerank

**Branch:** `feat/siglip-prod` · **Date:** 2026-09-28 · **Verdict:** TEST_PASS (offline scope); DB-backed tests env-skipped; rollout (E) not run — awaiting ✅.

## Commands

| Command | Exit | Result |
|---|---|---|
| `uv run ruff check src/ tests/` | 0 | clean |
| `uv run bandit -r src/ -ll` | 0 | clean |
| `uv run pytest tests/ -v` | 1 | 74 passed, 10 failed — see below |
| `uv run python scripts/eval_ocr_gate.py --margins 0.08` | 0 | table below |

Failures (none caused by SIG code):

- 9 × DB-backed (`test_wine_repository.py` 6, `test_catalog_load.py::TestCatalogImportDb` 3): `psycopg.OperationalError: password authentication failed for user "vine"` → **env-skipped**, not passes. Need Compose Postgres + valid `DATABASE_URL`.
- 1 × `test_owner_eval_scoring.py::test_owner_eval_set1_predictions_hit_at_1`: stale artifact `data/owner_eval/1/predictions.jsonl` (2026-09-24, pre-SIG) has null slug for `q-000026`. Test and data unchanged vs HEAD; resolves after rollout step E4 regenerates predictions.

## A. Existing tests fixed

- `test_wine_repository.py`, `test_catalog_load.py`: `768` → `load_database_settings().embedding_dim`.
- `test_compute_opt.py::test_dino_encoder_ctor_rejects_encode_batch_size_below_one`: `tmp_path` dummy model + patched `InferenceSession` (output shape `[None, 4]`); no dependency on `bin/`.

## B. `tests/test_encoder_preprocess.py` (16 cases, pass)

- letterbox 100×200 → 256×256, content rows 64..191, pad rows = `(123,116,103)`
- script `_letterbox is letterbox_rgb` + byte-equal arrays; encoder CHW == script `_preprocess(letterbox)` CHW (PNG file)
- `resize_mode` default `stretch`; stretch CHW == plain `cv2.resize` + normalize
- validator: letterbox without `pad_fill_rgb`; channel 256 / −1; unknown mode
- prod `database.yaml` == `bin/siglip2_wine_p1_epoch_3_preprocess.json` (skip if json absent)
- mean/std 0.5: 255 → 1.0, 0 → −1.0
- dim guard: `[None, 1152]` + config 768 → `RuntimeError` (message has both dims + model name); symbolic `["batch","dim"]`, `[None,None]`, `[]` → no error; match → ok

## C. `tests/test_policy_confident.py` (18 cases, pass)

Real `FuzzyReranker` from `config/ocr_rerank.yaml`, mocked OCR, Agora Yachting SKUs from the catalog.

| Case | Input | Expected reason / winner |
|---|---|---|
| always | Shiraz top-1, OCR `AGORA CABERNET SAUVIGNON YACHTING` | `always`, Cabernet |
| text_agrees | Cabernet top-1 | `text_agrees`, Cabernet |
| weak_text | top-1 «Бастардо» (AGORA WINERY), OCR `AGORA` | `weak_text`, keep top-1 |
| strong_text | Shiraz top-1, Cabernet candidate | `strong_text`, Cabernet (grape «каберне совиньон») |
| not_distinguishing | top-1 grape «Каберне Совиньон, Мерло» | keep top-1 |
| text_conflict | OCR also `SHIRAZ` | keep top-1 |
| img_drop | `max_img_drop=0.02`, drop 0.05 | keep top-1; within limit → switch |
| margin ≥ margin_min | margin 0.10 | OCR factory not called |
| decision log | tmp JSONL | `rerank_reason`, `text_leader`, `evidence`, `encoder_model`, `embedding_dim` |

`label_evidence`: «Пино Гри» needs both tokens; vintage digits never brand; producer stopwords alone (`ВИНОДЕЛЬНЯ`, `ESTATE`, `ПОМЕСТЬЕ`) → no manufacturer; core word `ФАНАГОРИЯ` → manufacturer; `GOLUBITSKOE` confirms «Поместье Голубицкое».

**Bug found:** stopword-only OCR (`ВИНОДЕЛЬНЯ` for «Винодельня Фанагория», `ПОМЕСТЬЕ` for «Поместье Голубицкое») confirmed the manufacturer via compact `partial_ratio`. Fixed in `FuzzyReranker.label_evidence` (compact check on manufacturer minus `producer_stopwords`). Offline regression output identical before/after.

Note: `test_prod_policy_is_confident` does not pin `margin_min` — `config/ocr_rerank.yaml` was changed to `0.06` in the working tree by a parallel, uncommitted edit (not part of SIG). Manuals document `0.08` per plan; reconcile before commit.

## Extra — `tests/test_catalog_clean_prepare.py` (3 cases, pass)

Rebuild prep from `data/clean` (no DB): ready / rejected split (`missing_image_file`, `image_missing_or_unreadable`, `duplicate_slug`, `missing_slug`), `image_source=clean`; `resolve_source_image` for `clean`; `--csv` repeatable.

Real data: `scripts/rebuild_catalog_db.sh --prepare-only` → 2103 rows, 2037 ready, 66 rejected (all `missing_image_file`, «Файл существует = нет»). Without `--yes` the script exits 3 before touching the DB.

## D. Offline regression (no DB)

`uv run python scripts/eval_ocr_gate.py --margins 0.08` (cached OCR `agent_docs/reports/ocr_lines_dev_crops.json`):

| model | margin | mode | R@1 | ocr | fixed | broken |
|---|---|---|---|---|---|---|
| siglip2_wine_p1_epoch_3 | 0.08 | off | 49/51 | 0 | 0 | 0 |
| siglip2_wine_p1_epoch_3 | 0.08 | always | 45/51 | 15 | 0 | 4 |
| siglip2_wine_p1_epoch_3 | 0.08 | confident | **49/51** | 15 | 0 | **0** |

Matches expectation (confident 49/51, broken 0).

Offline parity (Coder smoke, CPU): API encoder vs `compare_dino_onnx.py` letterbox embedder on 3 Dev-A crops — cosine 1.000000 each.

## E. Rollout checks

Not run — awaiting user ✅ (SIG-007). Prepared entrypoint: `scripts/rebuild_catalog_db.sh --yes` (prepare → `VINE_RESET_EMBEDDINGS=1 alembic upgrade head` → `catalog_import.py --csv wines_clean_ready.csv --crop-first --recreate-wines`); manual steps in `manuals/quickstart.md` «Перезаливка каталога».
