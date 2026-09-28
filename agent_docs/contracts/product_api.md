# Contract — Product API + `ProductService` (Stage 3)

**Scope:** photo → one wine card + confidence; analogs; catalog filters; dictionaries; search feedback.  
**Consumers:** JSON API `/api/v1/*` (backend branch) and Jinja UI `src/web/` (frontend branch) — both call the **same in-process `ProductService`**; UI never calls `/api/v1` over HTTP.  
**Not changed:** `POST /v1/eval/predict` (always `{"slug"}`, see [`eval_predict.md`](eval_predict.md)).  
**Changes:** 2026-09-28 owner decisions — analogs = same grape only, `vector` not produced (§4.2); OCR engine fallback chain ([`ocr_engine.md`](ocr_engine.md)).  
**Sources:** TZ gap ticket [`../reports/ticket_tz_gap_001_remaining_scope.md`](../reports/ticket_tz_gap_001_remaining_scope.md) items 1, 2, 8, 9; design review [`../reports/frontend_design_review.md`](../reports/frontend_design_review.md) §3–4.

---

## 1. Shared code (created once on `master` by `coder_prod_000_shared.md`)

| File | Content |
|---|---|
| `src/core/product/__init__.py` | re-exports |
| `src/core/product/schemas.py` | Pydantic v2 DTOs (§2) |
| `src/core/product/service.py` | `ProductService` Protocol (§3) + `SearchNotFoundError`, `UploadRejectedError` |
| `src/core/product/stub.py` | `StubProductService` — deterministic fixtures for UI development |
| `config/product.yaml` + `ProductSettings` / `load_product_settings()` in `src/core/config.py` | full file from §6 (placeholders); UI reads `upload`, backend reads everything |
| `src/api/main.py` | lifespan sets `app.state.product_settings = load_product_settings()` and `app.state.product_service = StubProductService()` (one line; backend branch swaps it for the real service) |

After this commit both branches **import** these types; changing a DTO = contract change → Planner.

## 2. DTOs (`src/core/product/schemas.py`)

**Color = `categories.name`** (`Красное` / `Белое` / `Розовое` / `Оранжевое`) everywhere in this API:
`WineCard.color`, `OcrHints.color`, `CatalogFilters.color`, `Dictionaries.colors`, `product.yaml` synonym keys.
DB column `wines.color` is a free-text shade («Тёмно-рубиновый») → exposed only as `WineCard.shade` (display, never filtered).

```python
ConfidenceLevel = Literal["high", "medium", "low"]
SearchStatus = Literal["found", "low", "not_found"]
AnalogSource = Literal["ocr_filters", "winner_filters", "vector"]   # "vector" reserved, not produced by the real service (§4.2)
Verdict = Literal["match", "mismatch"]

class WineCard(BaseModel):
    slug: str
    title: str
    manufacturer: str
    color: str                       # categories.name, e.g. "Красное"
    shade: str                       # wines.color, display only, e.g. "Тёмно-рубиновый"
    region: str
    grape_variety: str
    sweetness: str | None
    description: str
    public_rating: float | None
    product_url: str | None          # customer site page
    image_url: str                   # /static/wines/{slug}.webp
    dishes: list[str] = []
    alcohol_pct: float | None
    serving_temperature: str | None

class Candidate(BaseModel):          # vector top-K (TZ: confidence for top-1 and top-5)
    rank: int                        # 1..K
    slug: str
    title: str
    manufacturer: str
    image_url: str
    score: float                     # cosine, higher = better

class OcrHints(BaseModel):
    color: str | None = None         # categories.name, e.g. "Красное"
    grapes: list[str] = []           # values from dictionaries.grapes
    manufacturer: str | None = None  # exact catalog manufacturer
    ocr_ran: bool = False

class CatalogFilters(BaseModel):
    color: str | None = None         # categories.name
    grape: str | None = None
    region: str | None = None
    sweetness: str | None = None
    dish: str | None = None
    exclude_manufacturer: str | None = None
    exclude_slugs: list[str] = []

class AnalogsResult(BaseModel):
    source: AnalogSource
    filters: CatalogFilters          # what was applied (UI shows as removable chips)
    hints: OcrHints
    wines: list[WineCard]            # ≤ limit, sorted public_rating DESC NULLS LAST; may be empty (§4.2)
    total: int                       # matches before limit (UI: "показать все" → /catalog); 0 when empty

class SearchResult(BaseModel):
    search_id: str                   # uuid4 hex, unguessable
    created_at: datetime
    status: SearchStatus
    confidence_level: ConfidenceLevel
    score_1: float
    margin: float                    # score_1 - score_2
    winner: WineCard | None          # None only when status == "not_found"
    candidates: list[Candidate]      # always top-K (≤5), also for not_found
    analogs: AnalogsResult | None    # filled for low / not_found; None for found
    rerank_triggered: bool
    latency_ms: float

class Dictionaries(BaseModel):
    colors: list[str]                # categories.name
    grapes: list[str]                # normalized, blends split
    regions: list[str]
    sweetness: list[str]
    dishes: list[str]

class FeedbackIn(BaseModel):
    search_id: str
    slug: str | None = None          # wine the user judged (winner by default)
    verdict: Verdict
```

