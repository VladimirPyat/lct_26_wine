# RankedHit / retrieval contract (greenfield)

**Status:** Stage 1–2 — align with [wines_schema.md](wines_schema.md) / [wines_repository.md](wines_repository.md). Policy details: [eval_predict.md](eval_predict.md), [ocr_engine.md](ocr_engine.md).

## RankedHit

```python
class RankedHit(TypedDict):
    wine_id: int
    slug: str
    score: float       # higher better; DINO cosine/IP; comparable within one query
    title: str
    manufacturer: str
    category: str
    image_path: str    # or image_url public path /static/wines/...
    # optional extras for analogs later
```

## IRetriever

```python
class IRetriever(Protocol):
    def retrieve(self, image_path: str, *, top_k: int) -> list[RankedHit]: ...
```

Implementation: YOLO crop → DINO ONNX encode → `search_by_embedding`. Catalog load may encode **without** YOLO when source shots are already bottle crops. Not SIFT. Not FAISS file.

## Policy input/output (Stage 2)

- In: `list[RankedHit]`; OCR via [`IOCREngine`](ocr_engine.md); flags `enable_rerank`, thresholds `top_k` / `margin_min` / `abs_min`.
- Out (**eval**): always `slug` when candidates exist (see [eval_predict.md](eval_predict.md)); scores only in structured logs.
- Out (**product**, Stage 3): one wine card or not_found (+ analogs later); may use `abs_min` / not_found gate.

OCR/rerank reuses `FuzzyReranker` (`src/core/text/fuzzy.py`) on the shortlist only. Text backend for lines: `phocr` or `llm` adapter — same `list[str]`.
