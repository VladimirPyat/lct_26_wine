# Eval predict API + orchestrator (Stage 2B)

**Status:** approved (Phase B instructions ready).  
**Depends on:** [retrieval.md](retrieval.md), [ocr_engine.md](ocr_engine.md), [wines_repository.md](wines_repository.md).  
**Harness:** `data/owner_eval/<set>/participant_test.sh` (canonical; not `_migration/eval_organizer`).

## HTTP

| Item | Spec |
|------|------|
| Method / path | `POST /v1/eval/predict` |
| Body | `multipart/form-data`, field name **`image`** |
| Success | HTTP `200` or `201` |
| JSON | `{"slug":"<string>"}` or `[{"slug":"<string>"}]` (script takes first element) |
| Low confidence | **Always** return best available slug — **never** omit slug / return null because of `abs_min` or margin |
| Empty catalog / hard failure | Prefer structured 5xx or still best-effort; document choice in implementation. Organizer maps non-2xx / empty slug → `predicted_slug: null` in JSONL |

### Example

```json
{"slug": "agora-muskat-chernyj"}
```

## Pipeline

1. Persist upload to a temp path (or bytes → cropper API).
2. YOLO crop (existing cropper) → crop image.
3. Image encoder (ONNX, `config/database.yaml`; SigLIP2 since SIG plan) → embedding.
4. `search_by_embedding(embedding, top_k=policy.top_k)` → `list[RankedHit]`.
5. **Decision policy** (below) → winner slug.
6. Response: `{"slug": winner}` only (no scores in HTTP body).
7. Emit **structured decision log** (separate from response).

## Policy knobs (YAML)

```yaml
policy:
  top_k: 5
  margin_min: 0.08
  abs_min: 0.2
  enable_rerank: true
  rerank_mode: confident
  strong_combos: [[manufacturer, grape], [manufacturer, brand]]
  max_img_drop: null
```

| Key | Default | Meaning |
|-----|---------|---------|
| `top_k` | `5` | pgvector candidates; also rerank pool size |
| `margin_min` | `0.08` (was `0.1`) | If `score_1 - score_2 >= margin_min`, skip rerank. **Higher = more OCR calls** |
| `abs_min` | `0.2` | If `score_1 < abs_min`, flag **garbage** in logs; **still** return top-1 slug for eval |
| `enable_rerank` | `true` | If `false`, never call OCR/fuzzy (A/B testing) |
| `rerank_mode` | `confident` (code default `always`) | `always`: text leader wins. `confident`: see below |
| `strong_combos` | manufacturer+grape, manufacturer+brand | Signal sets OCR must confirm for the text leader |
| `max_img_drop` | `null` | Optional: keep image top-1 if `score_1 - score(leader) >` value |

Evidence stop lists live in `hybrid.fuzzy`: `producer_stopwords`, `generic_title_tokens`.

Eval does **not** use `enable_not_found_gate` (product Stage 3). Flag may exist in config but must not null out eval slug.

### Decision algorithm

```
hits = retrieve(top_k)
if empty:  # document: error or impossible in loaded catalog
  fail or raise

score_1 = hits[0].score
score_2 = hits[1].score if len(hits) > 1 else score_1
margin = score_1 - score_2
garbage = score_1 < abs_min

if not enable_rerank or margin >= margin_min or len(hits) == 1:
  winner = hits[0].slug
else:
  lines = ocr.recognize(crop_path)
  leader = fuzzy_rerank(hits, lines)[0]      # FuzzyReranker on shortlist
  if rerank_mode == "always":
    winner = leader.slug
  else:                                      # confident
    winner = leader.slug if confident(hits[0], leader, lines) else hits[0].slug

return winner  # always a slug when hits non-empty
```

**`confident(top, leader)`** — all must hold (`FuzzyReranker.label_evidence` per candidate):

1. `leader != top` (else reason `text_agrees`).
2. Leader signals ⊇ one of `strong_combos` (else `weak_text`). Signals:
   - `manufacturer` — compact producer string ≥ `mfr_compact_high`, or a producer token not in `producer_stopwords`;
   - `grape` — every token of one name from `grape_variety` (comma list) found in OCR;
   - `brand` — title tokens that are not grape / producer / `generic_title_tokens` / digits, found in OCR.
3. Leader has a confirmed grape/brand token **absent** from top's grapes/title (else `not_distinguishing`).
4. Top has no such token of its own vs leader (else `text_conflict`).
5. `max_img_drop` guard if set (else `img_drop`). Pass → `strong_text`.

## Structured logging

Per request, log (JSON line or dedicated logger), including at least:

- top-k: `slug`, `score` for each hit
- `margin`, `abs_min`, `garbage` flag
- `enable_rerank`, `rerank_triggered`
- `ocr.engine` (and `llm_task` if llm)
- OCR lines truncated (optional length cap)
- winner before/after rerank if rerank ran
- `rerank_mode`, `rerank_reason`, `text_leader`, `text_scores`, `evidence` (confident mode)
- `encoder_model` (ONNX file name), `embedding_dim`
- latency breakdown (crop / encode / search / ocr / rerank / total)

Eval HTTP body stays slug-only. Report script: `scripts/collect_eval_report.py` reads log file (+ optional `mapping.json`) → hit@1, rerank rate, garbage rate, latency p50/p95.

## Owner eval flow

1. API up: `uv run uvicorn api.main:app --app-dir src --host 0.0.0.0 --port 8080`
2. Set 1 harness (see `tooling.mdc`), then set 2.
3. Compare `predictions.jsonl` to `mapping.json` / golden for hit@1; golden latency may be `0`.

## Anti-cheat canary (tests)

After an honest hit@1 check against real `predictions.golden.jsonl` / `mapping.json`:

1. Copy golden to a **temp** path (never overwrite the committed golden).
2. Permute `predicted_slug` across rows so correct pairs are broken.
3. Re-run the same comparator → **must fail** (near-zero hit@1).

If the swapped comparison still “passes”, the test harness is invalid. See `tester_2b_eval.md`.

## Out of scope

- Product card / analogs / UI not_found (Stage 3+).
- Calibrating thresholds beyond starting defaults (YAML-only later).
