# OCR engine (Stage 2)

**Status:** approved (Phase B instructions ready). **Changed 2026-09-28** (owner decision D): startup engine fallback chain — see «Engine selection».  
**Depends on:** existing [`IOCREngine`](../../src/core/ocr/base.py); LLM path → [llm_engine.md](llm_engine.md).

## Contract (unchanged)

```python
class IOCREngine(ABC):
    def recognize(self, image_path: str) -> list[str]:
        """Return recognized text lines from a label/crop image."""
```

Same input/output for **all** backends so the orchestrator and `FuzzyReranker` do not care which engine is used.

## Backends

| `ocr.engine` | Implementation | Notes |
|--------------|----------------|--------|
| `phocr` | `PHOCREngine` | Local ONNX; used only when CUDA is available (see chain) |
| `llm` | Adapter over `create_llm_engine(ocr.llm_task)` | Default task name `ocr_label`; vision → `text_lines` |
| `mock` | `MockOCREngine` | Tests; empty lines |

Config knobs (`config/ocr_rerank.yaml`, defaults **unchanged**):

```yaml
ocr:
  engine: phocr          # phocr | llm | mock
  llm_task: ocr_label    # used when the effective engine is llm
  # existing phocr knobs: lang, limit_side_len, …
```

## Engine selection (fallback chain, whole app: eval + product)

Resolved **once at startup** (runtime build); the heavy engine may still be constructed lazily on first use.
Effective engine ∈ `phocr | llm | mock | none`.

| Configured `ocr.engine` | Condition | Effective | Reason logged |
|---|---|---|---|
| `phocr` | CUDA available | `phocr` (`use_cuda=True`, exactly as before) | `cuda_available` |
| `phocr` | CUDA not available | `llm` (task `ocr.llm_task`) | `no_cuda` |
| `phocr` / `llm` | LLM selected but unavailable (missing / empty API key, task YAML error, client init error) | `none` | `llm_unavailable: <error summary, no secrets>` |
| `llm` | LLM available | `llm` (no CUDA check) | `configured_llm` |
| `mock` | — | `mock` | `configured_mock` |

- **CUDA available** = `compute.device == "cuda"` **and** CUDA is actually usable by ONNX Runtime. `ort.get_available_providers()` alone is not enough (the GPU wheel lists `CUDAExecutionProvider` even with `CUDA_VISIBLE_DEVICES=""`); confirm via the already-built image-encoder session's active providers (`session.get_providers()` contains `CUDAExecutionProvider`) or an equivalent probe that creates no new model files. `compute.device: cpu` → not available.
- One INFO log line at startup: configured engine, effective engine, reason.
- GPU path (`phocr` + CUDA): same `PHOCREngine` arguments, same lazy construction, same rerank inputs → eval output **byte-identical** to before.
- **Effective `none`:** `runtime.get_ocr()` returns `None`; the eval policy **skips rerank** (vector decision stands; `rerank_triggered=False`, `rerank_reason="ocr_unavailable"`); product hints = `OcrHints(ocr_ran=False)` → unknown-wine analogs empty ([`product_api.md`](product_api.md) §4.2). No exception reaches the request.
- **Per-request LLM failure** (retries exhausted, non-retryable HTTP, empty content): the LLM OCR path raises a dedicated `OCRUnavailableError` (new, `core/ocr/base.py`); the policy catches **only** this type → same as `none` for that request (`rerank_reason="ocr_failed"`), product hints `ocr_ran=False`. PHOCR errors are **not** caught (GPU behaviour unchanged).
- No per-request re-selection (no switch from LLM back to PHOCR, no retry of `none`); restart re-evaluates.
- No new packages, no config default changes, no `auto` value — full GPU/CPU profiles = backlog `CFG-DEVICE-001`.

## LLM OCR behavior

- Prompt (markdown under `src/llm/prompts/`): extract **only** text visible on the label; **no** invented brand/year/grape.
- Parse model response into `list[str]` (non-empty lines; strip blanks) — compatible with PHOCR consumers.
- Retries / missing API key: per [llm_engine.md](llm_engine.md); missing key at startup → effective `none` (above), never a crash.

## Factory

`create_ocr_engine(...)` keeps building one named backend (no provider URLs in the OCR adapter — only `llm_task`).
The chain lives in a small pure selection function (inputs: configured engine, CUDA available, LLM factory/probe → effective engine + reason) called from `api/runtime.py`, unit-testable without GPU / network.

## Out of scope

- Changing `FuzzyReranker` API.
- Using VL as a slug judge (pick among candidates without fuzzy) — not this stage.
- PHOCR on CPU as a chain step (PHOCR recognition needs CUDA in practice; 5–7 s/request on CPU).
