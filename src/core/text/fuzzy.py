"""Levenshtein / RapidFuzz rerank каталожных вин по OCR-тексту."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import cast

import Levenshtein
from rapidfuzz import fuzz

from core.config import FuzzySettings
from core.contracts import SearchResult, WineRecord
from core.text.normalize import (
    compact_alnum,
    expand_token_aliases,
    is_generic_field,
    normalize_text,
    primary_ocr_lines,
    text_variants,
    tokenize,
    transliterate_cyrillic,
)
from core.text.ocr_postprocess import postprocess_ocr_lines

_REQUIRED_FIELDS: tuple[str, ...] = ("title", "manufacturer", "category")
_FUZZ_SCALE = 100.0
TEXT_SCORE_FORMULA_SHORTLIST_IDF = "additive+shortlist_idf"


class FuzzyReranker:
    """Скоринг и переранжирование кандидатов по нечёткому совпадению OCR и каталога.

    Ключи ``field_weights`` обязаны включать ``title``, ``manufacturer`` и
    ``category``. Вызывающий передаёт YAML-значения; класс сам конфиг не грузит.
    Опциональные ``min_line_chars`` / ``drop_spaced_letters`` включают OCR
    postprocess перед скорингом.

    Скоринг: Levenshtein ratio, RapidFuzz partial/token-set, транслит
    Cyrillic↔Latin, compact-токены, покрытие distinctive-токенов и бонус
    производителя, чтобы склеенный OCR вроде ``ALMAVALLEY`` совпадал с
    ``Alma Valley``.

    На image-шортлисте OCR-токен без ratio-матча может привязаться к
    уникальному соседу по числу правок (``мердон``→``мерло``). Несколько
    соседей на том же k — мусор. Catalog ``rank_ocr_only`` это не использует.
    """

    def __init__(
        self,
        field_weights: Mapping[str, float],
        fuzzy: FuzzySettings,
        *,
        min_line_chars: int | None = None,
        drop_spaced_letters: bool | None = None,
    ) -> None:
        missing = [name for name in _REQUIRED_FIELDS if name not in field_weights]
        if missing:
            msg = f"field_weights missing required keys: {missing}"
            raise KeyError(msg)
        self._field_weights = {
            name: float(field_weights[name]) for name in _REQUIRED_FIELDS
        }
        if (min_line_chars is None) ^ (drop_spaced_letters is None):
            msg = (
                "min_line_chars and drop_spaced_letters must both be set "
                "or both omitted"
            )
            raise ValueError(msg)
        self._min_line_chars = min_line_chars
        self._drop_spaced_letters = drop_spaced_letters
        self.token_min_len = fuzzy.token_min_len
        self.token_fuzz_min = fuzzy.token_fuzz_min
        self.short_field_len = fuzzy.short_field_len
        self.short_field_score_floor = fuzzy.short_field_score_floor
        self.short_field_dampen = fuzzy.short_field_dampen
        self.coverage_weight = fuzzy.coverage_weight
        self.token_hit_weight = fuzzy.token_hit_weight
        self.mfr_compact_high = fuzzy.mfr_compact_high
        self.mfr_compact_mid = fuzzy.mfr_compact_mid
        self.mfr_bonus_high = fuzzy.mfr_bonus_high
        self.mfr_bonus_mid = fuzzy.mfr_bonus_mid
        self.primary_line_cap = fuzzy.primary_line_cap
        self.prefilter_min_candidates = fuzzy.prefilter_min_candidates
        self.exact_title_token_bonus = fuzzy.exact_title_token_bonus
        self.title_token_ratio_min = fuzzy.title_token_ratio_min
        self.shortlist_idf_weight = fuzzy.shortlist_idf_weight
        self.token_edit_max = fuzzy.token_edit_max
        self.token_edit_max_frac = fuzzy.token_edit_max_frac
        self.token_edit_idf_scale = fuzzy.token_edit_idf_scale

    def normalize(self, text: str) -> str:
        """Нижний регистр, схлопывание пробелов, ё/Ё → е."""
        return normalize_text(text)

    def field_score(self, ocr_normalized: str, field_value: str) -> float:
        """Лучший нечёткий ratio в ``[0, 1]`` по текстовым вариантам.

        Пустое поле (пустое или только пробелы после normalize) даёт ``0.0``.
        Короткие generic-поля (например категория «красное») глушатся, если
        совпадение не почти точное, чтобы они не доминировали длинный OCR.
        """
        normalized_field = self.normalize(field_value)
        if not normalized_field:
            return 0.0
        ocr_norm = self.normalize(ocr_normalized)
        if not ocr_norm:
            return 0.0
        best = _best_variant_ratio(ocr_norm, normalized_field)
        if is_generic_field(normalized_field, short_field_len=self.short_field_len):
            if best < self.short_field_score_floor:
                best *= self.short_field_dampen
        return best

    def score_wine(
        self,
        ocr_lines: Sequence[str],
        *,
        title: str,
        manufacturer: str,
        category: str,
    ) -> float:
        """Взвешенные field-score плюс бонусы distinctive-токенов и производителя."""
        lines = self._prepare_lines(ocr_lines)
        primary = primary_ocr_lines(lines, max_lines=self.primary_line_cap)
        title_score = self._best_against_lines(primary, title)
        mfr_score = self._best_against_lines(primary, manufacturer)
        cat_score = self._best_against_lines(
            [self.normalize(line) for line in lines if self.normalize(line)],
            category,
        )
        coverage, hits = self._token_coverage(lines, title, manufacturer)
        mfr_bonus = self._manufacturer_compact_bonus(lines, manufacturer)
        title_bonus = self._exact_title_token_bonus(lines, title)
        return (
            self._field_weights["title"] * title_score
            + self._field_weights["manufacturer"] * mfr_score
            + self._field_weights["category"] * cat_score
            + self.coverage_weight * coverage
            + self.token_hit_weight * float(hits)
            + mfr_bonus
            + title_bonus
        )

    def rerank(
        self,
        ocr_lines: Sequence[str],
        candidates: Sequence[SearchResult],
        wines_by_id: Mapping[int, WineRecord],
        top_n: int,
    ) -> list[SearchResult]:
        """Переранжировать первые ``top_n`` image-кандидатов по ``text_score``.

        ``text_score`` = additive ``score_wine`` plus shortlist IDF: OCR
        tokens that match only some candidates (e.g. variety inside one
        producer family) are boosted; tokens matching the whole pool are
        ignored. Ничьи сохраняют исходный относительный порядок (stable).
        Каждый возвращённый dict — копия кандидата с полем ``text_score``.
        Кандидаты за пределами ``top_n`` отбрасываются; длина результата
        ``min(top_n, len(candidates))``.

        Raises:
            ValueError: если ``top_n`` отрицательный.
            KeyError: если ``wine_id`` из шортлиста нет в ``wines_by_id``.
        """
        if top_n < 0:
            msg = f"top_n must be >= 0, got {top_n}"
            raise ValueError(msg)

        prepared = self._prepare_lines(ocr_lines)
        shortlist = list(candidates[:top_n])
        wines: list[WineRecord] = []
        for candidate in shortlist:
            wine_id = candidate["wine_id"]
            if wine_id not in wines_by_id:
                msg = (
                    f"FuzzyReranker.rerank: wine_id {wine_id} is missing "
                    "from wines_by_id"
                )
                raise KeyError(msg)
            wines.append(wines_by_id[wine_id])
        ocr_tokens = self._ocr_content_tokens(prepared)
        idf_bonuses = self._shortlist_idf_bonus(ocr_tokens, wines)
        scored: list[tuple[float, int, SearchResult]] = []
        for index, candidate in enumerate(shortlist):
            wine = wines[index]
            text_score = self.score_wine(
                prepared,
                title=wine.title,
                manufacturer=wine.manufacturer,
                category=wine.category,
            )
            text_score += idf_bonuses[index]
            text_score -= self._shared_title_bonus(prepared, wine.title, wines)
            updated = dict(candidate)
            updated["text_score"] = text_score
            scored.append((text_score, index, cast(SearchResult, updated)))

        scored.sort(key=lambda item: (-item[0], item[1]))
        return [item[2] for item in scored]

    def rank_catalog(
        self,
        ocr_lines: Sequence[str],
        wines: Sequence[WineRecord],
        top_n: int,
    ) -> list[SearchResult]:
        """OCR-only ранжирование списка вин с опциональным token pre-filter."""
        if top_n < 0:
            msg = f"top_n must be >= 0, got {top_n}"
            raise ValueError(msg)

        prepared = self._prepare_lines(ocr_lines)
        candidates = self._prefilter_wines(prepared, wines)
        scored: list[tuple[float, int, SearchResult]] = []
        for index, wine in enumerate(candidates):
            text_score = self.score_wine(
                prepared,
                title=wine.title,
                manufacturer=wine.manufacturer,
                category=wine.category,
            )
            result = dict(
                SearchResult(
                    wine_id=wine.id,
                    external_id=wine.external_id,
                    score=text_score,
                    inliers=None,
                    good_matches=None,
                    vlad_rank=None,
                    image_path=wine.image_path,
                )
            )
            result["text_score"] = text_score
            scored.append((text_score, index, cast(SearchResult, result)))

        scored.sort(key=lambda item: (-item[0], item[1]))
        return [item[2] for item in scored[:top_n]]

    def _ocr_content_tokens(self, lines: Sequence[str]) -> list[str]:
        """Unique OCR tokens after stopword / min-length filter."""
        seen: set[str] = set()
        tokens: list[str] = []
        for line in lines:
            for token in tokenize(line, min_len=self.token_min_len):
                if token in seen:
                    continue
                seen.add(token)
                tokens.append(token)
        return tokens

    def _shortlist_idf_bonus(
        self,
        ocr_tokens: Sequence[str],
        wines: Sequence[WineRecord],
    ) -> list[float]:
        """Boost OCR tokens that do not match every wine in this shortlist.

        Tokens present on all candidates (typical manufacturer / family name)
        get zero weight. Catalog ``rank_ocr_only`` does not call this.
        """
        count = len(wines)
        if (
            count < 2
            or self.shortlist_idf_weight <= 0.0
            or not ocr_tokens
        ):
            return [0.0] * count
        bindings = self._unique_edit_bindings(ocr_tokens, wines)
        matched: list[set[str]] = []
        scales: list[dict[str, float]] = []
        for wine in wines:
            field_tokens = self._field_token_set(wine.title, wine.manufacturer)
            hits: set[str] = set()
            token_scale: dict[str, float] = {}
            for token in ocr_tokens:
                if self._token_matches_any(token, field_tokens):
                    hits.add(token)
                    token_scale[token] = 1.0
                    continue
                bound = bindings.get(token)
                if bound is None or self.token_edit_idf_scale <= 0.0:
                    continue
                group, _dist = bound
                if group & field_tokens:
                    hits.add(token)
                    token_scale[token] = self.token_edit_idf_scale
            matched.append(hits)
            scales.append(token_scale)
        document_freq: dict[str, int] = {}
        for hits in matched:
            for token in hits:
                document_freq[token] = document_freq.get(token, 0) + 1
        bonuses: list[float] = []
        for hits, token_scale in zip(matched, scales, strict=True):
            bonus = 0.0
            for token in hits:
                freq = document_freq[token]
                if 0 < freq < count:
                    bonus += token_scale[token] * math.log(count / freq)
            bonuses.append(self.shortlist_idf_weight * bonus)
        return bonuses

    def _unique_edit_bindings(
        self,
        ocr_tokens: Sequence[str],
        wines: Sequence[WineRecord],
    ) -> dict[str, tuple[frozenset[str], int]]:
        """Map OCR token → unique shortlist neighbor (canonical aliases, dist).

        Walk k=1..``token_edit_max``. Empty at k → try k+1. Several alias
        groups at the same k → garbage (do not try a larger k). ``dist`` must
        be ≤ ``token_edit_max_frac`` of the longer spelling. k=0 is exact /
        alias and is handled by ``_token_matches_any``.
        """
        if self.token_edit_max < 1:
            return {}
        universe: set[str] = set()
        for wine in wines:
            universe |= self._field_token_set(wine.title, wine.manufacturer)
        groups = _merge_alias_groups(universe)
        if not groups:
            return {}
        bindings: dict[str, tuple[frozenset[str], int]] = {}
        for token in ocr_tokens:
            if self._token_matches_any(token, universe):
                continue
            for dist in range(1, self.token_edit_max + 1):
                hits = [
                    group
                    for group in groups
                    if self._min_allowed_edit(token, group) == dist
                ]
                if len(hits) == 1:
                    bindings[token] = (hits[0], dist)
                    break
                if len(hits) > 1:
                    break
        return bindings

    def _min_allowed_edit(self, ocr_token: str, group: frozenset[str]) -> int | None:
        """Smallest allowed Levenshtein dist from OCR aliases to one group."""
        best: int | None = None
        ocr_vars = [
            variant
            for variant in expand_token_aliases(ocr_token)
            if len(variant) >= self.token_min_len
        ]
        for ocr_var in ocr_vars:
            for field_token in group:
                if len(field_token) < self.token_min_len:
                    continue
                dist = int(Levenshtein.distance(ocr_var, field_token))
                if dist < 1 or dist > self.token_edit_max:
                    continue
                maxlen = max(len(ocr_var), len(field_token))
                if dist > self.token_edit_max_frac * maxlen:
                    continue
                if best is None or dist < best:
                    best = dist
        return best

    def _prepare_lines(self, ocr_lines: Sequence[str]) -> list[str]:
        if self._min_line_chars is None or self._drop_spaced_letters is None:
            return list(ocr_lines)
        return postprocess_ocr_lines(
            ocr_lines,
            min_line_chars=self._min_line_chars,
            drop_spaced_letters=self._drop_spaced_letters,
        )

    def _best_against_lines(self, lines: Sequence[str], field_value: str) -> float:
        field_norm = self.normalize(field_value)
        if not field_norm or not lines:
            return 0.0
        blob = self.normalize(" ".join(lines))
        best = 0.0
        for target in (*lines, blob):
            best = max(best, self.field_score(target, field_norm))
        return best

    def _field_token_set(self, title: str, manufacturer: str) -> set[str]:
        min_len = self.token_min_len
        tokens: set[str] = set()
        for field in (title, manufacturer):
            for token in tokenize(field, min_len=min_len):
                tokens |= expand_token_aliases(token)
            compact = compact_alnum(field)
            if len(compact) >= min_len:
                tokens.add(compact)
                tokens.add(compact_alnum(transliterate_cyrillic(field)))
        return {token for token in tokens if len(token) >= min_len}

    def _token_coverage(
        self,
        ocr_lines: Sequence[str],
        title: str,
        manufacturer: str,
    ) -> tuple[float, int]:
        ocr_raw: list[str] = []
        for line in ocr_lines:
            ocr_raw.extend(tokenize(line, min_len=self.token_min_len))
        field_tokens = self._field_token_set(title, manufacturer)
        if not ocr_raw or not field_tokens:
            return 0.0, 0
        hits = 0
        for raw in set(ocr_raw):
            if self._token_matches_any(raw, field_tokens):
                hits += 1
        coverage = hits / max(1, len(set(ocr_raw)))
        return coverage, hits

    def _token_matches_any(self, token: str, field_tokens: set[str]) -> bool:
        min_len = self.token_min_len
        for candidate in expand_token_aliases(token):
            if len(candidate) < min_len:
                continue
            for field_token in field_tokens:
                if candidate == field_token:
                    return True
                if (
                    len(field_token) >= min_len
                    and float(fuzz.ratio(candidate, field_token)) >= self.token_fuzz_min
                ):
                    return True
        return False

    def _manufacturer_compact_bonus(
        self, ocr_lines: Sequence[str], manufacturer: str
    ) -> float:
        mfr_compact = compact_alnum(manufacturer)
        if len(mfr_compact) < 5:
            return 0.0
        mfr_lat = compact_alnum(transliterate_cyrillic(manufacturer))
        best = 0.0
        for line in ocr_lines:
            line_compact = compact_alnum(line)
            if not line_compact:
                continue
            best = max(
                best,
                float(fuzz.partial_ratio(line_compact, mfr_compact)) / _FUZZ_SCALE,
                float(fuzz.ratio(line_compact, mfr_compact)) / _FUZZ_SCALE,
                float(fuzz.partial_ratio(line_compact, mfr_lat)) / _FUZZ_SCALE,
            )
        if best >= self.mfr_compact_high:
            return self.mfr_bonus_high * best
        if best >= self.mfr_compact_mid:
            return self.mfr_bonus_mid * best
        return 0.0

    def _shared_title_bonus(
        self,
        ocr_lines: Sequence[str],
        title: str,
        wines: Sequence[WineRecord],
    ) -> float:
        """Drop the short-title bonus when its OCR token also hits a sibling.

        ``score_wine`` still adds the bonus. On a visual shortlist the same
        token often names the whole line (``гравити``, ``мускат``, ``шардоне``),
        so a one-word catalog title would outrank the real longer SKU.
        """
        trigger = self._exact_title_match_token(ocr_lines, title)
        if trigger is None or len(wines) < 2:
            return 0.0
        matched = 0
        for wine in wines:
            field_tokens = self._field_token_set(wine.title, wine.manufacturer)
            if self._token_matches_any(trigger, field_tokens):
                matched += 1
                if matched >= 2:
                    return self.exact_title_token_bonus
        return 0.0

    def _exact_title_token_bonus(self, ocr_lines: Sequence[str], title: str) -> float:
        """Бонус, если OCR-токен совпадает с коротким title (arena↔Арена)."""
        if self._exact_title_match_token(ocr_lines, title) is None:
            return 0.0
        return self.exact_title_token_bonus

    def _exact_title_match_token(
        self, ocr_lines: Sequence[str], title: str
    ) -> str | None:
        """OCR-токен, который совпал с коротким title целиком, иначе ``None``."""
        title_norm = normalize_text(title)
        title_compact = compact_alnum(title)
        title_lat = compact_alnum(transliterate_cyrillic(title))
        if len(title_compact) < self.token_min_len:
            return None
        # Only for short titles — long titles already get coverage/field scores.
        if len(title_norm.split()) > 3:
            return None
        for line in ocr_lines:
            for token in tokenize(line, min_len=self.token_min_len):
                for variant in expand_token_aliases(token):
                    if variant in {title_compact, title_lat, title_norm}:
                        return token
                    compact_hit = (
                        float(fuzz.ratio(variant, title_compact))
                        >= self.title_token_ratio_min
                    )
                    lat_hit = (
                        float(fuzz.ratio(variant, title_lat))
                        >= self.title_token_ratio_min
                    )
                    if compact_hit or lat_hit:
                        return token
        return None

    def _prefilter_wines(
        self,
        ocr_lines: Sequence[str],
        wines: Sequence[WineRecord],
    ) -> Sequence[WineRecord]:
        ocr_tokens: set[str] = set()
        for line in ocr_lines:
            for token in tokenize(line, min_len=self.token_min_len):
                ocr_tokens |= expand_token_aliases(token)
        if not ocr_tokens:
            return wines
        preferred: list[WineRecord] = []
        for wine in wines:
            field_tokens = self._field_token_set(wine.title, wine.manufacturer)
            if any(
                self._token_matches_any(token, field_tokens) for token in ocr_tokens
            ):
                preferred.append(wine)
        if len(preferred) >= self.prefilter_min_candidates:
            return preferred
        return wines


def _merge_alias_groups(tokens: Sequence[str] | set[str]) -> list[frozenset[str]]:
    """Union-find on overlapping ``expand_token_aliases`` sets (merlo≡merlot)."""
    groups: list[set[str]] = []
    for token in tokens:
        aliases = expand_token_aliases(token)
        if not aliases:
            continue
        overlapping = [group for group in groups if group & aliases]
        if not overlapping:
            groups.append(set(aliases))
            continue
        merged = set(aliases)
        for group in overlapping:
            merged |= group
        groups = [group for group in groups if group not in overlapping]
        groups.append(merged)
    return [frozenset(group) for group in groups]


def _best_variant_ratio(left: str, right: str) -> float:
    best = 0.0
    for left_variant in text_variants(left):
        for right_variant in text_variants(right):
            if not left_variant or not right_variant:
                continue
            best = max(
                best,
                float(Levenshtein.ratio(left_variant, right_variant)),
                float(fuzz.partial_ratio(left_variant, right_variant)) / _FUZZ_SCALE,
                float(fuzz.token_set_ratio(left_variant, right_variant)) / _FUZZ_SCALE,
            )
    return best
