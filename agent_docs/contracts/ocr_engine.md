# OCR engine (Stage 2)

**Status:** approved (Phase B instructions ready).  
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
| `phocr` | `PHOCREngine` | Local ONNX; primary path on GPU/dev |
| `llm` | Adapter over `create_llm_engine(ocr.llm_task)` | Default task name `ocr_label`; vision → `text_lines` |
| (tests) | `MockOCREngine` | Existing mock |

Config knobs (app / `config/ocr_rerank.yaml` or successor):

```yaml
ocr:
  engine: phocr          # phocr | llm
  llm_task: ocr_label    # used when engine=llm
  # existing phocr knobs: lang, limit_side_len, …
```

## LLM OCR behavior

- Prompt (markdown under `src/llm/prompts/`): extract **only** text visible on the label; **no** invented brand/year/grape.
- Parse model response into `list[str]` (non-empty lines; strip blanks) — compatible with PHOCR consumers.
- Retries / missing API key: per [llm_engine.md](llm_engine.md).

## Factory

Application code selects engine from config once at startup (or per request if tests need swap). Do not hardcode provider URLs in OCR adapter — only `llm_task` name.

## Out of scope

- Changing `FuzzyReranker` API.
- Using VL as a slug judge (pick among candidates without fuzzy) — not this stage.