## 3. `ProductService` Protocol (`src/core/product/service.py`)

```python
class ProductService(Protocol):
    def search(self, image_path: Path, *, original_name: str | None = None) -> SearchResult: ...
    def get_search(self, search_id: str) -> SearchResult | None: ...
    def query_photo_path(self, search_id: str) -> Path | None: ...
    def analogs_for(self, search_id: str, *, limit: int = 5) -> AnalogsResult: ...   # SearchNotFoundError
    def get_wine(self, slug: str) -> WineCard | None: ...
    def find_wines(self, filters: CatalogFilters, *, limit: int = 5, offset: int = 0) -> tuple[list[WineCard], int]: ...
    def dictionaries(self) -> Dictionaries: ...
    def record_feedback(self, feedback: FeedbackIn) -> None: ...                    # SearchNotFoundError
```

- Methods are **sync** (CPU/GPU + DB); FastAPI routes call them via `run_in_threadpool`.
- `search` takes ownership of `image_path` (copies into query storage); caller deletes its temp file.
- Upload validation (size/type) is done by the caller before `search` using `product.upload` settings; service may raise `UploadRejectedError` for undecodable images.

### Stub behaviour (`StubProductService`)

- 5 fixture wines (different colors/grapes/manufacturers, one with `public_rating=None`, one without `product_url`).
- `search`: status chosen by `original_name`: contains `notfound` → `not_found`; `low` → `low`; else `found`/`high`. Stores results in memory; `search_id` uuid4.
- `find_wines` filters fixtures in memory, sorts by rating desc; `dictionaries` from fixtures; `record_feedback` appends to an in-memory list; `query_photo_path` returns the copied temp file.
- The stub may keep producing `source="vector"` (UI development only); the real service never does (§4.2, owner decision 2026-09-28).

## 4. Real implementation (backend branch)

`src/core/product/catalog_service.py::CatalogProductService(runtime)` — built in lifespan from the existing `EvalRuntime`.

### 4.1 `search`

1. Save upload → `{queries_dir}/{search_id}{ext}`.
2. Same pipeline as eval: `WineRetriever.retrieve_bundle` → `decide(...)` (OCR rerank rules unchanged). Refactor shared code out of `api/eval_pipeline.py` instead of duplicating; eval output must stay byte-identical (`owner_eval` regression).
3. `winner_slug = decision.slug`; `score_1`, `margin` from decision.
4. Level / status (thresholds in `config/product.yaml`, cosine of **image** top-1):
   - `score_1 < not_found_min` → `status=not_found`, `confidence_level=low`, `winner=None`;
   - else `score_1 ≥ high_min` → `high`; `≥ medium_min` → `medium`; else `low`;
   - `high|medium` → `status=found`; `low` → `status=low`.
5. `low` / `not_found` → analogs (§4.2, unknown wine: OCR grape only); `found` → `analogs=None` (no OCR call for analogs; OCR runs only if the eval rerank rules trigger it).
6. Persist `SearchResult` JSON → `{queries_dir}/{search_id}.json`; decision log line (add `score_1`, `score_2`, `search_id`, `status`, `confidence_level`, `endpoint: "product"`).

### 4.2 Analogs

