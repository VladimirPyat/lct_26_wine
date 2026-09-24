# RankedHit / retrieval contract (greenfield)

**Status:** Stage 1 — align with [wines_schema.md](wines_schema.md) / [wines_repository.md](wines_repository.md).

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

Implementation: (optional YOLO crop) → DINO ONNX encode → `search_by_embedding`. Catalog load may encode **without** YOLO when source shots are already bottle crops. Not SIFT. Not FAISS file.

## Policy input/output

- In: `list[RankedHit]`, optional OCR lines, flags `enable_ocr_rerank`, `enable_not_found_gate`.
- Out (eval): `slug | None` (+ optional margin fields for debugging).
- Out (product): one wine card or not_found (+ analogs later).

OCR path reuses `FuzzyReranker` from `migration/text/fuzzy.py` on the shortlist only.
