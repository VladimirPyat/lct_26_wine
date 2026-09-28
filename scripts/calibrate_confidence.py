"""Калибровка порогов уверенности (``config/product.yaml`` → ``confidence``).

Прогоняет наборы ``data/owner_eval/{N}`` через ``ProductService.search`` — либо
работающего API (``POST /api/v1/search``), либо в процессе (``--in-process``,
``CatalogProductService`` без HTTP), печатает распределение ``score_1`` (косинус
image top-1) для попаданий / промахов top-1 и предлагает ``medium_min`` /
``high_min``. YAML не редактирует: значения меняются вручную после согласования.

    uv run python scripts/calibrate_confidence.py \
        --endpoint http://127.0.0.1:8080/api/v1/search --sets 1 2 \
        --report agent_docs/reports/confidence_calibration.md

    # без сервера; OCR на CPU (GPU занят другим процессом):
    CUDA_VISIBLE_DEVICES= uv run python scripts/calibrate_confidence.py \
        --in-process --ocr-device cpu --report ...
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import urllib.parse
import urllib.request
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT / "src"))

from core.config import ConfidenceSettings, load_product_settings  # noqa: E402

_CONTENT_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}
_GRID = [round(0.40 + 0.05 * i, 2) for i in range(12)]  # 0.40 .. 0.95
_HIT_QUANTILE_FOR_MEDIUM = 10.0


@dataclass(frozen=True)
class Sample:
    """Один запрос owner_eval и ответ продуктового поиска."""

    set_name: str
    query_id: str
    label: str
    expected: str | None
    predicted: str | None
    in_top5: bool
    score_1: float
    margin: float
    status: str
    level: str

    @property
    def hit(self) -> bool:
        return self.expected is not None and self.predicted == self.expected


def _percentile(sorted_values: Sequence[float], pct: float) -> float:
    if len(sorted_values) == 1:
        return sorted_values[0]
    rank = (pct / 100.0) * (len(sorted_values) - 1)
    low, high = math.floor(rank), math.ceil(rank)
    weight = rank - low
    return sorted_values[low] * (1.0 - weight) + sorted_values[high] * weight


def _stats(values: Sequence[float]) -> dict[str, float] | None:
    if not values:
        return None
    ordered = sorted(values)
    return {
        "n": float(len(ordered)),
        "min": ordered[0],
        "p10": _percentile(ordered, 10),
        "p25": _percentile(ordered, 25),
        "median": _percentile(ordered, 50),
        "p75": _percentile(ordered, 75),
        "max": ordered[-1],
        "mean": sum(ordered) / len(ordered),
    }


def _post_image(endpoint: str, image: Path, timeout: float) -> dict[str, Any]:
    if urllib.parse.urlparse(endpoint).scheme not in {"http", "https"}:
        msg = f"endpoint must be http(s): {endpoint}"
        raise ValueError(msg)
    content_type = _CONTENT_TYPES.get(image.suffix.lower(), "application/octet-stream")
    boundary = uuid.uuid4().hex
    body = b"".join(
        [
            f"--{boundary}\r\n".encode(),
            (
                'Content-Disposition: form-data; name="image"; '
                f'filename="{image.name}"\r\n'
                f"Content-Type: {content_type}\r\n\r\n"
            ).encode(),
            image.read_bytes(),
            f"\r\n--{boundary}--\r\n".encode(),
        ]
    )
    request = urllib.request.Request(  # noqa: S310
        endpoint,
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310  # nosec B310
        payload: dict[str, Any] = json.loads(response.read().decode("utf-8"))
    return payload


SearchFn = Callable[[Path], dict[str, Any]]


def _http_search(endpoint: str, timeout: float) -> SearchFn:
    return lambda image: _post_image(endpoint, image, timeout)


def _in_process_search(ocr_device: str | None) -> SearchFn:
    from api.runtime import build_eval_runtime
    from core.product.catalog_service import CatalogProductService

    runtime = build_eval_runtime()
    if ocr_device is not None:
        # OCR is built lazily from app_settings.compute, so this override is enough.
        compute = runtime.app_settings.compute.model_copy(update={"device": ocr_device})
        runtime.app_settings = runtime.app_settings.model_copy(
            update={"compute": compute}
        )
    service = CatalogProductService(runtime, load_product_settings())

    def search(image: Path) -> dict[str, Any]:
        result = service.search(image, original_name=image.name)
        return result.model_dump(mode="json")

    return search


def _run_set(set_dir: Path, search: SearchFn) -> list[Sample]:
    mapping = json.loads((set_dir / "mapping.json").read_text(encoding="utf-8"))
    samples: list[Sample] = []
    for case in mapping.get("cases", []):
        image = set_dir / "queries" / case["image_path"]
        result = search(image)
        candidates = result.get("candidates") or []
        winner = result.get("winner")
        # not_found hides the winner; image top-1 is the pipeline answer then.
        predicted = (
            winner["slug"]
            if winner
            else (candidates[0]["slug"] if candidates else None)
        )
        expected = case.get("expected_slug")
        samples.append(
            Sample(
                set_name=set_dir.name,
                query_id=case["query_id"],
                label=str(case.get("label", "positive")),
                expected=expected,
                predicted=predicted,
                in_top5=expected in {c["slug"] for c in candidates},
                score_1=float(result["score_1"]),
                margin=float(result["margin"]),
                status=str(result["status"]),
                level=str(result["confidence_level"]),
            )
        )
        last = samples[-1]
        mark = "HIT " if last.hit else "MISS"
        print(
            f"[set {set_dir.name}] {last.query_id} {mark} "
            f"score_1={last.score_1:.4f} status={last.status}",
            file=sys.stderr,
        )
    return samples


def _floor2(value: float) -> float:
    return math.floor(value * 100) / 100


def _ceil2(value: float) -> float:
    return math.ceil(value * 100) / 100


def _suggest(positives: Sequence[Sample]) -> dict[str, float | None]:
    hit_scores = sorted(s.score_1 for s in positives if s.hit)
    miss_scores = sorted(s.score_1 for s in positives if not s.hit)
    medium = (
        _floor2(_percentile(hit_scores, _HIT_QUANTILE_FOR_MEDIUM))
        if hit_scores
        else None
    )
    # high: every answer at or above it was correct on owner_eval.
    high = (
        _ceil2(miss_scores[-1] + 1e-9)
        if miss_scores
        else (_floor2(_percentile(hit_scores, 50)) if hit_scores else None)
    )
    if medium is not None and high is not None and high < medium:
        high = medium
    return {"medium_min": medium, "high_min": high}


def _grid_rows(
    positives: Sequence[Sample],
) -> list[tuple[float, int, int, float, float]]:
    total_hits = sum(1 for s in positives if s.hit)
    rows = []
    for threshold in _GRID:
        above = [s for s in positives if s.score_1 >= threshold]
        hits = sum(1 for s in above if s.hit)
        precision = hits / len(above) if above else 1.0
        recall = hits / total_hits if total_hits else 0.0
        rows.append((threshold, len(above), hits, precision, recall))
    return rows


def _fmt_stats(stats: dict[str, float] | None) -> str:
    if stats is None:
        return "—"
    keys = ("min", "p10", "p25", "median", "p75", "max", "mean")
    return f"n={int(stats['n'])}; " + ", ".join(f"{k}={stats[k]:.4f}" for k in keys)


def _render(
    samples: Sequence[Sample],
    current: ConfidenceSettings,
    source: str,
    sets: Sequence[str],
) -> str:
    positives = [s for s in samples if s.label == "positive" and s.expected]
    negatives = [s for s in samples if s.label != "positive"]
    suggestion = _suggest(positives)
    hits = [s.score_1 for s in positives if s.hit]
    misses = [s.score_1 for s in positives if not s.hit]
    outside = [s.score_1 for s in negatives]
    lines = [
        "# Калибровка порогов уверенности (SIG-ABS-001)",
        "",
        f"- Дата: {datetime.now(UTC).isoformat(timespec='seconds')}",
        f"- Источник: `owner_eval` наборы {', '.join(sets)} через `{source}`",
        "- Метрика: `score_1` — косинус image top-1; попадание = `winner.slug` "
        "(для `not_found` — top-1 кандидат) совпадает с `expected_slug`.",
        "- YAML **не изменён**: предложения ниже требуют согласования владельца.",
        "",
        "## Итоги",
        "",
        f"- Запросов (positive): {len(positives)}; hit@1: {len(hits)} "
        f"({(len(hits) / len(positives) if positives else 0):.3f}); "
        f"hit@5: {sum(1 for s in positives if s.in_top5)}",
        f"- `score_1` попаданий: {_fmt_stats(_stats(hits))}",
        f"- `score_1` промахов: {_fmt_stats(_stats(misses))}",
        f"- `score_1` negative (вне каталога): {_fmt_stats(_stats(outside))}",
        "",
        "## Точность / покрытие по порогу",
        "",
        "| порог | ответов ≥ порога | из них верных | точность | доля верных покрыто |",
        "|---|---|---|---|---|",
    ]
    for threshold, above, ok, precision, recall in _grid_rows(positives):
        lines.append(
            f"| {threshold:.2f} | {above} | {ok} | {precision:.3f} | {recall:.3f} |"
        )
    lines += [
        "",
        "## Пороги",
        "",
        "| ключ | сейчас (`product.yaml`) | предложение |",
        "|---|---|---|",
        f"| `high_min` | {current.high_min} | {suggestion['high_min']} |",
        f"| `medium_min` | {current.medium_min} | {suggestion['medium_min']} |",
        f"| `not_found_min` | {current.not_found_min} "
        "| TODO — нужны фото вне каталога |",
        "",
        "Правило предложения: `high_min` — выше максимального `score_1` среди "
        "промахов (все ответы ≥ порога верны на owner_eval); `medium_min` — "
        "10-й перцентиль `score_1` попаданий (≈90 % верных ответов получают "
        "статус `found`).",
        "",
        "## Промахи",
        "",
        "| набор | query_id | ожидалось | ответ | score_1 | margin | статус "
        "| в top-5 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for s in positives:
        if not s.hit:
            top5 = "да" if s.in_top5 else "нет"
            lines.append(
                f"| {s.set_name} | {s.query_id} | `{s.expected}` | `{s.predicted}` "
                f"| {s.score_1:.4f} | {s.margin:.4f} | {s.status} | {top5} |"
            )
    lines.append("")
    return "\n".join(lines)


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--endpoint", default="http://127.0.0.1:8080/api/v1/search")
    parser.add_argument("--sets", nargs="+", default=["1", "2"])
    parser.add_argument(
        "--eval-root", type=Path, default=_REPO_ROOT / "data" / "owner_eval"
    )
    parser.add_argument(
        "--timeout", type=float, default=120.0, help="per-request seconds"
    )
    parser.add_argument(
        "--in-process",
        action="store_true",
        help="build CatalogProductService in this process instead of HTTP",
    )
    parser.add_argument(
        "--ocr-device",
        choices=["cpu", "cuda"],
        default=None,
        help="in-process only: override compute.device for OCR (YAML untouched)",
    )
    parser.add_argument(
        "--report", type=Path, default=None, help="write markdown report"
    )
    parser.add_argument(
        "--samples-out", type=Path, default=None, help="write per-query JSONL"
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Точка входа CLI."""
    args = _parse_args(argv)
    current = load_product_settings().confidence
    if args.in_process:
        search = _in_process_search(args.ocr_device)
        source = "CatalogProductService.search (in-process)"
    else:
        search = _http_search(args.endpoint, args.timeout)
        source = f"POST {args.endpoint}"
    samples: list[Sample] = []
    for name in args.sets:
        samples.extend(_run_set(args.eval_root / name, search))
    report = _render(samples, current, source, args.sets)
    print(report)
    if args.report is not None:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(report, encoding="utf-8")
    if args.samples_out is not None:
        with args.samples_out.open("w", encoding="utf-8") as handle:
            for s in samples:
                row = {**s.__dict__, "hit": s.hit}
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
