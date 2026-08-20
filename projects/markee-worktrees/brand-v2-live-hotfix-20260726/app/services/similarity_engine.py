"""Trademark similarity engine.

Combines three independent similarity signals into a single weighted score:

1. **Textual** — ``rapidfuzz`` string ratio.
2. **Phonetic** — ``jellyfish`` metaphone plus a Portuguese-aware encoder.
3. **Nice classes** — Jaccard overlap of goods/services classes.

Default weighting: 50 % textual, 30 % phonetic, 20 % classes.
"""
from __future__ import annotations

import unicodedata

import jellyfish
from rapidfuzz import fuzz
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


def pt_phonetic_code(value: str) -> str:
    """Encode a string into a Portuguese-aware phonetic code.

    The transformation is deterministic and applies, in order:

    - lowercasing and accent removal (NFD + stripping combining marks);
    - Portuguese digraph folding (``lh→l``, ``nh→n``, ``ç→c``, ``ss→s``,
      ``ph→f``, ``ch→x`` and nasal endings);
    - ``x→ks``;
    - soft ``c`` before ``e``/``i`` → ``s``; ``qu``/``gu`` before ``e``/``i``
      collapse to ``k``/``g``; silent ``h`` is dropped;
    - removal of consecutive duplicate characters.

    Args:
        value: The text to encode.

    Returns:
        The phonetic code, or an empty string for empty input.
    """
    if not value:
        return ""

    # Lowercase and strip accents.
    s = value.lower()
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")

    # Portuguese digraphs (longer sequences first to avoid partial overlaps).
    replacements = [
        ("ães", "aes"),
        ("ão", "ao"),
        ("lh", "l"),
        ("nh", "n"),
        ("ç", "c"),
        ("ss", "s"),
        ("ph", "f"),
        ("ch", "x"),
    ]
    for old, new in replacements:
        s = s.replace(old, new)

    # General x → ks (after the ch digraph has been handled).
    s = s.replace("x", "ks")

    # Context-sensitive rules for c / qu / gu / h.
    result_chars: list[str] = []
    i = 0
    while i < len(s):
        ch = s[i]
        if ch == "c" and i + 1 < len(s) and s[i + 1] in "ei":
            result_chars.append("s")
            i += 1
        elif ch == "q" and i + 2 < len(s) and s[i + 1] == "u" and s[i + 2] in "ei":
            result_chars.append("k")
            i += 2
        elif ch == "g" and i + 2 < len(s) and s[i + 1] == "u" and s[i + 2] in "ei":
            result_chars.append("g")
            i += 2
        elif ch == "h":
            # Silent h — skip it entirely.
            pass
        else:
            result_chars.append(ch)
        i += 1

    s = "".join(result_chars)

    # Collapse consecutive duplicate characters.
    cleaned: list[str] = []
    prev = ""
    for ch in s:
        if ch != prev:
            cleaned.append(ch)
            prev = ch
    return "".join(cleaned)


