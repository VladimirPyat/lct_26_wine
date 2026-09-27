# @Coder — SIG: switch production encoder to SigLIP2

**Branch:** `feat/siglip-prod` (do not work on `master`).  
**Plan:** [`../plans/siglip_prod.md`](../plans/siglip_prod.md)  
**Contracts:** [`../contracts/retrieval.md`](../contracts/retrieval.md) (encoder preprocess), [`../contracts/wines_schema.md`](../contracts/wines_schema.md) (embedding dim), [`../contracts/eval_predict.md`](../contracts/eval_predict.md) (policy + log fields).  
**Artifacts (already in `bin/`, gitignored):** `siglip2_wine_p1_epoch_3.onnx`, `siglip2_wine_p1_epoch_3_preprocess.json`.

## Goal

API / catalog import encode with SigLIP2 using exactly the training preprocess (letterbox 256, mean/std 0.5, L2),
`embedding_dim = 1152`, guarded DB migration. OCR confident rerank is already implemented (commit `5c34275`) — only docs here.

**Do not** run the migration or the catalog reimport against the developer DB — that is rollout (SIG-007) and needs explicit user ✅.

## Steps

### SIG-001 — Encoder preprocess + fail-fast (`src/core/config.py`, `src/core/retrieve/dino_encoder.py`)

1. `DinoPreprocessSettings`: add
   - `resize_mode: Literal["stretch", "letterbox"] = "stretch"` (default keeps legacy DINO behaviour);
   - `pad_fill_rgb: tuple[int, int, int] | None = None`; validator: required when `resize_mode == "letterbox"`, each 0..255.
2. `DinoOnnxEncoder._preprocess_chw`: branch on `resize_mode`. Letterbox must be **byte-identical** to
   `scripts/compare_dino_onnx.py::_letterbox` (scale = size / max(h, w); `round` for new w/h, min 1; `cv2.INTER_LINEAR`;
   centered with `(size - n) // 2`; fill in RGB order). Prefer extracting one pure helper (e.g. `core/retrieve/preprocess.py`
   `letterbox_rgb(rgb, size, fill)`) and importing it from the script too, so there is a single implementation.
3. In `__init__`: read `self._session.get_outputs()` for `pooler_output`; if its last dim is an `int` and ≠ `database.embedding_dim`
   → `RuntimeError` naming model path, ONNX dim, config dim. Symbolic dims → skip check.
4. Log line at init: add `resize_mode`.

### SIG-002 — Config (`config/database.yaml`)

```yaml
dino_model_path: bin/siglip2_wine_p1_epoch_3.onnx
embedding_dim: 1152
dino:
  input_size: 256
  resize_mode: letterbox
  pad_fill_rgb: [123, 116, 103]
  normalize_mean: [0.5, 0.5, 0.5]
  normalize_std: [0.5, 0.5, 0.5]
  l2_normalize: true
  encode_batch_size: 16
```

Values must match `bin/siglip2_wine_p1_epoch_3_preprocess.json`. Keep the previous DINO block as a commented **rollback** section
(model path, 768, 224, ImageNet mean/std, `resize_mode: stretch`). Update the header comment (probe source = SigLIP ONNX).
Also fix stale comments in `config/compute_cropper.yaml` / `config/README.md` («DINO» → image encoder, SigLIP2).

### SIG-003 — Alembic `alembic/versions/0002_embedding_dim.py`

- `down_revision = "0001_initial_schema"`.
- `upgrade()`:
  1. `target = load_database_settings().embedding_dim`.
  2. Current dim: `SELECT atttypmod FROM pg_attribute WHERE attrelid = 'wines'::regclass AND attname = 'embedding'` (pgvector stores dim in `atttypmod`).
  3. Equal → no-op (fresh DB created by `0001` with new config lands here).
  4. Else if `SELECT count(*) FROM wines` > 0: if env `VINE_RESET_EMBEDDINGS == "1"` → `DELETE FROM wines`; otherwise `RuntimeError`
     explaining: embeddings of another dim cannot be converted; rerun with `VINE_RESET_EMBEDDINGS=1` then reimport catalog.
  5. `ALTER TABLE wines ALTER COLUMN embedding TYPE vector(<target>)`.
- `downgrade()`: no-op with a docstring (dim is config-driven; to go back, change config and run upgrade logic again) — do not drop data.
- No vector index exists today; do not add one.

### SIG-004 — Decision log traceability

`src/api/eval_pipeline.py` (or `api/runtime.py`): add to the decision log `extra`: `encoder_model` (model file name from
`DatabaseSettings.dino_model_path`) and `embedding_dim`. Keep HTTP body unchanged.

### SIG-005 — Docs (Russian)

- `manuals/configuration_guide.md`:
  - encoder section: SigLIP2 values, `resize_mode` / `pad_fill_rgb`, dim fail-fast, rollback to DINO;
  - policy section: `margin_min: 0.08`, `rerank_mode`, `strong_combos`, `max_img_drop`, `producer_stopwords`, `generic_title_tokens`;
    **fix the inverted hint**: more OCR = **increase** `margin_min`;
  - dim change procedure: config → `VINE_RESET_EMBEDDINGS=1 uv run alembic upgrade head` → reimport.
- `manuals/architecture.md`: encoder = SigLIP2 (class name stays `DinoOnnxEncoder`), confident rerank branch in the decision diagram.
- `manuals/quickstart.md`: required files in `bin/`, migration + reimport commands, GPU note (`LD_LIBRARY_PATH` for ORT CUDA, see `agent_docs/reports/siglip2_embedding_results.md`).
- `README.md` stack line: DINO → SigLIP2 (+ YOLO ONNX).
- Keep `manuals/index.md` in sync if headings change.

### Not in scope

Renaming `dino_*` identifiers; catalog dedupe; `abs_min` calibration; fp16 export; vector index; any change to `FuzzyReranker`
scoring or `decision.py` logic (tests for it are @Tester's).

## Verification

```bash
uv run ruff check src/ scripts/
uv run mypy src/            # env stub errors for onnxruntime/phocr/numpy pre-exist — no new errors in touched files
uv run bandit -r src/ -ll
uv run pytest tests/test_policy_decision.py tests/test_compute_opt.py -v
```

Offline parity smoke (no DB): encode 3 files from `data/train_dataset/embed_train_data/dev_a/queries_crop/` with
`create_dino_encoder()` and with `scripts/compare_dino_onnx.py`'s embedder using `--preprocess-json`; cosine ≥ 0.9999 per image.
Record numbers in progress.

## Acceptance

- [ ] Letterbox path implemented once, used by encoder and script; stretch path unchanged
- [ ] Encoder refuses mismatched ONNX dim
- [ ] `database.yaml` = SigLIP values + DINO rollback comment
- [ ] `0002_embedding_dim` guarded; not executed on the dev DB
- [ ] Decision log has `encoder_model`, `embedding_dim`
- [ ] Manuals / README updated (incl. margin_min hint fix)
- [ ] Lint / bandit clean; parity smoke recorded

## Handoff

Append to `agent_docs/progress/stage_2.md`: `READY_FOR_TEST (SIG)` with commands + exit codes. Next: @Tester `tester_siglip_prod.md`.