**Owner decisions 2026-09-28** (supersede the earlier OCR-color / color-only / `vector` chain). Rule for both
cases: **one filter = one grape**; no fallback chain, no color-only retry, no vector analogs («не будем мудрить»).

| Case | `source` | Applied `filters` | OCR |
|---|---|---|---|
| **A. Known wine** — `found`, user pressed «Подобрать аналоги» (`analogs_for`) | `winner_filters` | `grape` = winner's first grape; `exclude_manufacturer = winner.manufacturer` (TZ: «из других виноделен»); `exclude_slugs=[winner.slug]`; `color` / `region` **not** set | **none** — characteristics from DB (`winner`) |
| **B. Unknown wine** — `low` / `not_found` (computed in `search`; `analogs_for` re-queries from the stored `analogs.hints`, no new OCR) | `ocr_filters` | `grape` = first OCR grape (`hints.grapes[0]`); `exclude_slugs=[winner.slug]` when a (low) winner exists, else `[]`; `color` / `manufacturer` **not** set | only source of the grape |
| A without a winner grape / B without an OCR grape (or OCR unavailable / failed) | same as the row above | `grape=None` (exclusions as above) | — |

Result rules:
- `grape` set → `find_wines(filters, limit)`: first `limit` by `public_rating DESC NULLS LAST` (then `id`), `total` = full count. `total == 0` → empty result, **no retry**.
- `grape is None` → **no DB query**; `wines=[]`, `total=0` (a filter without grape would return the whole catalog).
- Empty result keeps its `source` (`winner_filters` / `ocr_filters`); UI decides the message from `wines == []`.
- A: winner's first grape = `split_grapes(winner.grape_variety)[0]` canonicalized by the grape dictionary (§4.3, same split / normalization). Grape filter = whole element match (`grape_names_any`), so «Пино» ≠ «Пино Гри».
- `hints` (display / UI chips, never auto-applied): A → `OcrHints(color=winner.color, grapes=[grape] or [], manufacturer=None, ocr_ran=False)` (region is on `SearchResult.winner.region`); B → full OCR hints (`color`, `grapes`, `manufacturer`, `ocr_ran`). The UI may add color / region later as user-chosen filters via `find_wines`.
- `vector` is **reserved** in `AnalogSource` (kept so the parallel `feat/web-ui` stub keeps compiling) and **never produced** by `CatalogProductService`. The former rule «candidates rank 2..K» and its defect DEF-1 are obsolete.

OCR for B (hint extraction):
- Lines: reuse `decision.ocr_lines` if rerank ran and OCR succeeded; else OCR on the crop via the runtime OCR engine (see [`ocr_engine.md`](ocr_engine.md) «Engine selection»). No engine (`none`) or per-request OCR failure → `OcrHints(ocr_ran=False)` → empty analogs. Never raises into the request.
- Grape (the only field used as a filter): dictionary grapes, whole-name match like `label_evidence` (all tokens of the grape name present; «ПИНО» alone ≠ «Пино Гри»), across scripts: Cyrillic, Latin, transliteration (`core/text/normalize.py` aliases + `FuzzyReranker` fuzzy token match), plus a **product-only** Latin alias map `analogs.grape_aliases` in `product.yaml` (catalog grape → Latin / OCR spellings, e.g. `Санджовезе: [sangiovese]`, `Пино Нуар: [pinot noir, pinot nero]`), so imported labels («CABERNET SAUVIGNON», «SANGIOVESE», «PINOT NOIR») map to catalog names. Alias phrases also match whole-phrase only. Several grapes → most specific (more tokens) first, then dictionary order. The shared `_TOKEN_ALIASES` table in `normalize.py` is **not** extended here (eval reranker uses it; eval must stay byte-identical). Note: `ocr_rerank.yaml` has no `fuzzy.aliases` block — the earlier reference was wrong.
- Color via `analogs.color_synonyms`; manufacturer via compact match against catalog manufacturers — reported in `hints` only.

