# RankedHit / retrieval contract (greenfield)

**Status:** Stage 1–2 — align with [wines_schema.md](wines_schema.md) / [wines_repository.md](wines_repository.md). Policy details: [eval_predict.md](eval_predict.md), [ocr_engine.md](ocr_engine.md).

## RankedHit

```python
class RankedHit(TypedDict):
    wine_id: int
    slug: str
    score: float       # higher better; encoder cosine (SigLIP2); comparable within one query
    title: str
    manufacturer: str
    category: str
    image_path: str    # or image_url public path /static/wines/...
    grape_variety: NotRequired[str]   # used by confident OCR rerank evidence
```

## Encoder preprocess (must equal training)

| Key (`database.yaml` → `dino:`) | SigLIP2 value | Note |
|---|---|---|
| `input_size` | 256 | |
| `resize_mode` | `letterbox` | longest side → `input_size`, centered, pad `pad_fill_rgb`; `stretch` = legacy DINO |
| `pad_fill_rgb` | `[123, 116, 103]` | same as notebooks (`PadIfNeeded`) |
| `normalize_mean` / `normalize_std` | `[0.5]*3` / `[0.5]*3` | after `/255` |
| `l2_normalize` | true | |

ONNX output `pooler_output [B, embedding_dim]`; encoder refuses to start if the static output dim ≠ `embedding_dim`.

## IRetriever

```python
class IRetriever(Protocol):
    def retrieve(self, image_path: str, *, top_k: int) -> list[RankedHit]: ...
```

Implementation: YOLO crop → encoder ONNX (`DinoOnnxEncoder` class, SigLIP2 weights) → `search_by_embedding`.

**Catalog vs query (SSOT):**

| Path | Image for DINO | Full bottle file |
|------|----------------|------------------|
| Catalog import | YOLO label crop required for insert (`data/tmp/catalog_crops/{slug}.webp`) | `static/wines/{slug}.*` for UI only (`image_url`) |
| Query / eval | YOLO crop; **fallback = full frame** if no/empty box (log at **ERROR**, `used_fallback` in decision JSONL) | N/A |

Do **not** insert a wine embedding from a full-frame catalog shot when the crop failed or is too small (`min_crop_side`) — quarantine under `data/tmp/catalog_crops_review/` instead. Not SIFT. Not FAISS file.

**YOLO `select_label_box` (keep):** candidates with `score >= confidence`; prefer frame-area fraction in `[box_area_min, box_area_max]` and `conf >= max_conf * box_conf_keep_ratio`; among those maximize `conf * (1 - dist_to_center)`; else max confidence; no candidates → query fallback / catalog review.

## Policy input/output (Stage 2)

- In: `list[RankedHit]`; OCR via [`IOCREngine`](ocr_engine.md); flags `enable_rerank`, thresholds `top_k` / `margin_min` / `abs_min`.
- Out (**eval**): always `slug` when candidates exist (see [eval_predict.md](eval_predict.md)); scores only in structured logs.
- Out (**product**, Stage 3): one wine card or not_found (+ analogs later); may use `abs_min` / not_found gate.

OCR/rerank reuses `FuzzyReranker` (`src/core/text/fuzzy.py`) on the shortlist only. Text backend for lines: `phocr` or `llm` adapter — same `list[str]`.