class SimilarityEngine:
    """Multi-factor similarity matching for trademarks."""

    DEFAULT_TEXT_WEIGHT = 0.50
    DEFAULT_PHONETIC_WEIGHT = 0.30
    DEFAULT_CLASS_WEIGHT = 0.20

    def __init__(self, db_session: AsyncSession) -> None:
        """Initialise the engine.

        Args:
            db_session: Async session used for database-backed searches.
        """
        self.db = db_session

    @staticmethod
    def text_similarity(a: str, b: str) -> float:
        """Return the case-insensitive rapidfuzz ratio (0–100) for two strings.

        Args:
            a: First string.
            b: Second string.

        Returns:
            A score between 0 and 100 (0 if either string is empty).
        """
        if not a or not b:
            return 0.0
        return float(fuzz.ratio(a.lower(), b.lower()))

    @staticmethod
    def phonetic_similarity(a: str, b: str) -> float:
        """Return a phonetic similarity (0–100) using metaphone codes.

        Args:
            a: First string.
            b: Second string.

        Returns:
            ``100.0`` when the metaphone codes match, otherwise ``0.0``.
        """
        if not a or not b:
            return 0.0
        code_a = jellyfish.metaphone(a.lower().strip())
        code_b = jellyfish.metaphone(b.lower().strip())
        if code_a and code_a == code_b:
            return 100.0
        return 0.0

    @staticmethod
    def pt_phonetic_similarity(a: str, b: str) -> float:
        """Return a Portuguese phonetic similarity (0–100).

        Args:
            a: First string.
            b: Second string.

        Returns:
            ``100.0`` when the PT phonetic codes match, otherwise ``0.0``.
        """
        if not a or not b:
            return 0.0
        code_a = pt_phonetic_code(a)
        code_b = pt_phonetic_code(b)
        if code_a and code_a == code_b:
            return 100.0
        return 0.0

    @staticmethod
    def class_overlap(classes_a: list[int], classes_b: list[int]) -> float:
        """Return the Jaccard overlap of two Nice class lists (0–100).

        Args:
            classes_a: First list of Nice class numbers.
            classes_b: Second list of Nice class numbers.

        Returns:
            ``(|A ∩ B| / |A ∪ B|) * 100`` (0 if either list is empty).
        """
        if not classes_a or not classes_b:
            return 0.0
        set_a, set_b = set(classes_a), set(classes_b)
        union = len(set_a | set_b)
        if union == 0:
            return 0.0
        return (len(set_a & set_b) / union) * 100.0

    @classmethod
    def composite_score(
        cls,
        text_score: float,
        phonetic_score: float,
        class_score: float,
        phonetic_weight: float = DEFAULT_PHONETIC_WEIGHT,
        class_weight: float = DEFAULT_CLASS_WEIGHT,
        text_weight: float = DEFAULT_TEXT_WEIGHT,
    ) -> float:
        """Combine the three signals into a single weighted score (0–100).

        Args:
            text_score: Textual similarity (0–100).
            phonetic_score: Phonetic similarity (0–100).
            class_score: Class overlap (0–100).
            phonetic_weight: Weight applied to the phonetic score.
            class_weight: Weight applied to the class score.
            text_weight: Weight applied to the textual score.

        Returns:
            The normalised weighted score. When all weights are zero the raw
            ``text_score`` is returned as a sensible fallback.
        """
        total = text_weight + phonetic_weight + class_weight
        if total == 0:
            return text_score
        return (
            (text_score * text_weight)
            + (phonetic_score * phonetic_weight)
            + (class_score * class_weight)
        ) / total

    async def find_similar_marks(
        self,
        query: str,
        nice_classes: list[int] | None = None,
        threshold: int = 80,
        limit: int = 50,
        jurisdiction: str | None = None,
    ) -> list[dict]:
        """Find marks similar to ``query`` using pg_trgm plus in-memory refinement.

        Strategy:
            1. Fast database-side candidate retrieval via the pg_trgm GIN index.
            2. In-memory refinement with rapidfuzz + phonetic + class scoring.
            3. Sort by descending composite score and truncate to ``limit``.

        Args:
            query: The mark text to search for.
            nice_classes: Optional Nice classes to weight/filter by.
            threshold: Minimum composite score (0–100) to keep a match.
            limit: Maximum number of results to return.
            jurisdiction: Optional jurisdiction filter (e.g. ``"EUIPO"``).

        Returns:
            A list of matching trademark rows (as dicts), each annotated with
            ``similarity_score``, ``phonetic_score`` and ``class_overlap_score``.
        """
        nice_classes = nice_classes or []

        sql = """
            SELECT id, source_id, word_mark, nice_classes, jurisdiction, status,
                   registration_date, applicants, representatives
            FROM trademarks
            WHERE word_mark IS NOT NULL
              AND similarity(word_mark, :query) > :trgm_threshold
        """
        params: dict = {
            "query": query,
            # pg_trgm similarity is 0–1; map the 0–100 threshold conservatively.
            "trgm_threshold": max(0.1, threshold / 200.0),
        }
        if jurisdiction:
            sql += " AND jurisdiction = :jurisdiction"
            params["jurisdiction"] = jurisdiction
        if nice_classes:
            sql += " AND nice_classes && :nice_classes"
            params["nice_classes"] = nice_classes

        sql += " ORDER BY similarity(word_mark, :query) DESC LIMIT :limit"
        params["limit"] = limit * 3  # over-fetch to allow refinement

        result = await self.db.execute(text(sql), params)
        rows = result.mappings().all()

        scored: list[tuple[float, dict]] = []
        for row in rows:
            word_mark = row.get("word_mark") or ""
            text_score = self.text_similarity(query, word_mark)
            phonetic_score = max(
                self.phonetic_similarity(query, word_mark),
                self.pt_phonetic_similarity(query, word_mark),
            )
            class_score = self.class_overlap(nice_classes, row.get("nice_classes") or [])
            composite = self.composite_score(text_score, phonetic_score, class_score)
            if composite >= threshold:
                enriched = dict(row)
                enriched["similarity_score"] = text_score
                enriched["phonetic_score"] = phonetic_score
                enriched["class_overlap_score"] = class_score
                enriched["composite_score"] = composite
                scored.append((composite, enriched))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [row for _, row in scored[:limit]]

    async def search_text_only(self, query: str, limit: int = 50) -> list[dict]:
        """Run a fast pg_trgm-only search without composite refinement.

        Args:
            query: The mark text to search for.
            limit: Maximum number of results.

        Returns:
            Matching trademark rows ordered by descending trigram similarity.
        """
        sql = """
            SELECT id, source_id, word_mark, nice_classes, jurisdiction, status,
                   registration_date, applicants, representatives,
                   similarity(word_mark, :query) AS sim
            FROM trademarks
            WHERE word_mark IS NOT NULL
              AND word_mark % :query
            ORDER BY similarity(word_mark, :query) DESC
            LIMIT :limit
        """
        result = await self.db.execute(text(sql), {"query": query, "limit": limit})
        return [dict(row) for row in result.mappings().all()]