**UI impact** (for the later merge with `feat/web-ui`; `web_ui.md` is edited in that branch, not here — no DTO change):
- `status in {low, not_found}`: right after «вино не найдено в каталоге» offer «Посмотреть аналоги из каталога» (analogs already in `SearchResult.analogs`).
- `analogs.wines == []` (any source) → text «Аналог подобрать не удалось» (no cards, no «показать все»).
- `source == "winner_filters"` with results → note: for more precise matching use the sommelier service (stub link).
- Chips show `filters.grape` (+ exclusions); color / region from `hints` / `winner` may be offered as optional chips that call `find_wines`.

### 4.3 Dictionaries

Built **once at startup** from DB (`categories` → `colors`, `regions`, `sweetness_levels`, split `wines.grape_variety` on `,;/+`, unnest `wines.dishes`), trimmed, case-normalized, sorted (ru collation-insensitive); cached on the service. Refresh = restart. No new table / migration.

### 4.4 Storage and retention

- `queries_dir` default `data/tmp/search_queries/` (gitignored). Files: `{id}{ext}`, `{id}.json`.
- Delete files older than `retention_days` (10) at startup + `scripts/cleanup_search_queries.py` (cron-able, `--dry-run`).
- `query_photo_path` returns the path only for a valid uuid4-hex id that exists (no path traversal); photo is served only by exact id (capability URL), never listed.

### 4.5 Feedback

Append JSONL to `feedback_log` (default `data/tmp/search_feedback.jsonl`, **not** the DB, not the decision log): `{ts, search_id, slug, verdict, status, confidence_level, winner_slug}`. Unknown `search_id` → `SearchNotFoundError`.

## 5. JSON endpoints (backend branch, `src/api/routers/product.py`)

| Method / path | Request | Response | Errors |
|---|---|---|---|
| `POST /api/v1/search` | multipart `image` | `SearchResult` | 400 empty/undecodable, 413 too large, 415 type, 503 runtime |
| `GET /api/v1/search/{search_id}` | — | `SearchResult` | 404 |
| `GET /api/v1/search/{search_id}/analogs?limit=5` | — | `AnalogsResult` | 404 |
| `GET /api/v1/wines/{slug}` | — | `WineCard` | 404 |
| `GET /api/v1/wines?color=&grape=&region=&sweetness=&dish=&exclude_manufacturer=&limit=5&offset=0` | — | `{"items": [WineCard], "total": int}` | 422 (`limit` 1..50) |
| `GET /api/v1/dictionaries` | — | `Dictionaries` | — |
| `POST /api/v1/feedback` | JSON `FeedbackIn` | 204 | 404 unknown search |

Errors: `{"detail": "..."}`; no stack traces. Photo endpoint is UI-only (`/result/{id}/photo`, see [`web_ui.md`](web_ui.md)).

## 6. Config `config/product.yaml` (created in shared step; values tuned by backend branch)

```yaml
confidence:            # cosine of image top-1; PLACEHOLDERS until calibration (SIG-ABS-001)
  high_min: 0.80
  medium_min: 0.65
  not_found_min: 0.50
analogs:
  limit: 5
  color_synonyms:      # OCR token → categories.name (hints only)
    Красное: [красное, красн, red, rosso, tinto, rouge]
    Белое: [белое, бел, white, bianco, blanco, blanc]
    Розовое: [розовое, розе, rose, rosé, rosado, rosato]
    Оранжевое: [оранжевое, orange, arancione, naranja]
  grape_aliases:       # catalog grape (dictionary value) → Latin / OCR spellings (whole-phrase match); optional, default {}
    Санджовезе: [sangiovese]
    Пино Нуар: [pinot noir, pinot nero]
    # … filled by @Coder for dictionary grapes with international names (fix1)
storage:
  queries_dir: data/tmp/search_queries
  retention_days: 10
feedback_log: data/tmp/search_feedback.jsonl
upload:
  max_mb: 15
  content_types: [image/jpeg, image/png, image/webp]
```

Synonym keys are `categories.name` values (see §2). A category missing from the map simply gets no OCR color hint.

## 7. Calibration hook (backend branch, no UI dependency)

`scripts/calibrate_confidence.py`: runs `owner_eval` sets 1/2 through `ProductService.search` (or reads decision log with `score_1`), prints `score_1` distribution for hit@1 / miss, proposes `medium_min` / `high_min`. `not_found_min` needs out-of-catalog photos → document as TODO if none available. Values are changed in YAML only.
