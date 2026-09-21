"""
Hybrid Reranker Engine for HedgeDoc.
Combines Vector Semantic Similarity with Lexical BM25 Keyword Matching and Reciprocal Rank Fusion (RRF).
Ensures the most contextually relevant chunks are prioritized before prompting the LLM.
"""

import re
import math
import logging
from typing import List, Dict, Any, Optional, Set

logger = logging.getLogger(__name__)

# Stop words for lexical filtering
VIETNAMESE_STOPWORDS: Set[str] = {
    "la", "là", "cua", "của", "va", "và", "co", "có", "nhung", "những", "cac", "các",
    "trong", "cho", "duoc", "được", "voi", "với", "ve", "về", "thi", "thì", "o", "ở",
    "nay", "này", "do", "đó", "mot", "một", "nhu", "như", "ra", "sao", "gi", "gì",
    "bao", "nhieu", "nhiêu", "the", "thế", "nao", "nào", "tai", "tại", "lieu", "liệu"
}

ENGLISH_STOPWORDS: Set[str] = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with",
    "by", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
    "what", "which", "who", "whom", "this", "that", "these", "those", "how", "why"
}

STOPWORDS: Set[str] = VIETNAMESE_STOPWORDS | ENGLISH_STOPWORDS


class HybridReranker:
    """
    Two-Stage Hybrid Reranker.
    Scores chunks based on:
    1. Vector Semantic Score (Cosine distance from ChromaDB)
    2. Lexical / Keyword Density Score (Token matches, exact phrase bonus, location label bonus)
    3. Reciprocal Rank Fusion (RRF) for balanced multi-signal rank aggregation.
    """

    def __init__(self, vec_weight: float = 0.5, lex_weight: float = 0.35, rrf_weight: float = 0.15):
        self.vec_weight = vec_weight
        self.lex_weight = lex_weight
        self.rrf_weight = rrf_weight

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract meaningful alphanumeric keywords, filtering stopwords."""
        clean = re.sub(r"[^\w\s\-\.]", " ", text.lower())
        tokens = [t.strip(".-_") for t in clean.split()]
        return [t for t in tokens if len(t) >= 2 and t not in STOPWORDS]

    def _compute_lexical_score(
        self,
        keywords: List[str],
        query: str,
        chunk_text: str,
        location_label: str
    ) -> float:
        """
        Calculate keyword match and term frequency density.
        Gives bonus to exact phrase hits and location header matches.
        """
        if not keywords:
            return 0.5

        chunk_lower = chunk_text.lower()
        loc_lower = location_label.lower()

        matched_count = 0
        total_term_freq = 0

        for kw in keywords:
            count = chunk_lower.count(kw)
            if count > 0:
                matched_count += 1
                total_term_freq += min(count, 5)  # Cap term freq to avoid keyword stuffing
            # Bonus if keyword is in the chapter/sheet/section title
            if kw in loc_lower:
                matched_count += 1
                total_term_freq += 2

        # Ratio of unique query keywords found in the chunk
        coverage_ratio = matched_count / max(1, len(keywords))

        # Bonus for exact query phrase match in the chunk
        phrase_bonus = 0.0
        q_clean = re.sub(r"[^\w\s]", " ", query.lower()).strip()
        if len(q_clean.split()) >= 2 and q_clean in chunk_lower:
            phrase_bonus = 0.3

        # Combine coverage, frequency, and phrase bonus
        freq_factor = math.log1p(total_term_freq) / 3.0
        lex_score = min(1.0, (coverage_ratio * 0.5) + (freq_factor * 0.3) + phrase_bonus)
        return max(0.0, lex_score)

    def rerank(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        top_k: int = 4,
        secondary_query: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Rerank retrieved candidate chunks and return the Top-K most relevant items.
        """
        if not candidates:
            return []

        # Deduplicate candidates by chunk_id
        unique_candidates: Dict[str, Dict[str, Any]] = {}
        for c in candidates:
            cid = c.get("chunk_id") or str(id(c))
            if cid not in unique_candidates:
                unique_candidates[cid] = c
            else:
                # Keep the entry with smaller distance (higher vector similarity)
                existing_dist = unique_candidates[cid].get("distance") or 1.0
                new_dist = c.get("distance") or 1.0
                if new_dist < existing_dist:
                    unique_candidates[cid] = c

        items = list(unique_candidates.values())
        if len(items) <= 1:
            if items:
                items[0]["rerank_score"] = 0.95
                if "metadata" in items[0]:
                    items[0]["metadata"]["rerank_score"] = 0.95
            return items

        # Prepare keywords from primary query and secondary (translated) query
        keywords = self._extract_keywords(query)
        if secondary_query:
            sec_keywords = self._extract_keywords(secondary_query)
            # Merge while preserving order
            for skw in sec_keywords:
                if skw not in keywords:
                    keywords.append(skw)

        # 1. Compute Semantic Vector Scores
        vec_scores = []
        for c in items:
            dist = c.get("distance")
            if dist is not None:
                # Cosine distance: 0.0 is perfect match, ~1.0 is orthogonal
                score = max(0.0, 1.0 - float(dist))
            else:
                score = 0.5
            vec_scores.append(score)

        # 2. Compute Lexical Scores
        lex_scores = []
        for c in items:
            loc = c.get("metadata", {}).get("location_label", "")
            txt = c.get("text", "")
            lex = self._compute_lexical_score(keywords, query, txt, loc)
            lex_scores.append(lex)

        # 3. Compute RRF (Reciprocal Rank Fusion)
        sorted_by_vec = sorted(range(len(items)), key=lambda i: vec_scores[i], reverse=True)
        sorted_by_lex = sorted(range(len(items)), key=lambda i: lex_scores[i], reverse=True)

        vec_ranks = {item_idx: rank for rank, item_idx in enumerate(sorted_by_vec, start=1)}
        lex_ranks = {item_idx: rank for rank, item_idx in enumerate(sorted_by_lex, start=1)}

        rrf_scores = []
        k_rrf = 60.0
        for i in range(len(items)):
            rrf = (1.0 / (k_rrf + vec_ranks[i])) + (1.0 / (k_rrf + lex_ranks[i]))
            rrf_scores.append(rrf)

        max_rrf = max(rrf_scores) if rrf_scores else 1.0
        norm_rrf = [r / max_rrf for r in rrf_scores]

        # 4. Final Aggregated Score
        scored_items = []
        for i, chunk in enumerate(items):
            final_score = (
                (self.vec_weight * vec_scores[i]) +
                (self.lex_weight * lex_scores[i]) +
                (self.rrf_weight * norm_rrf[i])
            )
            final_score = round(min(1.0, max(0.0, final_score)), 4)

            # Store score into chunk and its metadata
            chunk_copy = dict(chunk)
            chunk_copy["rerank_score"] = final_score
            if "metadata" in chunk_copy and isinstance(chunk_copy["metadata"], dict):
                chunk_copy["metadata"] = dict(chunk_copy["metadata"])
                chunk_copy["metadata"]["rerank_score"] = final_score

            scored_items.append((final_score, chunk_copy))

        # Sort descending by final_score
        scored_items.sort(key=lambda x: x[0], reverse=True)

        reranked = [item[1] for item in scored_items[:top_k]]
        logger.info(
            f"HybridReranker: Processed {len(items)} candidates -> Selected top {len(reranked)} (Scores: {[c['rerank_score'] for c in reranked]})"
        )
        return reranked
